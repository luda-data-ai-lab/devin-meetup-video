# User manual (English)

## 1. Setup (once, Windows PowerShell)
```powershell
winget install Gyan.FFmpeg; winget install Python.Python.3.12
cd D:\01_luda\project\luda-data-ai-lab\devin-meetup-video; pip install -r requirements.txt; copy .env.example .env
```
Open a new PowerShell; if `ffmpeg -version` prints a version you are ready.

## 2. Make the video
| Goal | Command |
|---|---|
| Quick preview (960x540, 1-2 min) | `python -m meetup_video render --preview --out out\preview.mp4` |
| Final video (1920x1080, ~60s) | `python -m meetup_video render --out out\devin-meetup-seoul.mp4` |
| Save one frame | `python -m meetup_video still --at 12.5 --out out\still.png` |

Output goes to the `out\` folder.

## 3. Editor screen (recommended)
```powershell
cd D:\01_luda\project\luda-data-ai-lab\devin-meetup-video; python -m meetup_video edit --port 8765
```
Open http://127.0.0.1:8765/ in a browser.
- Edit each scene's captions, terminal lines, duration, zoom, pan and image, then press **Save**. Invalid values (e.g. duration 0) are not saved and show an error.
- Images: the file picker on a scene card saves to `assets\scenes\<scene id>.png`.
- Ending: title, date, headcount, quiz URL (QR) and labels.
- **Preview** (960x540) / **Final** (1920x1080) render shows progress and plays the result on the page.
- The "매뉴얼" / "Manual" links in the top menu open this manual.

## 3-1. Edit the file directly
You can also edit `content\scenes.json` by hand.
- `caption_ko` / `caption_en`: captions at the top of the screen
- `terminal`: lines typed in the bottom-left terminal (`$` lines are white commands, others green results)
- `duration`: scene length in seconds
- `image`: background image path; if the file is missing a labelled placeholder (mock) is used
- `zoom`: [start, end] zoom, `pan`: horizontal drift (-1 left, 0 none, 1 right)
- `ending`: ending title, date, headcount, quiz labels and `qr_url` (quiz link, shown as a QR in step 4)
- `video.accent`: accent color (#RRGGBB)

## 4. Logos
The ending uses the official white Cognition and Devin logos in `assets\brand\`. Replace a file with the same name to change it.

## 5. Image generation (optional)
`.env` defaults to `IMAGE_PROVIDER=mock`. Real generation comes in a later step; the key goes only in `.env` as `OPENAI_API_KEY`.
