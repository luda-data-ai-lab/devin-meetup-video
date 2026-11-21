import json
import shutil
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from meetup_video import config, editor


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


def req(url, method="GET", data=None):
    r = urllib.request.Request(url, data=data, method=method)
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


def test_save_valid_config_and_reject_invalid(server):
    base, cfg, _ = server
    data = json.loads(req(base + "/api/config")[1])
    data["ending"]["qr_url"] = "https://quiz.example/q"
    data["scenes"][0]["caption_ko"] = "새 자막"
    assert req(base + "/api/config", "PUT", json.dumps(data).encode())[0] == 200
    saved = json.loads(cfg.read_text(encoding="utf-8"))
    assert saved["ending"]["qr_url"] == "https://quiz.example/q" and saved["scenes"][0]["caption_ko"] == "새 자막"
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
