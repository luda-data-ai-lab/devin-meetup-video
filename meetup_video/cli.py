import argparse
import sys
from pathlib import Path

from . import config
from .render import Renderer


def load_env(path):
    import os
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m meetup_video")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render", help="render the MP4")
    r.add_argument("--config", default=str(config.DEFAULT_CONFIG))
    r.add_argument("--out", default="out/devin-meetup-seoul.mp4")
    r.add_argument("--preview", action="store_true", help="960x540, 15fps quick preview")
    s = sub.add_parser("still", help="save one frame as PNG")
    s.add_argument("--config", default=str(config.DEFAULT_CONFIG))
    s.add_argument("--at", type=float, required=True, help="time in seconds")
    s.add_argument("--out", default="out/still.png")
    e = sub.add_parser("edit", help="open the browser editor")
    e.add_argument("--config", default=str(config.DEFAULT_CONFIG))
    e.add_argument("--port", type=int, default=8765)
    a = ap.parse_args(argv)

    load_env(config.ROOT / ".env")
    if a.cmd == "edit":
        from .editor import serve
        return serve(a.config, port=a.port)
    cfg = config.load(a.config)
    if getattr(a, "preview", False):
        cfg.width, cfg.height, cfg.fps = 960, 540, 15
    rd = Renderer(cfg)
    if a.cmd == "render":
        out = rd.render(a.out, progress=lambda f, n: print(f"\r{f * 100 // n:3d}%", end="", file=sys.stderr))
        print(f"\nsaved {out} ({cfg.total_duration:.0f}s)")
    else:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        rd.frame_at(a.at).save(a.out)
        print(f"saved {a.out}")
