"""Frame composition and MP4 encoding (Pillow + ffmpeg)."""
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

from . import fonts
from .providers import get_provider

TYPE_CPS = 22
BRAND = {"cognition": "assets/brand/logo_cognition_white.png", "devin": "assets/brand/logo_devin_white.png"}


class Renderer:
    def __init__(self, cfg, cache_dir=None):
        self.cfg = cfg
        self.W, self.H = cfg.width, cfg.height
        self.k = self.W / 1920
        self.cache_dir = Path(cache_dir or cfg.path("out/cache"))
        self.provider = get_provider(cfg.image_provider)
        self._bases = {}
        self._logos = {}
        self._last = {}

    def u(self, v):
        return int(round(v * self.k))

    # ---------- images ----------
    def base(self, scene):
        if scene.id in self._bases:
            return self._bases[scene.id]
        p = self.cfg.path(scene.image) if scene.image else None
        if not p or not p.exists():
            p = self.provider.generate(scene, (self.W, self.H), self.cache_dir / f"{scene.id}.png")
        img = Image.open(p).convert("RGB")
        s = max(self.W / img.width, self.H / img.height) * max(scene.zoom)
        img = img.resize((int(img.width * s) + 1, int(img.height * s) + 1), Image.LANCZOS)
        self._bases[scene.id] = img
        return img

    def camera(self, scene, t):
        base = self.base(scene)
        z0, z1 = scene.zoom
        z = z0 + (z1 - z0) * t
        zmax = max(scene.zoom)
        w, h = min(self.W * zmax / z, base.width), min(self.H * zmax / z, base.height)
        cx = base.width / 2 + scene.pan * (t - 0.5) * base.width * 0.05
        cx = min(max(cx, w / 2), base.width - w / 2)
        cy = base.height / 2
        box = (int(cx - w / 2), int(cy - h / 2), int(cx - w / 2 + w), int(cy - h / 2 + h))
        return base.crop(box).resize((self.W, self.H), Image.BILINEAR).convert("RGBA")

    def logo(self, name, h):
        if (name, h) not in self._logos:
            im = Image.open(self.cfg.path(BRAND[name])).convert("RGBA")
            self._logos[name, h] = im.resize((max(1, int(im.width * h / im.height)), h), Image.LANCZOS)
        return self._logos[name, h]

    # ---------- overlays ----------
    def draw_mixed(self, d, xy, text, fill, size):
        x, y = xy
        m, kf = fonts.mono(size), fonts.kr(size - 2)
        for c in text:
            f = kf if ord(c) >= 0x1100 else m
            d.text((x, y), c, font=f, fill=fill)
            x += f.getlength(c)
        return x

    def terminal(self, frame, lines, t):
        if not lines:
            return frame
        u, a = self.u, self.cfg.accent
        ov = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        x0, y0 = u(70), u(1010) - u(70) - u(52) * len(lines)
        x1, y1 = u(900), u(1010)
        d.rounded_rectangle((x0, y0, x1, y1), u(22), fill=(12, 16, 22, 215), outline=a + (255,), width=max(1, u(3)))
        for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
            d.ellipse((x0 + u(24 + i * 34), y0 + u(20), x0 + u(46 + i * 34), y0 + u(42)), fill=c)
        d.text((x0 + u(140), y0 + u(14)), "devin@seoul ~", font=fonts.mono(u(26)), fill=(150, 160, 170))
        shown = int(max(0.0, t - 0.4) * TYPE_CPS)
        y = y0 + u(70)
        for i, ln in enumerate(lines):
            if shown <= 0 and i > 0:
                break
            part = ln[:max(0, shown)]
            col = (235, 240, 245) if ln.startswith("$") else (120, 240, 200)
            xe = self.draw_mixed(d, (x0 + u(28), y), part, col, u(32))
            if shown <= len(ln):
                d.rectangle((xe + u(4), y + u(4), xe + u(22), y + u(40)), fill=a + (255,))
            shown -= len(ln)
            y += u(52)
        return Image.alpha_composite(frame, ov)

    def captions(self, frame, scene, t):
        if not (scene.caption_ko or scene.caption_en):
            return frame
        a = min(1.0, max(0.0, (t - 0.3) / 0.4), max(0.0, (scene.duration - t) / 0.4))
        if a <= 0:
            return frame
        u = self.u
        ov = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        fk, fe = fonts.kr(u(56)), fonts.kr(u(30))
        wk = d.textlength(scene.caption_ko, font=fk)
        we = d.textlength(scene.caption_en, font=fe)
        bw = max(wk, we) + u(80)
        d.rounded_rectangle(((self.W - bw) / 2, u(50), (self.W + bw) / 2, u(210)), u(20), fill=(0, 0, 0, int(150 * a)))
        d.text(((self.W - wk) / 2, u(64)), scene.caption_ko, font=fk, fill=(255, 255, 255, int(255 * a)))
        d.text(((self.W - we) / 2, u(152)), scene.caption_en, font=fe, fill=self.cfg.accent + (int(255 * a),))
        return Image.alpha_composite(frame, ov)

    def ending(self, frame, t):
        e, u, W = self.cfg.ending, self.u, self.W
        a = min(1.0, t / 0.6)
        ov = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        d.rectangle((0, 0, W, self.H), fill=(0, 0, 0, int(190 * a)))
        lh = u(84)
        cog, dev = self.logo("cognition", lh), self.logo("devin", lh)
        fx = fonts.kr(u(70))
        gap = u(50)
        xw = d.textlength("×", font=fx)
        left = u(160)
        x = left
        for lg in (cog, None, dev):
            if lg is None:
                d.text((x + gap, u(250) - u(6)), "×", font=fx, fill=(255, 255, 255, int(255 * a)))
                x += gap * 2 + xw
                continue
            l = lg.copy()
            l.putalpha(l.getchannel("A").point(lambda v: int(v * a)))
            ov.alpha_composite(l, (int(x), u(250)))
            x += lg.width
        d.text((left, u(400)), e.get("title", ""), font=fonts.kr(u(110)), fill=(255, 255, 255, int(255 * a)))
        d.text((left, u(560)), e.get("date", ""), font=fonts.kr(u(60)), fill=self.cfg.accent + (int(255 * a),))
        d.text((left, u(660)), e.get("venue", ""), font=fonts.kr(u(40)), fill=(220, 220, 220, int(255 * a)))
        q = (W - u(560), u(250), W - u(160), u(650))
        d.rounded_rectangle(q, u(24), fill=(255, 255, 255, int(235 * a)))
        qf = fonts.kr(u(64))
        msg = "QR" if not e.get("qr_url") else "QR ✓"
        d.text(((q[0] + q[2] - d.textlength(msg, font=qf)) / 2, u(410)), msg, font=qf, fill=(20, 20, 20, int(255 * a)))
        for i, key in enumerate(("qr_label_ko", "qr_label_en")):
            f = fonts.kr(u(44 if i == 0 else 30))
            txt = e.get(key, "")
            d.text(((q[0] + q[2] - d.textlength(txt, font=f)) / 2, u(680 + i * 64)), txt, font=f,
                   fill=(255, 255, 255, int(255 * a)))
        return Image.alpha_composite(frame, ov)

    # ---------- timeline ----------
    def last_frame(self, i):
        if i not in self._last:
            s = self.cfg.scenes[i]
            self._last[i] = self.scene_frame(i, s.duration)
        return self._last[i]

    def scene_frame(self, i, t):
        scene = self.cfg.scenes[i]
        if scene.type == "ending":
            if scene.image:
                bg = self.camera(scene, 0.5)
            elif i > 0:
                bg = self.last_frame(i - 1)
            else:
                bg = Image.new("RGBA", (self.W, self.H), (8, 10, 20, 255))
            return self.ending(bg, t)
        fr = self.camera(scene, t / scene.duration)
        fr = self.captions(fr, scene, t)
        return self.terminal(fr, scene.terminal, t)

    def locate(self, gt):
        start = 0.0
        last = len(self.cfg.scenes) - 1
        for i, s in enumerate(self.cfg.scenes):
            if gt < start + s.duration or i == last:
                return i, min(gt - start, s.duration)
            start += s.duration

    def frame_at(self, gt):
        i, t = self.locate(gt)
        fr = self.scene_frame(i, t)
        tr = self.cfg.transition_sec
        if i > 0 and t < tr and self.cfg.scenes[i].type != "ending":
            fr = Image.blend(self.last_frame(i - 1), fr, t / tr)
        return fr.convert("RGB")

    def render(self, out, progress=None):
        if not shutil.which("ffmpeg"):
            raise RuntimeError("ffmpeg not found on PATH")
        out = Path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        n = int(round(self.cfg.total_duration * self.cfg.fps))
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{self.W}x{self.H}",
               "-r", str(self.cfg.fps), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
               "-movflags", "+faststart", str(out)]
        ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        try:
            for f in range(n):
                ff.stdin.write(self.frame_at(f / self.cfg.fps).tobytes())
                if progress and f % self.cfg.fps == 0:
                    progress(f, n)
        finally:
            ff.stdin.close()
            ff.wait()
        if ff.returncode:
            raise RuntimeError(f"ffmpeg failed ({ff.returncode})")
        return out
