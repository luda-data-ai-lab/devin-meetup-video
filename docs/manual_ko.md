# 사용자 매뉴얼 (한국어)

## 1. 준비 (최초 1회, Windows PowerShell)
```powershell
winget install Gyan.FFmpeg; winget install Python.Python.3.12
cd D:\01_luda\project\luda-data-ai-lab\devin-meetup-video; pip install -r requirements.txt; copy .env.example .env
```
PowerShell을 새로 열어 `ffmpeg -version`이 나오면 준비 완료입니다.

## 2. 영상 만들기
| 하고 싶은 것 | 명령 |
|---|---|
| 빠른 미리보기 (960x540, 1~2분) | `python -m meetup_video render --preview --out out\preview.mp4` |
| 최종 영상 (1920x1080, 약 60초) | `python -m meetup_video render --out out\devin-meetup-seoul.mp4` |
| 다른 이름의 설정으로 렌더 | `python -m meetup_video render --config content\closing.json --out out\devin-meetup-seoul-closing.mp4` |
| 특정 순간 한 장 저장 | `python -m meetup_video still --at 12.5 --out out\still.png` |

결과는 `out\` 폴더에 저장됩니다.

## 3. 편집 화면 (추천)
```powershell
cd D:\01_luda\project\luda-data-ai-lab\devin-meetup-video; python -m meetup_video edit --port 8765
```
브라우저에서 http://127.0.0.1:8765/ 를 엽니다.
- 저장 목록(왼쪽): 저장해 둔 설정 이름이 보이고, 누르면 그 설정을 엽니다. **저장**은 지금 연 이름에 덮어쓰고, **+ 새 이름으로 저장**은 이름(글자·숫자·_·-, 40자 이내)을 정해 새로 저장합니다. 예: 기본(`scenes`)은 오프닝용 QR 끔, `closing`은 "QR 표시"를 켠 마무리용. 설정은 `content\<이름>.json`, 최종 렌더 영상은 `out\devin-meetup-seoul-<이름>.mp4`(기본은 `out\devin-meetup-seoul.mp4`)로 따로 저장됩니다. 필요 없는 설정은 `content\` 폴더에서 그 파일을 지우면 목록에서 사라집니다.
- 장면별 자막·터미널 줄·시간·확대·이동·이미지를 고치고 **저장**을 누릅니다. 터미널 줄 칸은 확대·이동 칸 아래에 한 줄 전체 폭으로 있고, 한 줄에 하나씩 씁니다. 잘못된 값(시간 0 등)은 저장되지 않고 오류가 표시됩니다.
- 이미지: 장면 카드의 파일 선택으로 올리면 `assets\scenes\<장면id>.png`로 저장됩니다(기본이 아닌 이름으로 연 설정은 `<이름>_<장면id>.png`라 원본 이미지를 덮어쓰지 않음).
- 엔딩: 제목·날짜·환영 문구를 고칩니다 (오프닝 영상이라 퀴즈 QR은 기본으로 끔. 마무리 때 쓰려면 "QR 표시"를 켜고 퀴즈 주소를 넣으면 QR 코드가 나옵니다).
- 배경음악: "음악 파일"에서 mp3/m4a/wav를 올리면 `assets\music\`에 저장되고 화면에서 바로 들어볼 수 있습니다. 음량(1=원음, 기본 0.8), 시작 페이드(초), 끝 페이드(초, 영상 끝에 맞춰 줄어듦), 곡 시작 위치(초)를 고칩니다. 파일 칸을 비우면 음악 없이 렌더합니다. 곡이 영상보다 짧으면 남은 부분은 무음입니다.
- 음악 저작권: 기본 곡은 A Game(Michael Ramir C.), Mixkit 무료 음악(상업 사용 가능, 출처 표기 불필요, https://mixkit.co/license/#musicFree)입니다. 유명 가요·팝송은 저작권자 허락(행사 공연 사용) 없이 쓰면 안 됩니다.
- **미리보기 렌더**(960x540) / **최종 렌더**(1920x1080)를 누르면 진행률이 표시되고, 끝나면 화면에서 바로 재생됩니다.
- 상단 메뉴의 "매뉴얼" / "Manual"로 이 문서를 엽니다.

## 3-1. 파일로 직접 고치기
`content\scenes.json`을 직접 고쳐도 됩니다.
- `caption_ko` / `caption_en`: 화면 위쪽 자막
- `terminal`: 왼쪽 아래 터미널에 타이핑되는 줄 (`$`로 시작하면 흰색 명령, 나머지는 초록색 결과)
- `duration`: 장면 길이(초)
- `image`: 장면 배경 이미지 경로. 파일이 없으면 장면 이름이 적힌 임시 이미지(mock)로 나옵니다.
- `zoom`: [시작, 끝] 확대 비율, `pan`: 좌우 이동 (-1 왼쪽, 0 없음, 1 오른쪽)
- `ending`: 엔딩 제목·날짜·`welcome`(환영 문구)
- `video.accent`: 강조색 (#RRGGBB)
- `music`: `file`(음악 파일 경로, 빈 값이면 음악 없음), `volume`(0~2), `fade_in`, `fade_out`(초), `start`(곡에서 몇 초부터)

## 4. 로고
엔딩에 `assets\brand\`의 Cognition·Devin 공식 로고(흰색)가 자동으로 들어갑니다. 파일을 같은 이름으로 바꾸면 새 로고가 쓰입니다.

## 5. 이미지 자동 생성 (선택)
`.env`의 `IMAGE_PROVIDER=mock`이 기본입니다. 실제 생성은 이후 단계에서 추가되며, 키는 `.env`의 `OPENAI_API_KEY`에만 넣습니다.

## 6. 실사 장면 · 캐릭터 · 얼굴 흐림
- 장면 `type`이 `video`이면 실제 영상(`video`)을 배경으로 씁니다. 파일이 없으면 `video_url`에서 `assets\footage\`로 자동으로 받습니다(이 폴더는 저장소에 올리지 않음).
- `video_start`: 원본 영상에서 몇 초부터 쓸지.
- `blur_faces: true`: 행인 얼굴을 자동으로 찾아 흐리게 합니다(opencv 필요, `pip install -r requirements.txt`).
- `characters`: 영상 위에 걷는 캐릭터를 올립니다. `sprite`는 `devin`(수달) 또는 `bots`(Alpha·Oscar·Echo·Romeo·Delta), `x`=[시작, 끝] 가로 위치(0~1), `h`=[시작, 끝] 키(화면 높이 비율), `y`=발 위치(0~1), `walk`=false면 흔들림 없음.
- 3D 장면 이미지는 `assets\scenes\<장면id>.jpg`이며, 편집 화면에서 바꿔 올릴 수 있습니다.

## 7. 앰버서더 지구본 인트로와 인사 영상
1. 받은 원본 영상 세 개를 `assets/footage/`에 넣습니다. 복사본의 파일명을 아래처럼 바꾸거나 편집 화면의 **원본 영상 경로**에 각 파일의 로컬 경로를 입력하세요. 원본 영상은 Git에 올라가지 않습니다.

   | 원본 파일 | 기본 로컬 파일명 |
   |---|---|
   | `Congrats-Seoul-Devin-Meetup-nikkie.mp4` | `ambassador-nikkie.mp4` |
   | `South-Korea-Greeting-ES-subbed.mp4` | `ambassador-colombia.mp4` |
   | 2026-11-16 오전 4:24:34 WhatsApp 영상 | `ambassador-abu-dhabi.mp4` |

2. 저장 목록에서 **ambassadors**를 엽니다. **Orbit** 인트로에서 지역을 펼쳐 국가별 인원을 고칩니다. 지역별·전 세계 합계는 즉시 갱신되며, **저장**을 누르면 변경 사항이 반영됩니다. 인트로는 전 세계 합계로 시작해 지역을 차례로 돌고, 서울에서 한국 앰버서더의 이름을 보여 주며 끝납니다. **Asia-Pacific**의 **한국 앰버서더 이름**에 한 줄에 한 명씩 입력합니다(프로젝트 JSON의 `featured_names`). 목록을 비우면 인원수는 그대로 유지되고 서울 장면만 빠집니다. **시간(초)**에서 재생 속도를 조절할 수 있습니다(기본 16초).
3. 영상 카드의 **위로** / **아래로**를 눌러 인사 영상 순서를 바꿉니다. 인트로는 맨 앞에 남습니다. 아부다비 영상 카드에서 **한글 자막**을 펼치면 문구를 수정하거나 자막을 추가·삭제하고, 영상 시작 지점 기준으로 시작·끝 시간(초)을 고칠 수 있습니다. 자막 시간은 순서대로 입력하고 서로 겹치거나 영상 길이를 넘지 않도록 합니다. nikkie와 콜롬비아 영상은 원본 화면에 이미 들어 있는 한국어 자막을 그대로 사용하므로 별도로 수정할 수 없습니다.
   같은 메뉴의 **자막 글자 크기**에서 크기를 조절할 수 있습니다(1080p 기준 픽셀, 아부다비 기본값 36).
4. 편집 화면에서 **미리보기 렌더** 또는 **최종 렌더**를 누르거나, 아래 명령을 실행합니다.

   ```powershell
   python -m meetup_video render --config content/ambassadors.json --out out/ambassador-reel.mp4
   ```

   최종 출력은 1920×1080, 초당 30프레임, 48 kHz 스테레오 AAC입니다. 세로 영상은 좌우 여백을 넣어 잘리지 않으며, 인사 영상의 음량은 일정한 기준으로 맞추고 새 한국어 자막은 화면에 직접 넣습니다.

`content/ambassadors.json`을 직접 고칠 때는 `scenes` 배열의 순서가 재생 순서입니다. `clip` 장면에는 로컬 영상 경로 `video`, 필요시 원본 시작 시간 `video_start`(초), 재생 길이 `duration`을 설정합니다. `subtitles`에는 `{"start": 1.36, "end": 2.5, "text": "안녕하세요"}` 형식으로 자막을 넣습니다. 원본에 한국어 자막이 들어 있으면 `subtitles_baked_in: true`로 설정하고 별도 자막은 넣지 않습니다. 새 `Region / Country / City` TSV가 있으면 `python -m meetup_video.roster path/to/roster.tsv`를 실행한 뒤, 결과의 `globe.regions` 부분만 인트로 장면에 붙여 넣으면 기존 영상 설정을 그대로 유지할 수 있습니다.
