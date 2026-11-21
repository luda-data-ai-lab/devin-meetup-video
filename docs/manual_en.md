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
| Render another saved setting | `python -m meetup_video render --config content\closing.json --out out\devin-meetup-seoul-closing.mp4` |
| Save one frame | `python -m meetup_video still --at 12.5 --out out\still.png` |

Output goes to the `out\` folder.

## 3. Editor screen (recommended)
```powershell
cd D:\01_luda\project\luda-data-ai-lab\devin-meetup-video; python -m meetup_video edit --port 8765
```
Open http://127.0.0.1:8765/ in a browser.
- Saved list (left): your saved settings by name; click one to open it. **Save** overwrites the open name; **+ Save as** saves under a new name (letters, digits, _ or -, up to 40). Example: the default (`scenes`) is the opening with QR off, `closing` has "Show QR" on. Settings go to `content\<name>.json` and the final render to `out\devin-meetup-seoul-<name>.mp4` (default: `out\devin-meetup-seoul.mp4`). Delete a file in `content\` to remove it from the list.
- Edit each scene's captions, terminal lines, duration, zoom, pan and image, then press **Save**. The terminal lines box is full width below zoom and pan; write one line per row. Invalid values (e.g. duration 0) are not saved and show an error.
- Images: the file picker on a scene card saves to `assets\scenes\<scene id>.png` (for a non-default save, `<name>_<scene id>.png`, so the original is not overwritten).
- Ending: title, date and the welcome line (quiz QR is off by default for the opening; tick "Show QR" and set the quiz URL to show a QR code).
- Music: upload an mp3/m4a/wav under "Music file"; it is saved to `assets\music\` and can be played on the page. Set volume (1 = original, default 0.8), fade in (s), fade out (s, ending with the video) and start position in the song (s). Leave the file empty to render without music. If the song is shorter than the video, the rest is silent.
- Music rights: the default track is A Game (Michael Ramir C.), Mixkit free music (commercial use, no attribution, https://mixkit.co/license/#musicFree). Well-known songs need the rights holder's permission for event playback.
- **Preview** (960x540) / **Final** (1920x1080) render shows progress and plays the result on the page.
- The "매뉴얼" / "Manual" links in the top menu open this manual.

## 3-1. Edit the file directly
You can also edit `content\scenes.json` by hand.
- `caption_ko` / `caption_en`: captions at the top of the screen
- `terminal`: lines typed in the bottom-left terminal (`$` lines are white commands, others green results)
- `duration`: scene length in seconds
- `image`: background image path; if the file is missing a labelled placeholder (mock) is used
- `zoom`: [start, end] zoom, `pan`: horizontal drift (-1 left, 0 none, 1 right)
- `ending`: ending title, date and `welcome` line
- `video.accent`: accent color (#RRGGBB)
- `music`: `file` (music path, empty = no music), `volume` (0-2), `fade_in`, `fade_out` (seconds), `start` (seconds into the song)

## 4. Logos
The ending uses the official white Cognition and Devin logos in `assets\brand\`. Replace a file with the same name to change it.

## 5. Image generation (optional)
`.env` defaults to `IMAGE_PROVIDER=mock`. Real generation comes in a later step; the key goes only in `.env` as `OPENAI_API_KEY`.

## 6. Real footage, characters, face blur
- A scene with `type: video` uses real footage (`video`) as background. If the file is missing it is downloaded from `video_url` into `assets\footage\` (not committed).
- `video_start`: seconds into the source clip.
- `blur_faces: true`: passerby faces are detected and blurred (needs opencv, `pip install -r requirements.txt`).
- `characters`: walking characters over the footage. `sprite` is `devin` (otter) or `bots` (Alpha, Oscar, Echo, Romeo, Delta); `x`=[start, end] horizontal position (0-1), `h`=[start, end] height as a fraction of the screen, `y`=feet position (0-1), `walk: false` disables the bob.
- 3D scene images live in `assets\scenes\<scene id>.jpg` and can be replaced from the editor.
