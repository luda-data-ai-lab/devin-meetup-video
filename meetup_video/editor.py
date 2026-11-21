"""Local browser editor for content/scenes.json with a render button (stdlib only)."""
import json
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import config
from .render import Renderer

STATIC = Path(__file__).resolve().parent / "static"
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}


class RenderJob:
    def __init__(self):
        self.lock = threading.Lock()
        self.state = {"running": False, "progress": 0, "output": "", "error": ""}

    def start(self, cfg_path, out_rel, preview):
        with self.lock:
            if self.state["running"]:
                return False
            self.state = {"running": True, "progress": 0, "output": "", "error": ""}
        threading.Thread(target=self._run, args=(cfg_path, out_rel, preview), daemon=True).start()
        return True

    def _run(self, cfg_path, out_rel, preview):
        try:
            cfg = config.load(cfg_path)
            if preview:
                cfg.width, cfg.height, cfg.fps = 960, 540, 15
            Renderer(cfg).render(config.ROOT / out_rel, progress=lambda f, n: self.state.update(progress=f * 100 // n))
            self.state.update(progress=100, output=out_rel)
        except Exception as e:  # surfaced to the editor screen
            self.state.update(error=str(e))
        finally:
            self.state["running"] = False


def make_handler(cfg_path, job):
    cfg_path = Path(cfg_path)
    save_lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def send(self, code, body, ctype="application/json; charset=utf-8"):
            if isinstance(body, (dict, list)):
                body = json.dumps(body, ensure_ascii=False).encode()
            elif isinstance(body, str):
                body = body.encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def body(self):
            n = int(self.headers.get("Content-Length", 0))
            return self.rfile.read(n)

        def file(self, p, ctype):
            if not p.is_file():
                return self.send(404, {"error": "not found"})
            self.send(200, p.read_bytes(), ctype)

        def do_GET(self):
            path = self.path.split("?")[0]
            if path == "/":
                return self.file(STATIC / "editor.html", "text/html; charset=utf-8")
            if path == "/api/config":
                return self.send(200, json.loads(cfg_path.read_text(encoding="utf-8")))
            if path == "/api/status":
                return self.send(200, job.state)
            m = re.fullmatch(r"/manual/(ko|en)", path)
            if m:
                return self.file(config.ROOT / "docs" / f"manual_{m[1]}.md", "text/plain; charset=utf-8")
            m = re.fullmatch(r"/files/((?:assets/scenes|out)/[\w.\-]+)", path)
            if m:
                p = config.ROOT / m[1]
                ctype = "video/mp4" if p.suffix == ".mp4" else f"image/{p.suffix.lstrip('.').replace('jpg', 'jpeg')}"
                return self.file(p, ctype)
            self.send(404, {"error": "not found"})

        def do_PUT(self):
            if self.path != "/api/config":
                return self.send(404, {"error": "not found"})
            try:
                data = json.loads(self.body())
                config.parse(data)
            except (ValueError, TypeError, KeyError) as e:
                return self.send(400, {"error": str(e)})
            with save_lock:
                tmp = cfg_path.with_suffix(".json.tmp")
                tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                os.replace(tmp, cfg_path)
            self.send(200, {"ok": True})

        def do_POST(self):
            path, _, query = self.path.partition("?")
            if path == "/api/render":
                preview = "preview=1" in query
                out = "out/preview.mp4" if preview else "out/devin-meetup-seoul.mp4"
                if not job.start(cfg_path, out, preview):
                    return self.send(409, {"error": "render already running"})
                return self.send(202, {"ok": True, "output": out})
            m = re.fullmatch(r"/api/upload/([\w\-]+)(\.\w+)", path)
            if m:
                if m[2].lower() not in IMAGE_EXT:
                    return self.send(400, {"error": "png/jpg/webp only"})
                dest = config.ROOT / "assets" / "scenes" / f"{m[1]}{m[2].lower()}"
                dest.write_bytes(self.body())
                return self.send(200, {"ok": True, "image": f"assets/scenes/{dest.name}"})
            self.send(404, {"error": "not found"})

    return Handler


def serve(cfg_path=config.DEFAULT_CONFIG, host="127.0.0.1", port=8765):
    srv = ThreadingHTTPServer((host, port), make_handler(cfg_path, RenderJob()))
    print(f"Editor: http://{host}:{port}/")
    srv.serve_forever()
