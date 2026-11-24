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


def test_globe_counts_and_featured_names_persist_through_editor(server):
    base, _, _ = server
    project = globe_project(["Region\tCountry\tCity", "Asia-Pacific\tKorea\tSeoul"])
    goal = base + "/api/config?name=ambassadors"
    assert req(goal, "PUT", json.dumps(project).encode())[0] == 200
    data = json.loads(req(goal)[1])
    data["scenes"][0]["globe"]["regions"][0]["countries"][0]["count"] = 7
    row = data["scenes"][0]["globe"]["regions"][0]["countries"][0]
    row["featured_names"] = ["  James Yeon  "]
    assert req(goal, "PUT", json.dumps(data).encode())[0] == 200
    row["featured_names"] = ["James Yeon"]
    assert json.loads(req(goal)[1]) == data


def test_city_details_persist_through_editor(server):
    base, _, _ = server
    project = globe_project(["Region\tCountry\tCity", "Asia-Pacific\tKorea\tSeoul"])
    globe = project["scenes"][0]["globe"]
    city = {"name": "서울", "country": "South Korea", "count": 1, "lat": 37.57, "lon": 126.98}
    globe["regions"][0]["cities"] = [city]
    url = base + "/api/config?name=ambassadors"
    assert req(url, "PUT", json.dumps(project).encode())[0] == 200
    assert json.loads(req(url)[1]) == project
    city["lat"] = 91
    assert req(url, "PUT", json.dumps(project).encode())[0] == 400


def test_orbit_end_hold_is_editable_and_validated(server):
    base, _, _ = server
    project = globe_project(["Region\tCountry\tCity", "Asia-Pacific\tKorea\tSeoul"])
    globe = project["scenes"][0]["globe"]
    url = base + "/api/config?name=ambassadors"
    for seconds in (0, 1.25):
        globe["end_hold"] = seconds
        assert req(url, "PUT", json.dumps(project).encode())[0] == 200
        assert json.loads(req(url)[1])["scenes"][0]["globe"]["end_hold"] == seconds
    for invalid in (-1, True, "3", float("inf")):
        globe["end_hold"] = invalid
        assert req(url, "PUT", json.dumps(project).encode())[0] == 400


def test_nader_reel_is_discoverable_and_editable_as_a_separate_project(server):
    base, default, _ = server
    for name in ("ambassadors", "ambassadors-nader"):
        project = config.DEFAULT_CONFIG.with_name(f"{name}.json")
        shutil.copy(project, default.parent)

    listed = json.loads(req(base + "/api/projects")[1])
    assert {project["name"] for project in listed["projects"]} >= {"ambassadors", "ambassadors-nader"}
    original_url = base + "/api/config?name=ambassadors"
    nader_url = original_url + "-nader"
    original = json.loads(req(original_url)[1])
    variant = json.loads(req(nader_url)[1])
    clip = variant["scenes"].pop()
    assert variant == original
    assert (clip["id"], clip["video"], clip["type"]) == (
        "nader-dabit", "assets/footage/nader-dabit-welcome.mp4", "clip")
    assert clip["subtitle_font_size"] == original["scenes"][-1]["subtitle_font_size"]
    cues = clip["subtitles"]
    assert len(cues) == 17
    assert [cue["start"] for cue in cues[:3]] == [0, 0.72, 1.94]
    assert [cue["end"] for cue in cues[:-1]] == [cue["start"] for cue in cues[1:]]
    assert cues[-1]["end"] == 59.26 < clip["duration"]

    variant["scenes"].insert(-1, clip)
    cues[0]["text"] = "안녕하세요, 여러분!"
    assert req(nader_url, "PUT", json.dumps(variant).encode())[0] == 200
    assert json.loads(req(nader_url)[1]) == variant
    assert json.loads(req(original_url)[1]) == original


def test_nader_welcome_is_a_single_editable_clip_with_the_same_subtitles(server):
    base, default, _ = server
    for name in ("nader-welcome", "ambassadors-nader"):
        shutil.copy(config.DEFAULT_CONFIG.with_name(f"{name}.json"), default.parent)
    listed = json.loads(req(base + "/api/projects")[1])
    assert "nader-welcome" in {project["name"] for project in listed["projects"]}

    url = base + "/api/config?name=nader-welcome"
    standalone = json.loads(req(url)[1])
    reel_url = base + "/api/config?name=ambassadors-nader"
    reel = json.loads(req(reel_url)[1])
    assert standalone["scenes"] == [reel["scenes"][-1]]
    clip = standalone["scenes"][0]
    assert (clip["id"], clip["type"], len(clip["subtitles"])) == ("nader-dabit", "clip", 17)

    clip["subtitles"][0]["text"] = "안녕하세요, 여러분!"
    assert req(url, "PUT", json.dumps(standalone).encode())[0] == 200
    assert json.loads(req(url)[1]) == standalone
    assert json.loads(req(reel_url)[1]) == reel


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


def test_mp4_serves_byte_ranges(server):
    base, _, root = server
    (root / "out").mkdir()
    (root / "out" / "preview.mp4").write_bytes(b"0123456789")
    url = base + "/files/out/preview.mp4?timestamp=1"
    for header, status, content_range, body in (
        ("", 200, None, b"0123456789"),
        ("bytes=0-0", 206, "bytes 0-0/10", b"0"),
        ("bytes=4-", 206, "bytes 4-9/10", b"456789"),
        ("bytes=-2", 206, "bytes 8-9/10", b"89"),
        ("bytes=7-15", 206, "bytes 7-9/10", b"789"),
        ("bytes=10-", 416, "bytes */10", b""),
        ("bytes=0-1,3-5", 200, None, b"0123456789"),
    ):
        request = urllib.request.Request(url, headers={"Range": header} if header else {})
        try:
            response = urllib.request.urlopen(request)
        except urllib.error.HTTPError as e:
            response = e
        with response:
            assert response.status == status
            assert response.headers["Accept-Ranges"] == "bytes"
            assert response.headers["Content-Length"] == str(len(body))
            assert response.headers["Content-Range"] == content_range
            assert response.read() == body


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


@pytest.mark.parametrize("preview", [False, True])
def test_render_preflight_lists_missing_clips_for_selected_project(server, monkeypatch, preview):
    base, default, root = server
    parse = config.parse
    monkeypatch.setattr(config, "parse", lambda data: parse(data, base_dir=root))
    for name in ("ambassadors", "ambassadors-nader"):
        shutil.copy(config.DEFAULT_CONFIG.with_name(f"{name}.json"), default.parent)
    calls = []
    monkeypatch.setattr(editor.RenderJob, "start", lambda _, *args: calls.append(args) or True)
    url = base + "/api/render?name=ambassadors" + ("&preview=1" if preview else "")
    expected = [
        "assets/footage/ambassador-nikkie.mp4",
        "assets/footage/ambassador-colombia.mp4",
        "assets/footage/ambassador-abu-dhabi.mp4",
    ]

    code, body = req(url, "POST", b"")
    assert code == 400
    assert json.loads(body) == {
        "error": "원본 영상 파일이 없습니다 / Missing source clips",
        "missing_clips": expected,
    }
    assert not calls

    (root / "assets" / "footage").mkdir()
    (root / expected[0]).touch()
    code, body = req(url, "POST", b"")
    assert code == 400
    assert json.loads(body)["missing_clips"] == expected[1:]
    assert not calls

    for path in expected[1:]:
        (root / path).touch()
    assert req(url, "POST", b"")[0] == 202
    assert calls == [(default.with_name("ambassadors.json"),
                      "out/preview-ambassadors.mp4" if preview else "out/devin-meetup-seoul-ambassadors.mp4",
                      preview)]


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
