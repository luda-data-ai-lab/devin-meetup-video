import shutil
import subprocess

import pytest

from meetup_video import config
from meetup_video.render import Renderer


def small_cfg(tmp_path):
    cfg = config.parse({
        "video": {"width": 320, "height": 180, "fps": 5, "transition_sec": 0.4},
        "ending": {"title": "Devin Meetup Seoul", "date": "2026.12.01"},
        "scenes": [
            {"id": "a", "duration": 1, "caption_ko": "서울", "caption_en": "Seoul", "terminal": ["$ devin run", "> ok ✓"]},
            {"id": "b", "duration": 1, "pan": 1},
            {"id": "end", "type": "ending", "duration": 1},
        ],
    }, base_dir=config.ROOT)
    return Renderer(cfg, cache_dir=tmp_path / "cache")


def test_frames_have_configured_size_and_mock_images(tmp_path):
    rd = small_cfg(tmp_path)
    for t in (0, 0.5, 1.1, 2.5):
        assert rd.frame_at(t).size == (320, 180)
    assert (tmp_path / "cache" / "a.png").exists()


def test_transition_blends_previous_scene(tmp_path):
    rd = small_cfg(tmp_path)
    mid = rd.frame_at(1.2).tobytes()
    assert mid != rd.frame_at(1.6).tobytes()


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")
def test_render_mp4(tmp_path):
    out = small_cfg(tmp_path).render(tmp_path / "v.mp4")
    probe = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height,nb_read_frames", "-of", "csv=p=0", str(out)],
                           capture_output=True, text=True, check=True).stdout.strip()
    assert probe == "320,180,15"
