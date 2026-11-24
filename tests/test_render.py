import shutil
import subprocess
from array import array

import pytest
from PIL import Image, ImageChops, ImageDraw

from meetup_video import config
from meetup_video.render import Renderer, subtitle_card


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


@pytest.mark.parametrize(("clip_id", "first_frame", "frame_count"), [
    ("nikkie", 554, 600),
    ("nader-dabit", 2565, 1806),
])
def test_clip_frame_indices_are_consecutive_on_the_output_timeline(clip_id, first_frame, frame_count):
    cfg = config.load(config.ROOT / "content" / "ambassadors-nader.json")
    cfg.width, cfg.height = 16, 9
    renderer = Renderer(cfg)
    indices = []
    image = Image.new("RGB", (cfg.width, cfg.height))

    class FrameSource:
        def get(self, index):
            indices.append(index)
            return image

    renderer._videos[clip_id] = FrameSource()
    for scene in cfg.scenes:
        if scene.id == clip_id:
            scene.subtitles = []
    for frame in range(first_frame, first_frame + frame_count):
        renderer.frame_at(frame / cfg.fps)
    assert indices == list(range(frame_count))


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="ffmpeg/ffprobe not installed")
def test_joined_clip_keeps_portrait_audio_and_burns_subtitles(tmp_path):
    clip = tmp_path / "portrait.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "color=red:s=64x96:r=10:d=1",
                    "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100:duration=1",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", str(clip)], check=True)
    data = {"video": {"width": 320, "height": 180, "fps": 10},
            "scenes": [{"id": "intro", "duration": 1},
                       {"id": "clip", "type": "clip", "duration": 1, "video": str(clip),
                        "subtitles": [{"start": 0.2, "end": 0.6, "text": "안녕하세요\n서울에 오신 걸 환영합니다!"}]}]}
    renderer = Renderer(config.parse(data), cache_dir=tmp_path / "cache")
    out = renderer.render(tmp_path / "reel.mp4")
    probe = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries",
                                     "stream=codec_name,width,height,r_frame_rate,channels,sample_rate",
                                     "-of", "compact=p=0", str(out)], text=True).splitlines()
    assert probe == ["codec_name=h264|width=320|height=180|r_frame_rate=10/1",
                     "codec_name=aac|sample_rate=48000|channels=2|r_frame_rate=0/0"]
    pcm = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(out), "-vn", "-f", "s16le", "-ac", "1", "-"])
    samples = array("h", pcm)
    assert max(map(abs, samples[1000:47000])) == 0
    assert max(map(abs, samples[50000:90000])) > 100
    before, captioned, after = [renderer.frame_at(t) for t in (1.1, 1.3, 1.7)]
    assert before.getpixel((0, 90)) == (0, 0, 0)
    assert before.getpixel((160, 90))[0] > 240
    assert before.tobytes() == after.tobytes() != captioned.tobytes()
    data["scenes"][1]["subtitle_font_size"] = 36
    renderer.cfg.scenes[1].subtitle_font_size = config.parse(data).scenes[1].subtitle_font_size
    smaller = renderer.frame_at(1.3)
    normal_box = ImageChops.difference(before, captioned).getbbox()
    smaller_box = ImageChops.difference(before, smaller).getbbox()
    assert smaller_box is not None
    assert smaller_box[2] - smaller_box[0] < normal_box[2] - normal_box[0]
    assert smaller_box[3] - smaller_box[1] < normal_box[3] - normal_box[1]
    renderer._videos["clip"].close()


def test_subtitle_font_size_does_not_shrink_when_setting_increases(monkeypatch):
    actual_sizes = []
    draw_text = ImageDraw.ImageDraw.multiline_text

    def capture_size(draw, xy, text, *args, font, **kwargs):
        actual_sizes.append(font.size)
        return draw_text(draw, xy, text, *args, font=font, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "multiline_text", capture_size)
    cue = " ".join(["서울에 오신 걸 환영합니다!"] * 5)
    for size in (120, 144):
        subtitle_card(cue, 1920, 1080, size)
    smaller, larger = actual_sizes
    assert 120 == smaller <= larger <= 144


def test_clip_rejects_double_subtitles_and_invalid_timing():
    clip = {"id": "c", "type": "clip", "duration": 1, "video": "local.mp4",
            "subtitles": [{"start": 0, "end": 0.5, "text": "안녕하세요"}]}
    with pytest.raises(config.ConfigError, match="burned-in"):
        config.parse({"scenes": [{**clip, "subtitles_baked_in": True}]})
    with pytest.raises(config.ConfigError, match="subtitle times"):
        config.parse({"scenes": [{**clip, "subtitles": [{"start": 0, "end": 1.1, "text": "안녕하세요"}]}]})
    with pytest.raises(config.ConfigError, match="subtitle font size"):
        config.parse({"scenes": [{**clip, "subtitle_font_size": 0}]})


def test_ending_qr_toggle(tmp_path):
    base = {"video": {"width": 320, "height": 180, "fps": 5}, "scenes": [{"id": "e", "type": "ending", "duration": 1}]}
    off = Renderer(config.parse({**base, "ending": {"title": "T", "qr_url": "https://q.example"}}), cache_dir=tmp_path)
    on = Renderer(config.parse({**base, "ending": {"title": "T", "qr_url": "https://q.example", "show_qr": True}}), cache_dir=tmp_path)
    assert off.frame_at(0.9).tobytes() != on.frame_at(0.9).tobytes()


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")
def test_render_with_music_adds_faded_audio_track(tmp_path):
    song = tmp_path / "song.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                    str(song)], check=True)
    cfg = config.parse({
        "video": {"width": 160, "height": 90, "fps": 5},
        "music": {"file": str(song), "volume": 0.5, "fade_out": 1},
        "scenes": [{"id": "a", "duration": 2}],
    }, base_dir=config.ROOT)
    out = Renderer(cfg, cache_dir=tmp_path / "cache").render(tmp_path / "m.mp4")
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,duration", "-of", "csv=p=0",
                            str(out)], capture_output=True, text=True, check=True).stdout.split()
    kinds = {line.split(",")[0]: float(line.split(",")[1]) for line in probe}
    assert set(kinds) == {"video", "audio"} and abs(kinds["audio"] - 2) < 0.1


def test_missing_music_file_fails_before_encoding(tmp_path):
    cfg = config.parse({"music": {"file": "assets/music/nope.mp3"}, "scenes": [{"id": "a", "duration": 1}]},
                       base_dir=tmp_path)
    with pytest.raises(RuntimeError, match="music file not found"):
        Renderer(cfg, cache_dir=tmp_path).music_args()
