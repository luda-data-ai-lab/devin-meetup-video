import pytest

from meetup_video import config
from meetup_video.globe import view_at
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


def test_roster_project_matches_supplied_regional_totals():
    scene = config.load(config.ROOT / "content" / "ambassadors.json").scenes[0]
    regions = scene.globe["regions"]
    assert [sum(c["count"] for c in r["countries"]) for r in regions] == [71, 22, 39, 4, 10, 46]
    assert sum(len(r["countries"]) for r in regions) == 45


def test_globe_motion_and_frame_size():
    video = {"width": 320, "height": 180}
    renderer = Renderer(config.parse({**globe_project(ROSTER), "video": video}))
    scene = renderer.cfg.scenes[0]
    assert view_at(scene, 4) == (1, 36, -103)
    assert view_at(scene, 5.5) == (1, 26, 115)
    start, final = (renderer.frame_at(t) for t in (0, 11))
    assert start.size == final.size == (320, 180)
    assert start.tobytes() != final.tobytes()
