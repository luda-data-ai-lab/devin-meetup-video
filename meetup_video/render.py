"""Frame composition and MP4 encoding (Pillow + ffmpeg)."""
import math
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw

from . import fonts
from .providers import get_provider

TYPE_CPS = 22


def is_hangul(c):
    o = ord(c)
    return 0x1100 <= o <= 0x11FF or 0x3130 <= o <= 0x318F or 0xAC00 <= o <= 0xD7AF
BRAND = {"cognition": "assets/brand/logo_cognition_white.png", "devin": "assets/brand/logo_devin_white.png"}


SPRITE_FILES = {"devin": "assets/characters/devin.png", "bots": "assets/characters/bots.png"}
FACE_MODEL = "assets/models/yunet.onnx"


class VideoSource:
    """Sequential ffmpeg reader that returns cover-fit RGB frames; seeks by restarting."""

    def __init__(self, path, start, size, fps):
        self.path, self.start, self.size, self.fps = str(path), start, size, fps
        self.proc, self.next, self.frame = None, 0, None

    def _open(self, idx):
        self.close()
        w, h = self.size
        vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={self.fps}"
        self.proc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-ss", str(self.start + idx / self.fps), "-i", self.path,
                                      "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL)
        self.next = idx

    def get(self, idx):
        if self.proc is None or idx < self.next - 1 or idx > self.next + self.fps:
            self._open(idx)
        n = self.size[0] * self.size[1] * 3
        while self.next <= idx:
            b = self.proc.stdout.read(n)
            if len(b) < n:
                break
            self.frame = Image.frombytes("RGB", self.size, b)
            self.next += 1
        if self.frame is None:
            raise RuntimeError(f"no frames decoded from {self.path}")
        return self.frame

    def close(self):
        if self.proc:
            self.proc.kill()
            self.proc.wait()
            self.proc = None


class FaceBlur:
    def __init__(self, model):
        try:
            import cv2
            import numpy as np
        except ImportError as e:
            raise RuntimeError("blur_faces needs opencv-python-headless (pip install -r requirements.txt)") from e
        self.cv2, self.np = cv2, np
        self.det = cv2.FaceDetectorYN.create(str(model), "", (320, 320), 0.6)

    def __call__(self, img):
        cv2, np = self.cv2, self.np
        a = np.array(img)
        h, w = a.shape[:2]
        self.det.setInputSize((w, h))
        _, faces = self.det.detect(cv2.cvtColor(a, cv2.COLOR_RGB2BGR))
        for row in ([] if faces is None else faces):
            x, y, fw, fh = (int(v) for v in row[:4])
            p = int(0.35 * max(fw, fh))
            x0, y0, x1, y1 = max(0, x - p), max(0, y - p), min(w, x + fw + p), min(h, y + fh + p)
            if x1 > x0 and y1 > y0:
                k = max(15, (max(x1 - x0, y1 - y0) // 2) | 1)
                a[y0:y1, x0:x1] = cv2.GaussianBlur(a[y0:y1, x0:x1], (k, k), 0)
        return Image.fromarray(a)


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
        self._videos = {}
        self._sprites = {}
        self._blur = None

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

    def video_frame(self, scene, t):
        if scene.id not in self._videos:
            p = self.cfg.path(scene.video)
            if not p.exists():
                if not scene.video_url:
                    raise FileNotFoundError(f"scene {scene.id}: {scene.video} not found and no video_url")
                p.parent.mkdir(parents=True, exist_ok=True)
                part = p.with_name(p.name + ".part")
                urllib.request.urlretrieve(scene.video_url, part)
                os.replace(part, p)
            self._videos[scene.id] = VideoSource(p, scene.video_start, (self.W, self.H), self.cfg.fps)
        fr = self._videos[scene.id].get(int(round(t * self.cfg.fps)))
        if scene.blur_faces:
            if self._blur is None:
                self._blur = FaceBlur(self.cfg.path(FACE_MODEL))
            fr = self._blur(fr)
        z = max(1.0, scene.zoom[0] + (scene.zoom[1] - scene.zoom[0]) * (t / scene.duration))
        if z > 1.001:
            w, h = self.W / z, self.H / z
            cx = self.W / 2 + scene.pan * (t / scene.duration - 0.5) * self.W * 0.05
            cx = min(max(cx, w / 2), self.W - w / 2)
            fr = fr.crop((int(cx - w / 2), int((self.H - h) / 2), int(cx + w / 2), int((self.H + h) / 2))).resize((self.W, self.H), Image.BILINEAR)
        return fr.convert("RGBA")

    def sprite(self, name):
        if name not in self._sprites:
            im = Image.open(self.cfg.path(SPRITE_FILES[name])).convert("RGBA")
            solid = im.getchannel("A").point(lambda v: 255 if v > 16 else 0)
            self._sprites[name] = im.crop(solid.getbbox())
        return self._sprites[name]

    def characters(self, frame, scene, t):
        if not scene.characters:
            return frame
        u = min(1.0, t / scene.duration)
        e = u * u * (3 - 2 * u)
        for i, c in enumerate(scene.characters):
            x0, x1 = c.get("x", [0.5, 0.5])
            h0, h1 = c.get("h", [0.4, 0.4])
            cx, h = (x0 + (x1 - x0) * e) * self.W, (h0 + (h1 - h0) * e) * self.H
            feet = c.get("y", 0.95) * self.H
            sp = self.sprite(c["sprite"])
            im = sp.resize((max(1, int(sp.width * h / sp.height)), max(1, int(h))), Image.BILINEAR)
            if c.get("walk", True):
                im = im.rotate(math.sin(2 * math.pi * 0.8 * t + i) * 3, resample=Image.BICUBIC, expand=True)
            bob = abs(math.sin(2 * math.pi * 1.6 * t + i)) * h * 0.025 if c.get("walk", True) else 0
            sh = Image.new("RGBA", frame.size, (0, 0, 0, 0))
            ImageDraw.Draw(sh).ellipse((cx - im.width * 0.38, feet - h * 0.03, cx + im.width * 0.38, feet + h * 0.03), fill=(0, 0, 0, 120))
            frame = Image.alpha_composite(frame, sh)
            frame.alpha_composite(im, (int(cx - im.width / 2), int(feet - im.height - bob)))
        return frame

    def camera(self, scene, t):
        if scene.type == "video":
            return self.video_frame(scene, t * scene.duration)
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
    def text_width(self, text, size):
        img = Image.new("RGBA", (1, 1))
        return self.draw_mixed(ImageDraw.Draw(img), (0, 0), text, (0, 0, 0), size)

    def draw_mixed(self, d, xy, text, fill, size):
        x, y = xy
        m, kf, sf = fonts.mono(size), fonts.kr(size), fonts.symbol(size)
        kr = [is_hangul(c) for c in text]
        for i, c in enumerate(text):
            near_kr = c == " " and ((i > 0 and kr[i - 1]) or (i + 1 < len(text) and kr[i + 1]))
            f = kf if kr[i] or near_kr else sf if ord(c) >= 0x2000 else m
            d.text((x, y), c, font=f, fill=fill)
            x += f.getlength(c)
        return x

    def terminal(self, frame, lines, t):
        if not lines:
            return frame
        u, a = self.u, self.cfg.accent
        ov = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        size, step = u(42), u(64)
        width = max(self.text_width(ln, size) for ln in lines)
        x0, y0 = u(60), u(1020) - u(80) - step * len(lines)
        x1, y1 = min(self.W - u(60), x0 + max(u(860), width + u(90))), u(1020)
        d.rounded_rectangle((x0, y0, x1, y1), u(22), fill=(8, 11, 16, 235), outline=a + (255,), width=max(1, u(3)))
        for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
            d.ellipse((x0 + u(24 + i * 34), y0 + u(20), x0 + u(46 + i * 34), y0 + u(42)), fill=c)
        d.text((x0 + u(140), y0 + u(14)), "devin@seoul ~", font=fonts.mono(u(28)), fill=(185, 195, 205))
        shown = int(max(0.0, t - 0.4) * TYPE_CPS)
        y = y0 + u(72)
        for i, ln in enumerate(lines):
            if shown <= 0 and i > 0:
                break
            part = ln[:max(0, shown)]
            col = (255, 255, 255) if ln.startswith("$") else (140, 255, 215)
            xe = self.draw_mixed(d, (x0 + u(30), y), part, col, size)
            if shown <= len(ln):
                d.rectangle((xe + u(4), y + u(6), xe + u(26), y + u(50)), fill=a + (255,))
            shown -= len(ln)
            y += step
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
        d.text((left, u(680)), e.get("welcome", ""), font=fonts.kr(u(52)), fill=(235, 240, 245, int(255 * a)))
        if e.get("show_qr") and e.get("qr_url"):
            import qrcode
            q = qrcode.make(e["qr_url"], border=2).get_image().convert("RGBA").resize((u(360), u(360)), Image.NEAREST)
            q.putalpha(int(255 * a))
            ov.alpha_composite(q, (W - u(520), u(250)))
            f = fonts.kr(u(40))
            txt = e.get("qr_label", "")
            d.text((W - u(340) - d.textlength(txt, font=f) / 2, u(640)), txt, font=f, fill=(255, 255, 255, int(255 * a)))
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
        fr = self.characters(fr, scene, t)
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

    def music_args(self):
        m = self.cfg.music
        if not m["file"]:
            return []
        path = self.cfg.path(m["file"])
        if not path.is_file():
            raise RuntimeError(f"music file not found: {m['file']}")
        total = self.cfg.total_duration
        fo = min(m["fade_out"], total)
        af = f"volume={m['volume']}"
        if m["fade_in"] > 0:
            af += f",afade=t=in:st=0:d={m['fade_in']}"
        if fo > 0:
            af += f",afade=t=out:st={total - fo}:d={fo}"
        return ["-ss", str(m["start"]), "-i", str(path), "-map", "0:v", "-map", "1:a",
                "-af", af + ",apad", "-c:a", "aac", "-b:a", "192k", "-t", str(total)]

    def render(self, out, progress=None):
        if not shutil.which("ffmpeg"):
            raise RuntimeError("ffmpeg not found on PATH")
        out = Path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        n = int(round(self.cfg.total_duration * self.cfg.fps))
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{self.W}x{self.H}",
               "-r", str(self.cfg.fps), "-i", "-", *self.music_args(), "-c:v", "libx264", "-pix_fmt", "yuv420p",
               "-crf", "20", "-movflags", "+faststart", str(out)]
        ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        try:
            for f in range(n):
                ff.stdin.write(self.frame_at(f / self.cfg.fps).tobytes())
                if progress and f % self.cfg.fps == 0:
                    progress(f, n)
        finally:
            ff.stdin.close()
            ff.wait()
            for v in self._videos.values():
                v.close()
        if ff.returncode:
            raise RuntimeError(f"ffmpeg failed ({ff.returncode})")
        return out
