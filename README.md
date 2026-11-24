# devin-meetup-video

## Render the ambassador reel (Windows PowerShell)

The source ZIP and Git clone **do not include the greeting videos**. Create `assets/footage/` in the extracted or cloned project folder and copy the three original videos there with these names:

| Original video | Required path |
|---|---|
| `Congrats-Seoul-Devin-Meetup-nikkie.mp4` | `assets/footage/ambassador-nikkie.mp4` |
| `South-Korea-Greeting-ES-subbed.mp4` | `assets/footage/ambassador-colombia.mp4` |
| `WhatsApp Video 2026-11-16 at 4.24.34 AM.mp4` | `assets/footage/ambassador-abu-dhabi.mp4` |

`assets/footage/nader-dabit-welcome.mp4` is only needed for **ambassadors-nader** or **nader-welcome**, not the basic reel.

With Python 3.12 and FFmpeg (`ffmpeg` and `ffprobe`) on PATH, run:

```powershell
Set-Location 'D:\01_luda\project\luda-data-ai-lab\devin-meetup-video'
python -m pip install -r requirements.txt
python -m meetup_video render --config 'content/ambassadors.json' --out 'out/ambassador-reel.mp4'
```

If you extracted a ZIP elsewhere, use the folder containing `requirements.txt` in place of the path above. To use the editor, run `python -m meetup_video edit --port 8765`, open <http://127.0.0.1:8765/>, select **ambassadors**, and click **Final**. If a video is missing, the editor lists the expected paths before starting the render.

## Event opener

Devin Meetup Seoul (2026-12-01) opening video: Devin and the bot team walk through Seoul, 1920x1080.

- Spec: [SPEC.md](SPEC.md) · Plan: [DEVIN.md](DEVIN.md)
- Manual: [한국어](docs/manual_ko.md) · [English](docs/manual_en.md)

```powershell
cd D:\01_luda\project\luda-data-ai-lab\devin-meetup-video; pip install -r requirements.txt; python -m meetup_video render --preview --out out\preview.mp4
```
