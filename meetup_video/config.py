import json
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "content" / "scenes.json"


SPRITES = ("devin", "bots")


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
    video: str = ""
    video_url: str = ""
    video_start: float = 0.0
    blur_faces: bool = False
    characters: list = field(default_factory=list)


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
    music: dict
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
    return parse(data)


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
        if raw.get("type", "image") not in ("image", "video", "ending"):
            raise ConfigError(f"scene {raw['id']}: type must be image, video or ending")
        if raw.get("type") == "video" and not raw.get("video"):
            raise ConfigError(f"scene {raw['id']}: video scenes need a video path")
        for c in raw.get("characters", []):
            if c.get("sprite") not in SPRITES:
                raise ConfigError(f"scene {raw['id']}: sprite must be one of {', '.join(SPRITES)}")
        s = Scene(**{k: v for k, v in raw.items() if k in Scene.__dataclass_fields__})
        s.duration = float(s.duration)
        try:
            s.zoom = tuple(float(z) for z in s.zoom)
        except (TypeError, ValueError):
            s.zoom = ()
        if len(s.zoom) != 2 or min(s.zoom) <= 0:
            raise ConfigError(f"scene {raw['id']}: zoom must be two numbers > 0")
        scenes.append(s)
    if not scenes:
        raise ConfigError("at least one scene is required")
    music = parse_music(data.get("music") or {})
    return Config(
        width=int(video.get("width", 1920)),
        height=int(video.get("height", 1080)),
        fps=int(video.get("fps", 30)),
        accent=hex_color(video.get("accent", "#2DD4BF")),
        transition_sec=float(video.get("transition_sec", 0.5)),
        image_provider=data.get("image_provider", "mock"),
        ending=data.get("ending", {}),
        scenes=scenes,
        music=music,
        base_dir=Path(base_dir),
    )


def parse_music(raw):
    m = {"file": str(raw.get("file") or "")}
    for key, default, hi in (("volume", 0.8, 2.0), ("fade_in", 0.5, None), ("fade_out", 4.0, None), ("start", 0.0, None)):
        try:
            v = float(raw.get(key, default))
        except (TypeError, ValueError):
            raise ConfigError(f"music.{key} must be a number")
        if v < 0 or (hi is not None and v > hi):
            raise ConfigError(f"music.{key} must be between 0 and {hi}" if hi else f"music.{key} must be >= 0")
        m[key] = v
    return m
