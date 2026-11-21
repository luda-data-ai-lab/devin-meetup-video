"""Cross-platform font lookup (Ubuntu, Windows, macOS)."""
from functools import lru_cache
from pathlib import Path
from PIL import ImageFont

KR_BOLD = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
    "C:/Windows/Fonts/malgunbd.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
]
MONO_BOLD = [
    str(Path.home() / ".local/share/fonts/JetBrainsMono-Bold.ttf"),
    "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf",
    "C:/Windows/Fonts/consolab.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "/System/Library/Fonts/Menlo.ttc",
]


def _first(paths):
    for p in paths:
        if Path(p).exists():
            return p
    return None


def _kr_index(path):
    if not path.endswith(".ttc"):
        return 0
    for i in range(10):
        try:
            if "KR" in " ".join(ImageFont.truetype(path, 10, index=i).getname()):
                return i
        except OSError:
            break
    return 0


@lru_cache(maxsize=None)
def kr(size):
    p = _first(KR_BOLD)
    if not p:
        raise RuntimeError("Korean font not found. Ubuntu: sudo apt install fonts-noto-cjk / Windows: Malgun Gothic")
    return ImageFont.truetype(p, size, index=_kr_index(p))


@lru_cache(maxsize=None)
def mono(size):
    p = _first(MONO_BOLD)
    return ImageFont.truetype(p, size) if p else ImageFont.load_default(size)
