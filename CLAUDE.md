# study-helper: Learning X 백그라운드 학습 도구

숭실대학교 Canvas Learning X(canvas.ssu.ac.kr)의 강의 영상을 Docker 컨테이너 기반 CUI 환경에서
백그라운드로 재생(출석 처리)하거나 다운로드/변환/요약할 수 있는 도구.

## 실행 방법

```bash
docker compose run --rm study-helper          # 정상 실행 (TUI 직접 연결)
docker compose build && docker compose run --rm study-helper  # 이미지 재빌드 후 실행
```

- **`docker compose up` 사용 금지**: 로그 멀티플렉싱으로 TUI 깨짐. `run --rm`만 사용할 것
- `src/`는 볼륨 마운트되어 있어 코드 수정 후 재빌드 없이 재실행만 해도 반영됨
- `.env`, `.secret_key`는 볼륨 마운트로 호스트에 영속화됨
- 다운로드 파일은 `./data/`에 저장됨 (컨테이너 내 `/data/`)
- Whisper 모델, Playwright Chromium은 named volume에 캐시되어 재빌드 시 재다운로드 불필요

Docker Hub 릴리즈 이미지 사용 시: `docker-compose.yml` 상단 주석 참고.

## 개발 환경 설정

의존성 추가 시 `pyproject.toml` 수정 후 `docker compose up`으로 재빌드.

torch는 `pyproject.toml`에 포함하지 않음 — Dockerfile에서 CPU wheel로 직접 설치.

## 절대 건드리면 안 되는 것들

- **Playwright headless Chromium 유지**: 시스템 Chrome 경로 하드코딩 금지. Docker에서는 Playwright 내장 Chromium만 사용.
- **GUI 의존성 추가 금지**: flet, PyQt5 등 GUI 라이브러리 사용 금지. CUI 전용.
- **비디오 셀렉터**: `video.vc-vplay-video1`로 영상 URL 추출. 변경 시 Learning X 쪽 변경 확인 필요.

## 설계 의도

- **기본 엔진**: STT는 Whisper(로컬, base 모델), 요약은 Gemini API. 키는 `.env`에서 로드.
- **다운로드 경로**: 컨테이너 내 `/data/downloads/` — 볼륨 마운트로 호스트 접근.
- **출력 파일**: mp4(영상), mp3(음성, ffmpeg 변환), txt(STT 결과), `_summarized.txt`(요약).
- **백그라운드 재생**: video DOM 폴링(Plan A) + 진도 API 직접 호출(Plan B) 두 방식으로 구현. Plan A 실패 시 자동으로 Plan B로 전환.

## 프로젝트 구조

```
study-helper/
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── src/
│   ├── main.py
│   ├── config.py                     # 환경변수 로드 및 설정 저장
│   ├── crypto.py                     # 계정 정보 암호화/복호화
│   ├── auth/
│   │   └── login.py                  # Playwright 로그인 처리
│   ├── scraper/
│   │   ├── course_scraper.py         # 과목/주차/강의 목록 스크래핑
│   │   └── models.py                 # Course, LectureItem, Week 등 데이터 모델
│   ├── player/
│   │   └── background_player.py      # 백그라운드 재생 (출석용)
│   ├── downloader/
│   │   └── video_downloader.py       # 영상 URL 추출 + HTTP 스트리밍 다운로드
│   ├── converter/
│   │   └── audio_converter.py        # mp4 → mp3 (ffmpeg)
│   ├── stt/
│   │   └── transcriber.py            # Whisper STT
│   ├── summarizer/
│   │   └── summarizer.py             # Gemini/OpenAI API 요약
│   └── ui/
│       ├── login.py                  # 로그인 화면
│       ├── courses.py                # 과목/강의 선택 화면
│       ├── player.py                 # 재생 진행 화면
│       ├── download.py               # 다운로드 진행 화면
│       └── settings.py               # 초기 설정 화면
└── data/
    └── downloads/                    # 볼륨 마운트 대상
```

## Learning X 기술 메모

| 항목 | 값 |
|------|-----|
| 대시보드 URL | `https://canvas.ssu.ac.kr/` |
| 과목 목록 | `window.ENV.STUDENT_PLANNER_COURSES` (JS 평가) |
| 강의 목록 URL | `https://canvas.ssu.ac.kr/courses/{course_id}/external_tools/71` |
| 강의 목록 iframe | `iframe#tool_content` → `#root` (data-course_name, data-professors) |
| 주차/강의 파싱 | `.xnmb-module-list`, `.xnmb-module_item-outer-wrapper` 등 `.xnmb-*` 클래스 |
| 완료 여부 | `[class*='module_item-completed']` (completed / incomplete) |
| 출석 상태 | `[class*='attendance_status']` (attendance / late / absent / excused) |
| 비디오 | `video.vc-vplay-video1` |

## 환경 변수 (.env)

계정 정보와 설정은 최초 실행 시 TUI에서 입력하면 자동 저장됨. 직접 편집도 가능.

```
# 계정 (자동 저장, 암호화)
LMS_USER_ID=
LMS_PASSWORD=

# 다운로드 설정
DOWNLOAD_DIR=          # 비워두면 Docker: /data/downloads, macOS: ~/Downloads
DOWNLOAD_RULE=         # video / audio / both

# STT 설정
STT_ENABLED=           # true / false
WHISPER_MODEL=base     # tiny / base / small / medium / large

# AI 요약 설정
AI_ENABLED=            # true / false
AI_AGENT=              # gemini / openai
GEMINI_MODEL=          # gemini-2.5-flash 등
GOOGLE_API_KEY=
OPENAI_API_KEY=
```

## Git 커밋 규칙

형식: `type(scope): 한국어 설명` — 첫 줄 72자 이내

| type | 용도 |
|------|------|
| feat | 새 기능 |
| fix | 버그 수정 |
| refactor | 리팩토링 |
| docs | 문서 |
| test | 테스트 |
| chore | 빌드/도구 설정 |

## 보안 주의사항

아래 항목은 `.gitignore`에 등록되어 있음. 커밋 전 `git status`로 반드시 확인.

- `.env` — 실제 설정값 저장 파일. **절대 커밋 금지**. `.env.example`만 커밋 허용
- `.secret_key` — 계정/API 키 암호화에 사용하는 키. **절대 커밋 금지**
- `data/` — `data/downloads/`에 저장되는 다운로드 파일. **절대 커밋 금지**

**민감 정보 처리**: 학번, 비밀번호, API 키는 TUI 입력 즉시 `crypto.py`로 암호화되어 `.env`에 저장됨. 평문으로 저장되지 않음.
