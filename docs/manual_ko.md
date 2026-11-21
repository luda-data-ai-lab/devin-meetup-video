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
| 특정 순간 한 장 저장 | `python -m meetup_video still --at 12.5 --out out\still.png` |

결과는 `out\` 폴더에 저장됩니다.

## 3. 편집 화면 (추천)
```powershell
cd D:\01_luda\project\luda-data-ai-lab\devin-meetup-video; python -m meetup_video edit --port 8765
```
브라우저에서 http://127.0.0.1:8765/ 를 엽니다.
- 장면별 자막·터미널 줄·시간·확대·이동·이미지를 고치고 **저장**을 누릅니다. 터미널 줄 칸은 확대·이동 칸 아래에 한 줄 전체 폭으로 있고, 한 줄에 하나씩 씁니다. 잘못된 값(시간 0 등)은 저장되지 않고 오류가 표시됩니다.
- 이미지: 장면 카드의 파일 선택으로 올리면 `assets\scenes\<장면id>.png`로 저장됩니다.
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
