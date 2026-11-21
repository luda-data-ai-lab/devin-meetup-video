import json
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "content" / "scenes.json"


class ConfigError(ValueError):
    pass


@dataclass
class Scene:
    id: str
    duration: float
    type: str = "image"
    image: str = ""
    prompt: str = ""
    caption_ko: str = ""
    caption_en: str = ""
    terminal: list = field(default_factory=list)
    zoom: tuple = (1.0, 1.1)
    pan: float = 0.0


@dataclass
class Config:
    width: int
    height: int
    fps: int
    accent: tuple
    transition_sec: float
    image_provider: str
    ending: dict
    scenes: list
    base_dir: Path

    @property
    def total_duration(self):
        return sum(s.duration for s in self.scenes)

    def path(self, rel):
        p = Path(rel)
        return p if p.is_absolute() else self.base_dir / p


def hex_color(value):
    v = value.lstrip("#")
    if len(v) != 6:
        raise ConfigError(f"color must be #RRGGBB: {value}")
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))


def load(path=DEFAULT_CONFIG):
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    return parse(data, base_dir=path.resolve().parent.parent)


def parse(data, base_dir=ROOT):
    video = data.get("video", {})
    scenes = []
    seen = set()
    for raw in data.get("scenes", []):
        if not raw.get("id"):
            raise ConfigError("every scene needs an id")
        if raw["id"] in seen:
            raise ConfigError(f"duplicate scene id: {raw['id']}")
        seen.add(raw["id"])
        if float(raw.get("duration", 0)) <= 0:
            raise ConfigError(f"scene {raw['id']}: duration must be > 0")
        if raw.get("type", "image") not in ("image", "ending"):
            raise ConfigError(f"scene {raw['id']}: type must be image or ending")
        s = Scene(**{k: v for k, v in raw.items() if k in Scene.__dataclass_fields__})
        s.duration = float(s.duration)
        s.zoom = tuple(s.zoom)
        scenes.append(s)
    if not scenes:
        raise ConfigError("at least one scene is required")
    return Config(
        width=int(video.get("width", 1920)),
        height=int(video.get("height", 1080)),
        fps=int(video.get("fps", 30)),
        accent=hex_color(video.get("accent", "#2DD4BF")),
        transition_sec=float(video.get("transition_sec", 0.5)),
        image_provider=data.get("image_provider", "mock"),
        ending=data.get("ending", {}),
        scenes=scenes,
        base_dir=Path(base_dir),
    )
