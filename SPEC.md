# SPEC — Devin Meetup Seoul 오프닝 영상

## 목적
2026-12-01 Devin Meetup Seoul(최대 120명) 오프닝에서 Cognition과 Devin을 재미있게 소개하는 약 60초 영상.
Devin(공식 마스코트: 갓 쓴 주황 수달)과 팀 봇들이 서울 거리를 걸어다니며 일하는 모습.

## 결과물
- `out/devin-meetup-seoul.mp4` — 1920x1080, 30fps, H.264, 약 60초
- 장면별 정지 이미지(썸네일·포스터용)

## 구성
- 장면 8개 (스토리보드 v2): 남산타워 → 광화문 → 명동 → 지하철 2호선 → 편의점/포장마차 → 한강 → 행사장 입구 → 엔딩 타이틀(퀴즈 QR)
- 장면 = AI 배경 이미지 + 코드 애니메이션(터미널 타이핑, 자막, 카메라 줌/팬, 전환)
- 자막: 한국어 메인 + 영어 보조

## 편집 화면 (관리자)
- 브라우저 화면에서 장면별 문구·터미널 줄·시간·이미지·엔딩 QR URL을 수정하고 "렌더" 버튼으로 다시 만든다.
- 설정은 `content/scenes.json` 한 파일에 저장 (코드 수정 없이 변경 가능).

## 이미지
- 기본: 저장소에 커밋된 AI 생성 이미지 사용 (`assets/scenes/*.png`). 화풍(A 3D / B 웹툰 / C 실제 거리 합성)은 James 선택 후 결정.
- 이미지 파일이 없으면 provider가 대신 만든다 (기본 mock = 장면 이름이 적힌 그라데이션).
- 선택: 이미지 재생성 기능 — 실제 키는 `.env`(James 입력), `.env.example`에는 placeholder만. 개발·테스트는 mock provider.

## 범위 밖
- 내레이션 녹음

## 브랜드 자산
- `assets/brand/`: Cognition 로고(흰색), Devin 로고(흰색), Cognition 심볼, Devin 수달 마스코트 — James 제공 공식 파일
- 엔딩 타이틀에 Cognition × Devin 로고, 장면 이미지 생성 시 마스코트를 참조 이미지로 사용

## 실행 환경
- Python 3.10+, Pillow, ffmpeg (PATH에 있어야 함)
- 글꼴: Ubuntu Noto Sans CJK / Windows 맑은 고딕·Consolas 자동 선택

## 확정 사항 (2026-11-21)
- 화풍: C(실제 서울 거리 영상) + 3D 장면 혼합, 약 90초, 15장면 (콘티 v3, 첫 장면 샌프란시스코 → 인천 도착)
- Bot: 실제 아바타 모양·색 (HQ·Alpha 자홍, HQ·Oscar 노랑, FDE·Echo 분홍보라, RE·Romeo 주황, FDE·Delta 주홍 단안형), 개발 풀 Bot은 행사장 장면에 등장
- 실사: 우선 Mixkit 720p, 완료 후 Pexels 고화질로 교체
