import json
import shutil
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from meetup_video import config, editor
from meetup_video.roster import globe_project


@pytest.fixture
def server(tmp_path, monkeypatch):
    cfg = tmp_path / "scenes.json"
    shutil.copy(config.DEFAULT_CONFIG, cfg)
    root = tmp_path / "root"
    (root / "assets" / "scenes").mkdir(parents=True)
    (root / "docs").mkdir()
    (root / "docs" / "manual_ko.md").write_text("# 매뉴얼", encoding="utf-8")
    monkeypatch.setattr(config, "ROOT", root)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), editor.make_handler(cfg, editor.RenderJob()))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}", cfg, root
    srv.shutdown()


def req(url, method="GET", data=None, headers=None):
    r = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def test_page_and_manual_served(server):
    base, _, _ = server
    code, body = req(base + "/")
    assert code == 200 and "영상 편집".encode() in body and b"/manual/en" in body
    assert req(base + "/manual/ko") == (200, "# 매뉴얼".encode())


def test_globe_counts_persist_through_editor(server):
    base, _, _ = server
    project = globe_project(["Region\tCountry\tCity", "Asia-Pacific\tKorea\tSeoul"])
    goal = base + "/api/config?name=ambassadors"
    assert req(goal, "PUT", json.dumps(project).encode())[0] == 200
    data = json.loads(req(goal)[1])
    data["scenes"][0]["globe"]["regions"][0]["countries"][0]["count"] = 7
    assert req(goal, "PUT", json.dumps(data).encode())[0] == 200
    assert json.loads(req(goal)[1]) == data


def test_save_valid_config_and_reject_invalid(server):
    base, cfg, _ = server
    data = json.loads(req(base + "/api/config")[1])
    data["ending"]["welcome"] = "어서 오세요"
    data["scenes"][0]["caption_ko"] = "새 자막"
    assert req(base + "/api/config", "PUT", json.dumps(data).encode())[0] == 200
    saved = json.loads(cfg.read_text(encoding="utf-8"))
    assert saved["ending"]["welcome"] == "어서 오세요" and saved["scenes"][0]["caption_ko"] == "새 자막"
    data["scenes"][0]["duration"] = 0
    code, body = req(base + "/api/config", "PUT", json.dumps(data).encode())
    assert code == 400 and b"duration" in body
    assert json.loads(cfg.read_text(encoding="utf-8"))["scenes"][0]["duration"] == 5


def test_upload_image_and_reject_other_types(server):
    base, _, root = server
    code, body = req(base + "/api/upload/s1_namsan.PNG", "POST", b"\x89PNG")
    assert code == 200 and json.loads(body)["image"] == "assets/scenes/s1_namsan.png"
    assert (root / "assets" / "scenes" / "s1_namsan.png").read_bytes() == b"\x89PNG"
    assert req(base + "/api/upload/x.exe", "POST", b"x")[0] == 400
    assert req(base + "/files/../SPEC.md")[0] == 404


def test_upload_music_and_serve_it(server):
    base, _, root = server
    code, body = req(base + "/api/upload-music/my_song.MP3", "POST", b"ID3")
    assert code == 200 and json.loads(body)["file"] == "assets/music/my_song.mp3"
    assert req(base + "/files/assets/music/my_song.mp3") == (200, b"ID3")
    assert req(base + "/api/upload-music/x.exe", "POST", b"x")[0] == 400


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")
def test_render_job_reports_progress(tmp_path):
    cfg = tmp_path / "c.json"
    cfg.write_text(json.dumps({"video": {"width": 160, "height": 90, "fps": 2},
                               "scenes": [{"id": "a", "duration": 1}]}), encoding="utf-8")
    job = editor.RenderJob()
    assert job.start(cfg, str(tmp_path / "v.mp4"), preview=False)
    for _ in range(100):
        if not job.state["running"]:
            break
        time.sleep(0.1)
    assert job.state["error"] == "" and job.state["progress"] == 100


def test_cross_origin_writes_rejected(server):
    base, _, root = server
    evil = {"Origin": "http://evil.example"}
    assert req(base + "/api/upload/s1_namsan.png", "POST", b"x", evil)[0] == 403
    assert req(base + "/api/config", "PUT", b"{}", evil)[0] == 403
    assert req(base + "/api/render", "POST", b"", {"Host": "evil.example"})[0] == 403
    assert not (root / "assets" / "scenes" / "s1_namsan.png").exists()
    assert req(base + "/api/upload/s1_namsan.png", "POST", b"x", {"Origin": base})[0] == 200


def test_named_projects_save_list_and_open(server):
    base, cfg, _ = server
    data = json.loads(req(base + "/api/config")[1])
    data["ending"]["show_qr"] = True
    assert req(base + "/api/config?name=closing", "PUT", json.dumps(data).encode())[0] == 200
    assert json.loads((cfg.parent / "closing.json").read_text(encoding="utf-8"))["ending"]["show_qr"] is True
    assert json.loads(cfg.read_text(encoding="utf-8"))["ending"].get("show_qr") is not True
    j = json.loads(req(base + "/api/projects")[1])
    assert j["default"] == "scenes"
    assert [(p["name"], p["qr"]) for p in j["projects"]] == [("scenes", False), ("closing", True)]
    assert json.loads(req(base + "/api/config?name=closing")[1])["ending"]["show_qr"] is True
    assert req(base + "/api/config?name=nope")[0] == 404
    for bad in ("..%2Fx", "a%20b", "x" * 41):
        assert req(base + f"/api/config?name={bad}", "PUT", json.dumps(data).encode())[0] == 400


def test_render_uses_project_name(tmp_path):
    cfg = tmp_path / "scenes.json"
    shutil.copy(config.DEFAULT_CONFIG, cfg)
    shutil.copy(config.DEFAULT_CONFIG, tmp_path / "closing.json")
    calls = []

    class Job:
        state = {}

        def start(self, src, out, preview):
            calls.append((src.name, out, preview))
            return True

    srv = ThreadingHTTPServer(("127.0.0.1", 0), editor.make_handler(cfg, Job()))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_port}"
    try:
        assert req(base + "/api/render", "POST", b"")[0] == 202
        assert req(base + "/api/render?name=closing", "POST", b"")[0] == 202
        assert req(base + "/api/render?name=closing&preview=1", "POST", b"")[0] == 202
        assert req(base + "/api/render?name=missing", "POST", b"")[0] == 404
    finally:
        srv.shutdown()
    assert calls == [("scenes.json", "out/devin-meetup-seoul.mp4", False),
                     ("closing.json", "out/devin-meetup-seoul-closing.mp4", False),
                     ("closing.json", "out/preview-closing.mp4", True)]


def test_default_config_with_any_file_name(tmp_path):
    cfg = tmp_path / "opening.v2.json"
    shutil.copy(config.DEFAULT_CONFIG, cfg)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), editor.make_handler(cfg, editor.RenderJob()))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_port}"
    try:
        data = json.loads(req(base + "/api/config")[1])
        assert req(base + "/api/config", "PUT", json.dumps(data).encode())[0] == 200
        assert [p["name"] for p in json.loads(req(base + "/api/projects")[1])["projects"]] == ["opening.v2"]
    finally:
        srv.shutdown()


def test_projects_list_survives_missing_default(server):
    base, cfg, _ = server
    data = json.loads(req(base + "/api/config")[1])
    assert req(base + "/api/config?name=closing", "PUT", json.dumps(data).encode())[0] == 200
    cfg.unlink()
    j = json.loads(req(base + "/api/projects")[1])
    assert [p["name"] for p in j["projects"]] == ["closing"]


def test_upload_image_for_korean_name(server):
    base, _, root = server
    code, body = req(base + "/api/upload/" + urllib.parse.quote("마무리_s01") + ".png", "POST", b"\x89PNG")
    assert code == 200 and json.loads(body)["image"] == "assets/scenes/마무리_s01.png"
    assert (root / "assets" / "scenes" / "마무리_s01.png").read_bytes() == b"\x89PNG"
