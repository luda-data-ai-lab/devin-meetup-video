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

## 3. 문구·시간·이미지 바꾸기
`content\scenes.json` 한 파일만 고치면 됩니다 (편집 화면은 3단계에서 추가).
- `caption_ko` / `caption_en`: 화면 위쪽 자막
- `terminal`: 왼쪽 아래 터미널에 타이핑되는 줄 (`$`로 시작하면 흰색 명령, 나머지는 초록색 결과)
- `duration`: 장면 길이(초)
- `image`: 장면 배경 이미지 경로. 파일이 없으면 장면 이름이 적힌 임시 이미지(mock)로 나옵니다.
- `zoom`: [시작, 끝] 확대 비율, `pan`: 좌우 이동 (-1 왼쪽, 0 없음, 1 오른쪽)
- `ending`: 엔딩 제목·날짜·인원·퀴즈 안내 문구와 `qr_url`(퀴즈 주소, 4단계에서 QR로 표시)
- `video.accent`: 강조색 (#RRGGBB)

## 4. 로고
엔딩에 `assets\brand\`의 Cognition·Devin 공식 로고(흰색)가 자동으로 들어갑니다. 파일을 같은 이름으로 바꾸면 새 로고가 쓰입니다.

## 5. 이미지 자동 생성 (선택)
`.env`의 `IMAGE_PROVIDER=mock`이 기본입니다. 실제 생성은 이후 단계에서 추가되며, 키는 `.env`의 `OPENAI_API_KEY`에만 넣습니다.
