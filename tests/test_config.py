import pytest

from meetup_video import config


def test_default_config_is_60_seconds_with_ending():
    cfg = config.load()
    assert cfg.total_duration == 60
    assert len(cfg.scenes) == 8
    assert cfg.scenes[-1].type == "ending"
    assert cfg.ending["date"] == "2026.12.01"


def test_rejects_duplicate_ids():
    with pytest.raises(config.ConfigError):
        config.parse({"scenes": [{"id": "a", "duration": 1}, {"id": "a", "duration": 1}]})


def test_rejects_bad_duration_and_color():
    with pytest.raises(config.ConfigError):
        config.parse({"scenes": [{"id": "a", "duration": 0}]})
    with pytest.raises(config.ConfigError):
        config.parse({"video": {"accent": "red"}, "scenes": [{"id": "a", "duration": 1}]})


def test_config_outside_content_dir_resolves_assets_from_repo_root(tmp_path):
    alt = tmp_path / "alt.json"
    alt.write_text(config.DEFAULT_CONFIG.read_text(encoding="utf-8"), encoding="utf-8")
    cfg = config.load(alt)
    assert cfg.path("assets/brand/logo_devin_white.png").exists()
