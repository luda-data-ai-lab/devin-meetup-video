"""Scene image providers. Development and tests use MockProvider."""
import os
from PIL import Image, ImageDraw

from . import fonts


class MockProvider:
    name = "mock"

    def generate(self, scene, size, out_path):
        w, h = size
        img = Image.new("RGB", size)
        d = ImageDraw.Draw(img)
        seed = sum(map(ord, scene.id))
        c1 = (40 + seed % 60, 30 + seed * 7 % 80, 90 + seed * 3 % 120)
        c2 = (10, 12, 30)
        for y in range(h):
            k = y / h
            d.line([(0, y), (w, y)], fill=tuple(int(a * (1 - k) + b * k) for a, b in zip(c1, c2)))
        f = fonts.kr(max(12, h // 14))
        label = f"[mock] {scene.id}"
        d.text(((w - d.textlength(label, font=f)) / 2, h * 0.42), label, font=f, fill=(255, 255, 255))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path)
        return out_path


class OpenAIProvider:
    name = "openai"

    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        if not self.api_key or self.api_key.startswith("your-"):
            raise RuntimeError("OPENAI_API_KEY is not set in .env (IMAGE_PROVIDER=openai)")

    def generate(self, scene, size, out_path):
        raise NotImplementedError("Real image generation is added in a later slice; commit scene images to assets/scenes/")


def get_provider(name):
    name = os.environ.get("IMAGE_PROVIDER", name or "mock")
    if name == "mock":
        return MockProvider()
    if name == "openai":
        return OpenAIProvider()
    raise ValueError(f"unknown image provider: {name}")
