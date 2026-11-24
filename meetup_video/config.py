import json
import math
import unicodedata
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
    globe: dict = field(default_factory=dict)
    subtitles: list = field(default_factory=list)
    subtitles_baked_in: bool = False
    subtitle_font_size: int = 49

    @property
    def timeline_duration(self):
        return self.duration + (self.globe.get("end_hold", 0) if self.type == "globe" else 0)


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
        return sum(s.timeline_duration for s in self.scenes)

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


def validate_globe(scene):
    g = scene.globe
    if not math.isfinite(scene.duration):
        raise ConfigError(f"scene {scene.id}: globe duration must be finite")
    regions = g.get("regions") if isinstance(g, dict) else None
    if not isinstance(regions, list) or not regions:
        raise ConfigError(f"scene {scene.id}: globe needs at least one region")
    hold = g.get("end_hold", 0)
    if type(hold) not in (int, float) or not 0 <= hold < math.inf or not math.isfinite(scene.timeline_duration):
        raise ConfigError(f"scene {scene.id}: globe end_hold must be a finite nonnegative number")
    for region in regions:
        validate_globe_region(scene.id, region)


def validate_globe_region(scene_id, region):
    if not isinstance(region, dict) or not isinstance(region.get("name"), str) or not region["name"].strip():
        raise ConfigError(f"scene {scene_id}: globe region needs a name")
    countries = region.get("countries")
    if not isinstance(countries, list) or not countries:
        raise ConfigError(f"scene {scene_id}: globe region needs at least one country")
    for key, limit in (("lat", 90), ("lon", 180)):
        coord = region.get(key)
        if type(coord) not in (int, float) or not -limit <= coord <= limit:
            raise ConfigError(f"scene {scene_id}: globe region {key} must be between {-limit} and {limit}")
    cities = region.get("cities", [])
    if not isinstance(cities, list):
        raise ConfigError(f"scene {scene_id}: globe cities must be a list")
    for city in cities:
        if not isinstance(city, dict):
            raise ConfigError(f"scene {scene_id}: each city must be an object")
        keys = ("name", "country", "roster_city") if "roster_city" in city else ("name", "country")
        for key in keys:
            value = city.get(key)
            if (not isinstance(value, str) or not value.strip()
                    or any(unicodedata.category(char) in ("Cc", "Zl", "Zp") for char in value)):
                raise ConfigError(f"scene {scene_id}: city {key} must be nonblank single-line text")
        if type(city.get("count")) is not int or city["count"] < 0:
            raise ConfigError(f"scene {scene_id}: city count must be a nonnegative integer")
        for key, limit in (("lat", 90), ("lon", 180)):
            coord = city.get(key)
            if type(coord) not in (int, float) or not -limit <= coord <= limit:
                raise ConfigError(f"scene {scene_id}: city {key} must be between {-limit} and {limit}")
    for row in countries:
        if not isinstance(row, dict):
            raise ConfigError(f"scene {scene_id}: globe country must be an object")
        country, count = row.get("country"), row.get("count")
        if not isinstance(country, str) or not country.strip():
            raise ConfigError(f"scene {scene_id}: globe country needs a name")
        if type(count) is not int or count < 0:
            raise ConfigError(f"scene {scene_id}: globe count must be a nonnegative integer")
        names = row.get("featured_names", [])
        if not isinstance(names, list) or any(
            not isinstance(name, str) or not name.strip()
            or any(unicodedata.category(char) in ("Cc", "Zl", "Zp") for char in name)
            for name in names
        ):
            raise ConfigError(f"scene {scene_id}: globe featured_names must be nonblank single-line names without control characters")
        if "featured_names" in row:
            row["featured_names"] = [name.strip() for name in names]


def validate_clip(scene):
    if not isinstance(scene.video, str) or not scene.video.strip():
        raise ConfigError(f"scene {scene.id}: clips need a video path")
    if not math.isfinite(scene.duration):
        raise ConfigError(f"scene {scene.id}: clip duration must be finite")
    if type(scene.video_start) not in (int, float) or not math.isfinite(scene.video_start) or scene.video_start < 0:
        raise ConfigError(f"scene {scene.id}: clip video_start must be a nonnegative number")
    if type(scene.subtitles_baked_in) is not bool or not isinstance(scene.subtitles, list):
        raise ConfigError(f"scene {scene.id}: invalid clip subtitles")
    if scene.subtitles_baked_in and scene.subtitles:
        raise ConfigError(f"scene {scene.id}: cannot add subtitles to a clip with burned-in subtitles")
    if type(scene.subtitle_font_size) is not int or not 1 <= scene.subtitle_font_size <= 1080:
        raise ConfigError(f"scene {scene.id}: subtitle font size must be an integer from 1 to 1080")
    previous_end = 0
    for cue in scene.subtitles:
        if not isinstance(cue, dict):
            raise ConfigError(f"scene {scene.id}: invalid subtitle cue")
        start, end, text = cue.get("start"), cue.get("end"), cue.get("text")
        if (type(start) not in (int, float) or type(end) not in (int, float)
                or not previous_end <= start < end <= scene.duration):
            raise ConfigError(f"scene {scene.id}: subtitle times must be in order, non-overlapping, and within the clip")
        if not isinstance(text, str) or not text.strip():
            raise ConfigError(f"scene {scene.id}: subtitle text cannot be empty")
        previous_end = end


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
        if raw.get("type", "image") not in ("image", "video", "ending", "globe", "clip"):
            raise ConfigError(f"scene {raw['id']}: type must be image, video, ending, globe or clip")
        if raw.get("type") == "video" and not raw.get("video"):
            raise ConfigError(f"scene {raw['id']}: video scenes need a video path")
        for c in raw.get("characters", []):
            if c.get("sprite") not in SPRITES:
                raise ConfigError(f"scene {raw['id']}: sprite must be one of {', '.join(SPRITES)}")
        s = Scene(**{k: v for k, v in raw.items() if k in Scene.__dataclass_fields__})
        s.duration = float(s.duration)
        if s.type == "globe":
            validate_globe(s)
        if s.type == "clip":
            validate_clip(s)
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
