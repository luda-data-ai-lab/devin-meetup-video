import pytest
from PIL import ImageDraw

from meetup_video import config
from meetup_video.globe import frame, view_at
from meetup_video.render import Renderer
from meetup_video.roster import globe_project, read_roster


ROSTER = """Region\tCountry\tCity
N.A.\tUSA\tNYC
\tUSA\tNew York
\t\t
Asia-Pacific\tKorea\tSeoul
""".splitlines()


def test_roster_counts_rows_not_distinct_cities():
    assert list(read_roster(ROSTER))[:2] == [("N.A.", "United States", "New York City")] * 2
    scene = config.parse(globe_project(ROSTER)).scenes[0]
    assert [(r["name"], r["countries"]) for r in scene.globe["regions"]] == [
        ("North America", [{"country": "United States", "count": 2}]),
        ("Asia-Pacific", [{"country": "South Korea", "count": 1}]),
    ]


@pytest.mark.parametrize("bad", [-1, None, True, 1.5])
def test_globe_rejects_invalid_count(bad):
    data = globe_project(ROSTER)
    data["scenes"][0]["globe"]["regions"][0]["countries"][0]["count"] = bad
    with pytest.raises(config.ConfigError, match="globe count"):
        config.parse(data)


@pytest.mark.parametrize("bad", ["James Yeon", [None], [" "], ["James\nYeon"], ["James\x00Yeon"], ["James\u2028Yeon"]])
def test_globe_rejects_invalid_featured_names(bad):
    data = globe_project(ROSTER)
    data["scenes"][0]["globe"]["regions"][-1]["countries"][0]["featured_names"] = bad
    with pytest.raises(config.ConfigError, match="featured_names"):
        config.parse(data)


def test_roster_project_matches_supplied_regional_totals():
    scene = config.load(config.ROOT / "content" / "ambassadors.json").scenes[0]
    assert scene.duration == 16
    regions = scene.globe["regions"]
    assert [sum(c["count"] for c in r["countries"]) for r in regions] == [71, 22, 39, 4, 10, 46]
    assert sum(len(r["countries"]) for r in regions) == 45


def test_korea_closing_stop_shows_only_its_featured_names(monkeypatch):
    cfg = config.load(config.ROOT / "content" / "ambassadors.json")
    cfg.width, cfg.height = 320, 180
    scene = cfg.scenes[0]
    regions = scene.globe["regions"]
    assert [row for region in regions for row in region["countries"] if row.get("featured_names")] == [
        {"country": "South Korea", "count": 3, "featured_names": ["James Yeon", "Jaden Son", "Jeongmin Lee"]}
    ]
    assert view_at(scene, 13) == (6, 26, 115)
    stop, lat, lon = view_at(scene, 15)
    assert stop == 7
    assert (lat, lon) == pytest.approx((37.57, 126.98))

    labels = []
    draw_text = ImageDraw.ImageDraw.text

    def capture_text(draw, xy, text, *args, **kwargs):
        labels.append(text)
        return draw_text(draw, xy, text, *args, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", capture_text)
    renderer = Renderer(cfg)
    renderer.frame_at(13)
    assert "South Korea" in labels
    assert "James Yeon" not in labels
    labels.clear()
    renderer.frame_at(15)
    assert labels[1:6] == ["대한민국", "서울  /  SEOUL, SOUTH KOREA", "James Yeon", "Jaden Son", "Jeongmin Lee"]
    assert "3" not in labels

    korea = next(row for row in regions[-1]["countries"] if row["country"] == "South Korea")
    korea["featured_names"] = []
    assert view_at(scene, 15) == (6, 26, 115)


def test_orbit_region_pins_and_seoul_name_zoom(monkeypatch):
    scene = config.load(config.ROOT / "content" / "ambassadors.json").scenes[0]
    scene.globe["regions"][2]["countries"][0]["count"] += 1
    labels = []
    draw_text = ImageDraw.ImageDraw.text

    def capture(draw, xy, text, *args, anchor=None, font=None, fill=None, **kwargs):
        labels.append((text, anchor, font.size, fill))
        return draw_text(draw, xy, text, *args, anchor=anchor, font=font, fill=fill, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", capture)
    frame(scene, 0, 480, 270)
    pin_counts = {text for text, anchor, _, _ in labels if anchor == "mm" and text.isdecimal()}
    assert pin_counts == {"71", "22", "40", "4", "10", "46"}

    labels.clear()
    frame(scene, 7, 480, 270)
    pins = {text: fill for text, anchor, _, fill in labels if anchor == "mm" and text.isdecimal()}
    assert pins["40"] == "#76f7ce"
    assert len(pins) > 1
    assert all(fill == "#f0faf8" for text, fill in pins.items() if text != "40")

    names = {"James Yeon", "Jaden Son", "Jeongmin Lee"}
    sizes = []
    for t in (14.55, 15.7):
        labels.clear()
        frame(scene, t, 480, 270)
        sizes.append({text: size for text, _, size, _ in labels if text in names})
    assert sizes[0].keys() == sizes[1].keys() == names
    assert all(sizes[0][name] < sizes[1][name] for name in names)


def test_opening_pins_include_region_moved_to_auckland(monkeypatch):
    scene = config.load(config.ROOT / "content" / "ambassadors.json").scenes[0]
    scene.globe["regions"][-1].update(lat=-36.85, lon=174.76)
    config.validate_globe(scene)
    pin_counts = []
    draw_text = ImageDraw.ImageDraw.text

    def capture(draw, xy, text, *args, anchor=None, **kwargs):
        if anchor == "mm" and text.isdecimal():
            pin_counts.append(text)
        return draw_text(draw, xy, text, *args, anchor=anchor, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", capture)
    frame(scene, 0, 480, 270)
    assert sorted(pin_counts) == ["10", "22", "39", "4", "46", "71"]


def test_opening_fallback_keeps_badges_for_fiji_and_samoa(monkeypatch):
    scene = config.load(config.ROOT / "content" / "ambassadors.json").scenes[0]
    scene.globe["regions"] = [
        {"name": "Fiji", "lat": -17.7134, "lon": 178.065,
         "countries": [{"country": "Fiji", "count": 12}]},
        {"name": "Samoa", "lat": -13.759, "lon": -172.1046,
         "countries": [{"country": "Samoa", "count": 13}]},
    ]
    config.validate_globe(scene)
    pin_counts = []
    draw_text = ImageDraw.ImageDraw.text

    def capture(draw, xy, text, *args, anchor=None, **kwargs):
        if anchor == "mm" and text.isdecimal():
            pin_counts.append(text)
        return draw_text(draw, xy, text, *args, anchor=anchor, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", capture)
    frame(scene, 0, 480, 270)
    assert sorted(pin_counts) == ["12", "13"]


def test_globe_motion_and_frame_size():
    video = {"width": 320, "height": 180}
    renderer = Renderer(config.parse({**globe_project(ROSTER), "video": video}))
    scene = renderer.cfg.scenes[0]
    assert scene.duration == 6
    assert view_at(scene, 0) == (0, 18, -28)
    assert view_at(scene, 2) == (1, 18, -28)
    assert view_at(scene, 2.7) == (1, 36, -103)
    assert view_at(scene, 5.5) == (2, 26, 115)
    start, final = (renderer.frame_at(t) for t in (0, 5.5))
    assert start.size == final.size == (320, 180)
    assert start.tobytes() != final.tobytes()
