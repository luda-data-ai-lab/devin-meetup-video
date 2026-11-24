# User manual (English)

## 1. Setup (once, Windows PowerShell)
```powershell
winget install Gyan.FFmpeg; winget install Python.Python.3.12
cd D:\01_luda\project\luda-data-ai-lab\devin-meetup-video; pip install -r requirements.txt; copy .env.example .env
```
Open a new PowerShell and check that both `ffmpeg -version` and `ffprobe -version` print a version.

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

## 7. Ambassador globe and greeting reel
1. Create `assets/footage/` in the extracted or cloned project folder and put the three supplied source videos there. Rename copies as shown below, or set **Source clip** to each local path in the editor. Neither a GitHub source ZIP nor a clone includes these videos. The basic **ambassadors** project does not require the Nader clip.

   | Original file | Default local filename |
   |---|---|
   | `Congrats-Seoul-Devin-Meetup-nikkie.mp4` | `ambassador-nikkie.mp4` |
   | `South-Korea-Greeting-ES-subbed.mp4` | `ambassador-colombia.mp4` |
   | `WhatsApp Video 2026-11-16 at 4.24.34 AM.mp4` | `ambassador-abu-dhabi.mp4` |

2. Open the **ambassadors** saved project. Expand a region in **Orbit** to edit country counts. The region and worldwide totals update immediately; **Save** persists them. The intro opens on the worldwide total and shows pins with active ambassador counts for all six regions across two globe views. During the tour, the current region's pin is highlighted, and the intro ends by zooming in on Seoul and enlarging South Korea's featured names. In **Asia-Pacific**, enter one name per line under **South Korea ambassador names** (the country's `featured_names` in the project JSON). Clearing the list removes the Seoul stop without changing the counts. **Duration** sets the tour timing (15.44 seconds by default). **End hold** (`globe.end_hold` in JSON) keeps the final map still before the first greeting clip: 3 seconds by default, or 0 for the original tour pacing with no added hold. The default intro is about 18.44 seconds including the hold.
   Expand **City pins** within a region to add, remove, or edit a city's name, country, count, latitude, and longitude. During that region's stop, up to seven visible cities with positive counts appear as gold pins, with name and count callouts where space allows. Cities appear only on the map; editing them does not change country, regional, or worldwide totals. The worldwide opening and Seoul close do not show these city pins.
3. Use **Move up** / **Move down** on a clip to change the greeting order without moving the intro. Expand **Korean subtitle cues** on Abu Dhabi to revise text, add or remove cues, or edit their start/end times in seconds relative to the start of that clip. Cues must be in order, not overlap, and fit within its duration. Nikkie and Colombia keep the Korean subtitles that are already in their video images; those subtitles cannot be edited separately.
   Set **Subtitle font size** in the same section (pixels at 1080p; Abu Dhabi is set to 36).
4. Choose **Preview** or **Final** in the editor. If any required clips are missing, the editor lists all expected paths before starting the render. Add the files or update the source clip paths, then try again. To render from the command line:

   ```powershell
   python -m meetup_video render --config content/ambassadors.json --out out/ambassador-reel.mp4
   ```

   The final reel is 1920×1080 at 30 fps with 48 kHz stereo AAC. Portrait clips keep their framing with side bars; spoken audio is loudness-normalized and new Korean cues are burned into the picture.

For the separate version with Nader Dabit's welcome, save the supplied MP4 as `assets/footage/nader-dabit-welcome.mp4` and open **ambassadors-nader**. Nader's clip is last by default, and its order and Korean cues are editable. **Final** renders a separate file without replacing the original **ambassadors** reel. From the command line, use `python -m meetup_video render --config content/ambassadors-nader.json --out out/ambassador-reel-nader.mp4`.

To render just Nader's welcome, open **nader-welcome** with the same source MP4. It starts directly on Nader and burns in the same editable Korean cues, without changing either ambassador project. From the command line, use `python -m meetup_video render --config content/nader-welcome.json --out out/nader-welcome.mp4`.

For direct editing, `content/ambassadors.json` uses the order of the `scenes` array. A `clip` scene has a local `video` path, optional `video_start` in source seconds, and `duration`. Its `subtitles` are `{"start": 1.36, "end": 2.5, "text": "안녕하세요"}` objects; set `subtitles_baked_in: true` and omit cues for footage that already has Korean text.

To refresh from a new `Region / Country / City` TSV, run `python -m meetup_video.roster path/to/roster.tsv --existing-project content/ambassadors.json` (use the project you're updating), then replace only `globe.regions` in its intro scene. Counts come from the new TSV. For matching cities, the converter keeps the saved display name and coordinates; otherwise it uses the bundled lookup. Unknown locations still count toward their country but get no pin. If you rename a city directly in JSON, keep its original roster name in `roster_city` so that it can still be matched.
