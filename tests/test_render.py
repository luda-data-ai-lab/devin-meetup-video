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


def test_missing_korean_font_fails_loudly(monkeypatch):
    from meetup_video import fonts
    monkeypatch.setattr(fonts, "KR_BOLD", ["/nonexistent.ttf"])
    fonts.kr.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="Korean font"):
            fonts.kr(20)
    finally:
        fonts.kr.cache_clear()


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")
def test_video_scene_with_characters_and_face_blur(tmp_path):
    clip = tmp_path / "clip.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=320x180:rate=5:duration=2",
                    "-pix_fmt", "yuv420p", str(clip)], check=True)
    cfg = config.parse({"video": {"width": 320, "height": 180, "fps": 5}, "scenes": [
        {"id": "v", "type": "video", "duration": 2, "video": str(clip), "blur_faces": True,
         "characters": [{"sprite": "devin", "x": [0.2, 0.8], "h": [0.5, 0.5]}]}]})
    rd = Renderer(cfg, cache_dir=tmp_path)
    a, b = rd.frame_at(0.0), rd.frame_at(1.8)
    assert a.size == (320, 180) and a.tobytes() != b.tobytes()
    assert rd.frame_at(0.2).size == (320, 180)
    rd._videos["v"].close()


def test_video_scene_requires_path_and_known_sprite():
    with pytest.raises(config.ConfigError, match="video path"):
        config.parse({"scenes": [{"id": "v", "type": "video", "duration": 1}]})
    with pytest.raises(config.ConfigError, match="sprite"):
        config.parse({"scenes": [{"id": "v", "duration": 1, "characters": [{"sprite": "cat"}]}]})


def test_ending_qr_toggle(tmp_path):
    base = {"video": {"width": 320, "height": 180, "fps": 5}, "scenes": [{"id": "e", "type": "ending", "duration": 1}]}
    off = Renderer(config.parse({**base, "ending": {"title": "T", "qr_url": "https://q.example"}}), cache_dir=tmp_path)
    on = Renderer(config.parse({**base, "ending": {"title": "T", "qr_url": "https://q.example", "show_qr": True}}), cache_dir=tmp_path)
    assert off.frame_at(0.9).tobytes() != on.frame_at(0.9).tobytes()
