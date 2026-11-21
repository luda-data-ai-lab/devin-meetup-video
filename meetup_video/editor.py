"""Local browser editor for content/scenes.json with a render button (stdlib only)."""
import json
import os
import re
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import config
from .render import Renderer

STATIC = Path(__file__).resolve().parent / "static"
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}
MUSIC_EXT = {".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".wav": "audio/wav"}
NAME = re.compile(r"[\w\-]{1,40}")


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


def outputs(name, default):
    if name == default:
        return "out/devin-meetup-seoul.mp4", "out/preview.mp4"
    return f"out/devin-meetup-seoul-{name}.mp4", f"out/preview-{name}.mp4"


def make_handler(cfg_path, job):
    cfg_path = Path(cfg_path)
    content, default = cfg_path.parent, cfg_path.stem
    save_lock = threading.Lock()

    def project(query):
        name = urllib.parse.parse_qs(query).get("name", [default])[0]
        if name == default:
            return name, cfg_path
        if not NAME.fullmatch(name):
            raise ValueError("이름은 글자·숫자·_·- 40자 이내 / name: letters, digits, _ or -, up to 40")
        return name, content / f"{name}.json"

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

        def local_request(self):
            host = self.headers.get("Host", "")
            if host.rsplit(":", 1)[0] not in ("127.0.0.1", "localhost"):
                return False
            origin = self.headers.get("Origin")
            return origin is None or origin == f"http://{host}"

        def file(self, p, ctype):
            if not p.is_file():
                return self.send(404, {"error": "not found"})
            self.send(200, p.read_bytes(), ctype)

        def do_GET(self):
            path, _, query = self.path.partition("?")
            path = urllib.parse.unquote(path)
            if path == "/":
                return self.file(STATIC / "editor.html", "text/html; charset=utf-8")
            if path == "/api/projects":
                items = []
                for p in sorted({cfg_path, *(p for p in content.glob("*.json") if NAME.fullmatch(p.stem))}):
                    try:
                        qr = bool(json.loads(p.read_text(encoding="utf-8")).get("ending", {}).get("show_qr"))
                    except (OSError, ValueError):
                        continue
                    items.append({"name": p.stem, "qr": qr})
                items.sort(key=lambda i: (i["name"] != default, i["name"]))
                return self.send(200, {"projects": items, "default": default})
            if path == "/api/config":
                try:
                    _, p = project(query)
                except ValueError as e:
                    return self.send(400, {"error": str(e)})
                return self.file(p, "application/json; charset=utf-8")
            if path == "/api/status":
                return self.send(200, job.state)
            m = re.fullmatch(r"/manual/(ko|en)", path)
            if m:
                return self.file(config.ROOT / "docs" / f"manual_{m[1]}.md", "text/plain; charset=utf-8")
            m = re.fullmatch(r"/files/((?:assets/scenes|assets/music|out)/[\w.\-]+)", path)
            if m:
                p = config.ROOT / m[1]
                ext = p.suffix.lower()
                ctype = "video/mp4" if ext == ".mp4" else MUSIC_EXT.get(ext) or f"image/{ext.lstrip('.').replace('jpg', 'jpeg')}"
                return self.file(p, ctype)
            self.send(404, {"error": "not found"})

        def do_PUT(self):
            if not self.local_request():
                return self.send(403, {"error": "forbidden origin"})
            path, _, query = self.path.partition("?")
            if path != "/api/config":
                return self.send(404, {"error": "not found"})
            try:
                _, dest = project(query)
                data = json.loads(self.body())
                config.parse(data)
            except (ValueError, TypeError, KeyError) as e:
                return self.send(400, {"error": str(e)})
            with save_lock:
                tmp = dest.with_suffix(".json.tmp")
                tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                os.replace(tmp, dest)
            self.send(200, {"ok": True})

        def do_POST(self):
            if not self.local_request():
                return self.send(403, {"error": "forbidden origin"})
            path, _, query = self.path.partition("?")
            if path == "/api/render":
                try:
                    name, src = project(query)
                except ValueError as e:
                    return self.send(400, {"error": str(e)})
                if not src.is_file():
                    return self.send(404, {"error": "저장 후 렌더하세요 / save first"})
                preview = "preview=1" in query
                final, prev = outputs(name, default)
                out = prev if preview else final
                if not job.start(src, out, preview):
                    return self.send(409, {"error": "render already running"})
                return self.send(202, {"ok": True, "output": out})
            m = re.fullmatch(r"/api/upload-music/([\w\-]+)(\.\w+)", path)
            if m:
                if m[2].lower() not in MUSIC_EXT:
                    return self.send(400, {"error": "mp3/m4a/wav only"})
                dest = config.ROOT / "assets" / "music" / f"{m[1]}{m[2].lower()}"
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(self.body())
                return self.send(200, {"ok": True, "file": f"assets/music/{dest.name}"})
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
