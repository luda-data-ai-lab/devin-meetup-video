import json
import sys

import pytest
from PIL import ImageDraw

from meetup_video import config
from meetup_video.globe import frame, view_at
from meetup_video.render import Renderer
from meetup_video.roster import globe_project, main as roster_main, read_roster


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
    [nyc] = scene.globe["regions"][0]["cities"]
    assert (nyc["name"], nyc["count"], nyc["lat"], nyc["lon"]) == ("New York City", 2, 40.7143, -74.006)


def test_roster_uses_one_country_row_for_case_variants():
    rows = ["Region\tCountry\tCity", "N.A.\tunited states\tNYC", "\tUnited States\tNew York",
            "\tExample Islands\t", "\tEXAMPLE ISLANDS\t"]
    [region] = globe_project(rows)["scenes"][0]["globe"]["regions"]
    assert region["countries"] == [{"country": "Example Islands", "count": 2},
                                   {"country": "United States", "count": 2}]
    [city] = region["cities"]
    assert (city["name"], city["country"], city["count"]) == ("New York City", "United States", 2)


@pytest.mark.parametrize("saved_country", ["United States", "USA"])
def test_roster_refresh_keeps_saved_city_names_and_coordinates(tmp_path, monkeypatch, capsys, saved_country):
    project = globe_project(ROSTER)
    regions = project["scenes"][0]["globe"]["regions"]
    city = regions[0]["cities"][0]
    city.update(name="NYC Metro", country=saved_country, roster_city=city["name"], lat=40.5, lon=-73.9)
    regions[1]["countries"][0]["featured_names"] = ["James Yeon"]
    project_path = tmp_path / "ambassadors.json"
    project_path.write_text(json.dumps(project), encoding="utf-8")
    tsv = tmp_path / "roster.tsv"
    tsv.write_text("Region\tCountry\tCity\nN.A.\tUSA\tNew York\n\tUSA\tMiami, Florida\n"
                   "\tUSA\tPortland + SF\nAsia-Pacific\tKorea\t\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["roster", str(tsv), "--existing-project", str(project_path)])
    roster_main()
    refreshed = config.parse(json.loads(capsys.readouterr().out)).scenes[0].globe["regions"]
    assert refreshed[0]["countries"] == [{"country": "United States", "count": 3}]
    assert [pin["name"] for pin in refreshed[0]["cities"]] == ["Miami", "NYC Metro"]
    assert refreshed[0]["cities"][1] == {**city, "count": 1}
    assert "cities" not in refreshed[1]
    assert refreshed[1]["countries"][0]["featured_names"] == ["James Yeon"]


def test_roster_refresh_matches_country_totals_pins_and_featured_names_with_one_key():
    names = ["James Yeon", "Jaden Son", "Jeongmin Lee"]
    saved_city = {"country": "korea", "name": "Seoul Metro", "roster_city": "Seoul",
                  "lat": 37.6, "lon": 127, "count": 9}
    previous = [{"name": "Asia-Pacific",
                 "countries": [{"country": "south korea", "count": 1, "featured_names": names}],
                 "cities": [saved_city]}]
    rows = ["Region\tCountry\tCity", "Asia-Pacific\tsouth korea\tSeoul", "\tKOREA\tSeoul",
            "Europe\tUnited Kingdom\tLondon"]
    scene = config.parse(globe_project(rows, previous)).scenes[0]
    europe, asia = scene.globe["regions"]
    assert europe["countries"] == [{"country": "United Kingdom", "count": 1}]
    assert asia["countries"] == [{"country": "South Korea", "count": 2, "featured_names": names}]
    assert asia["cities"] == [{**saved_city, "count": 2}]
    assert view_at(scene, scene.duration) == pytest.approx((3, 37.57, 126.98))


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
    assert scene.duration == 15.44
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
    assert view_at(scene, scene.duration) == (6, 26, 115)


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


def test_regional_tour_draws_editable_city_pins_only_on_map(monkeypatch):
    scene = config.load(config.ROOT / "content" / "ambassadors.json").scenes[0]
    europe = next(region for region in scene.globe["regions"] if region["name"] == "Europe")
    london = next(city for city in europe["cities"] if city["name"] == "London")
    london["name"], london["count"] = "Greater London", 5
    expected = "Greater London · 5"
    labels = []
    draw_text = ImageDraw.ImageDraw.text

    def capture(draw, xy, text, *args, **kwargs):
        labels.append((text, xy[0]))
        return draw_text(draw, xy, text, *args, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", capture)
    frame(scene, 0, 480, 270)
    assert not any(text == expected for text, _ in labels)
    labels.clear()
    frame(scene, 7, 480, 270)
    assert [x for text, x in labels if text == expected and x > 224]
    assert any(text == "United Kingdom" and x < 224 for text, x in labels)
    assert not any("주요 도시" in text or "CITY PIN" in text for text, _ in labels)
    labels.clear()
    frame(scene, 15.7, 480, 270)
    assert not any(text == expected for text, _ in labels)


@pytest.mark.parametrize("project", ["ambassadors", "ambassadors-nader"])
def test_orbit_holds_the_finished_map_for_three_seconds(project):
    cfg = config.load(config.ROOT / "content" / f"{project}.json")
    cfg.width, cfg.height = 480, 270
    scene = cfg.scenes[0]
    renderer = Renderer(cfg)
    assert scene.globe["end_hold"] == 3
    assert scene.timeline_duration == pytest.approx(18.44)
    assert renderer.locate(scene.timeline_duration) == (1, 0)
    start = renderer.frame_at(scene.duration).tobytes()
    assert renderer.frame_at(scene.duration - 0.2).tobytes() != start
    assert renderer.frame_at(scene.timeline_duration - 1 / cfg.fps).tobytes() == start


def test_zero_end_hold_restores_original_roster_tour_pacing():
    scene = config.parse(globe_project(ROSTER)).scenes[0]
    times = [0, 2, 2.7, 5.5, scene.duration]
    original = [view_at(scene, t) for t in times]
    scene.globe["end_hold"] = 3
    assert view_at(scene, 2) != original[1]
    scene.globe["end_hold"] = 0
    assert [view_at(scene, t) for t in times] == original


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


def test_opening_alternate_badges_preserve_standard_positions(monkeypatch):
    scene = config.load(config.ROOT / "content" / "ambassadors.json").scenes[0]
    scene.globe["regions"] = [
        {"name": name, "lat": lat, "lon": lon, "countries": [{"country": name, "count": count}]}
        for name, lat, lon, count in [
            ("Saipan", 15.185, 145.75, 101),
            ("Guam", 13.4443, 144.7937, 102),
            ("Manila", 14.5995, 120.9842, 103),
            ("Palau", 7.515, 134.5825, 104),
        ]
    ]
    config.validate_globe(scene)
    pin_counts = set()
    draw_text = ImageDraw.ImageDraw.text

    def capture(draw, xy, text, *args, anchor=None, **kwargs):
        if anchor == "mm" and text.isdecimal():
            pin_counts.add(text)
        return draw_text(draw, xy, text, *args, anchor=anchor, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", capture)
    frame(scene, 0, 480, 270)
    assert {"101", "103", "104"} <= pin_counts


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
