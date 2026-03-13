# Changelog

## [v1.1.2] - 2026-03-13

### 추가
- **CI/CD 파이프라인**: GitHub Actions에서 Lint, 단위 테스트, Docker 빌드 자동 검증
- **단위 테스트 26개**: `crypto`, `models`, `config`, `summarizer`, `converter`, `transcriber` 모듈 커버리지 확보
- **STT 언어 선택**: 한국어(ko) / 영어(en) / 자동 감지(auto) 옵션 추가
- **AI 요약 커스텀 프롬프트**: 사용자 정의 프롬프트 지원
- **세션 만료 자동 재로그인**: LMS 세션 만료 감지 시 자동으로 재인증
- **다운로드 이어받기**: Range 헤더를 활용한 중단된 다운로드 재개 지원
- **자동 모드 진행 상태 영속화**: JSON 파일로 자동 모드 진행 상태 저장/복원
- **수동 모드 재생 오류 텔레그램 알림**: 수동 재생 중 오류 발생 시 텔레그램 알림 발송

### 수정
- **Ruff lint/format 전체 적용**: 코드 스타일 통일
- **Whisper 모델 싱글톤 캐싱**: 반복 로드로 인한 메모리 누수 방지
- **로그인 실패 시 자격증명 유지**: 실패 시 저장된 자격증명을 삭제하지 않도록 변경
- **play_lecture() 리소스 정리 보장**: `try-finally` 블록으로 예외 발생 시에도 리소스 정리
- **진도 API 실패 재시도**: 즉시 재시도 및 완료 보고 최대 3회 재시도
- **스크래핑 선택자 실패 시 경고 로그 추가**
- **텔레그램 응답 `ok` 필드 검증 추가**
- **과목/강의 선택 입력 공백 처리**: `strip()` 추가로 공백 포함 입력 시 번호/명령어 인식 실패 방지
- **`.secret_key` 디렉토리 충돌 수정**: Docker 바인드 마운트 시 `.secret_key`가 디렉토리로 생성된 경우 내부에 키 파일을 생성하도록 변경 (`IsADirectoryError` 해결)

### 변경
- **CI `uv sync` 플래그 수정**: `--dev` → `--extra dev` (uv 문법 오류 수정, `ruff`·`pytest` 설치 실패 해결)

---

## [v1.1.1] - 2026-03-13

### 추가
- **자동 업데이트 알림**: 앱 시작 시 Docker Hub API를 조회하여 현재 버전보다 최신 버전이 존재할 경우 메인 과목 목록 화면 상단에 업데이트 안내 배너 표시
  - 현재 버전 / 최신 버전 및 업데이트 명령어(`docker compose pull && docker compose run --rm study-helper`) 안내
  - 버전 체크는 과목 목록 로드와 병렬 실행 — 추가 대기 시간 없음
  - 네트워크 오류 또는 조회 실패 시 조용히 무시 (앱 시작 차단 없음)

---

## [v1.1.0] - 2026-03-10

### 변경
- **STT 엔진 교체**: `openai-whisper` → `faster-whisper` (CTranslate2 기반)
  - PyTorch 의존성 완전 제거 → Docker 이미지 크기 약 700MB 감소
  - CPU에서 약 2.5배 속도 향상 (INT8 양자화 적용)
  - 인식률 동일 또는 소폭 개선
  - wav 중간 파일 없이 mp3/mp4 직접 처리 (faster-whisper 내장 PyAV 오디오 디코딩)
  - 모델 캐시 경로 변경: `~/.cache/whisper` → `~/.cache/huggingface`
- **Dockerfile 간소화**: `pip install torch` 레이어 제거

---

## [v1.0.3] - 2026-03-10

### 수정
- **100% 완료 보고 ErrAlreadyInView 오류 수정**: `_report_completion` 함수에 `commons_frame` / `use_page_eval` 파라미터 추가
  - Plan A(video DOM 방식) 완료 후: `page.evaluate fetch`로 canvas.ssu.ac.kr 동일 오리진에서 호출 (sl=1 세션 중에도 정상 동작)
  - Plan B(진도 API 방식) 완료 후: 재생 루프에서 사용한 `commons_frame`을 그대로 재사용하여 JSONP 방식으로 호출 (ErrAlreadyInView 우회)
- **정상 재생 시 로그 파일 미생성**: 재생 성공 시 `play_ok` 로그를 저장하지 않도록 변경 — 오류/미완료 상태에서만 `logs/YYYYMMDD_HHMMSS_play.log` 생성
- **버전 자동 읽기**: `config.py`의 `APP_VERSION`을 정적 상수에서 `CHANGELOG.md` 첫 번째 `## [vX.Y.Z]` 항목을 파싱하는 동적 함수로 교체 — 버전 수동 갱신 불필요

### 추가
- **메인 화면 버전·학번 표시**: 과목 목록 화면 상단에 현재 앱 버전(`vX.Y.Z`)과 로그인된 학번을 표시
- **CHANGELOG.md Docker 이미지 포함**: `Dockerfile`에 `COPY CHANGELOG.md ./` 추가하여 Docker Hub 배포 이미지에서도 버전 자동 읽기 동작

---

## [v1.0.2] - 2026-03-09

### 수정
- **대용량 영상 다운로드 실패 수정**: `response.body()` 방식(전체 메모리 로드)을 Playwright 쿠키 추출 후 `requests` 스트리밍으로 교체 — Playwright 내부 문자열 크기 제한(`0x1fffffe8`)으로 인한 390MB 이상 파일 다운로드 오류 수정
- **content.php XML 구조 B 지원 추가**: `service_root > media > media_uri`에 `[MEDIA_FILE]` 플레이스홀더를 사용하는 구형 강의 포맷 지원 — `story_list/.../main_media` 파일명으로 치환하여 실제 URL 생성
- **다운로드 재시도 추가**: CDN 일시 오류(504 Gateway Time-out 등) 발생 시 지수 백오프(2초, 4초)로 최대 3회 자동 재시도

---

## [v1.0.1] - 2026-03-09

### 변경
- **Docker Hub 배포**: Docker Hub(`igor0670/study-helper`)를 통한 이미지 배포로 전환
  - `docker-compose.yml`을 로컬 빌드 대신 Docker Hub 이미지(`igor0670/study-helper:latest`) 사용으로 변경
  - GitHub Release에 `docker-compose.yml`, `.env.example` 첨부 파일 자동 포함
  - Release 노트에 Docker Hub 설치 방법 안내 추가
- **릴리즈 태그 정리**: `v1.0` 형식의 불필요한 중간 태그 생성 제거 — `{{version}}`(예: `1.0.1`)과 `latest` 두 태그만 생성
- **README 설치 방법 업데이트**: Docker Hub 이미지 기반 설치 흐름으로 재작성

### 보안
- **Debian base 이미지 고정**: `python:3.11-slim` → `python:3.11-slim-bookworm`으로 명시하여 빌드 재현성 확보
- **시스템 패키지 CVE 패치**: `apt-get upgrade -y` 추가로 알려진 취약점 대응
  - CVE-2026-1837 (jpeg-xl)
  - CVE-2026-23865 (freetype)
  - CVE-2025-45582 (tar)
- **Python 패키지 CVE 패치**:
  - CVE-2025-8869: `pip` 최신 버전으로 업그레이드
  - CVE-2026-24049: `wheel` 최신 버전으로 업그레이드
  - CVE-2025-68146, CVE-2026-22701: `filelock>=3.25.0` 제약 추가 (3.20.0 취약 버전 제외)

---

## [v1.0.0] - 2026-03-09

### 추가
- **자동 모드**: 지정된 스케줄(KST 기준 기본 09:00 / 13:00 / 18:00 / 23:00)마다 미시청 강의를 자동으로 재생 → 다운로드 → STT → AI 요약 → 텔레그램 알림 처리
  - 자동 모드 진입 시 스케줄 직접 설정 가능
  - 대기 화면에 다음 실행 시각 및 남은 시간 실시간 표시
  - STT·AI 요약·텔레그램 미설정 시 필수 조건 안내 후 설정 화면으로 이동
  - 오류 발생 강의는 건너뛰고 텔레그램으로 오류 알림 발송
- **텔레그램 알림**: 재생 완료/실패, 다운로드 실패, 다운로드 불가(learningx), AI 요약 완료, 자동 모드 오류 알림 지원
  - 요약 전송 후 파일 자동 삭제 옵션
  - 봇 토큰/Chat ID 입력 시 연결 테스트 자동 수행
- **다운로드 재시도**: URL 추출 실패 시 10초 간격으로 최대 3회 자동 재시도, 최종 실패 시에만 텔레그램 오류 알림 발송
- **learningx 강의 조기 감지**: 다운로드 불가 형식 강의를 URL로 즉시 감지하여 불필요한 재시도 없이 안내 메시지 표시
- **오류 로그**: 재생/다운로드 실패 시에만 `logs/YYYYMMDD_HHMMSS_<action>.log` 파일 자동 생성 (정상 동작 시 파일 미생성)
- **가이드 문서**: Gemini API 키 발급 가이드(`docs/gemini-api-key.md`), 텔레그램 봇 설정 가이드(`docs/telegram-setup.md`) 추가

### 변경
- 텔레그램 봇 토큰·Chat ID·API 키 입력 시 평문 표시로 변경 (붙여넣기 불가 문제 해결)
- 텔레그램 알림 메시지 양식 규격화

### 수정
- learningx 플레이어 강의 지원: `canvas.ssu.ac.kr/learningx/lti/lecture_attendance` 방식 강의를 자동 감지하여 learningx API에서 `viewer_url`을 조회, 기존 Plan B(진도 API 방식)로 출석 처리
- 재생 완료 후 강의 목록의 시청 상태(`completion`)를 즉시 갱신하여 재로드 없이 완료 표시 반영
- 강의 페이지 이동 시 `wait_until="networkidle"` → `domcontentloaded`로 변경하여 LMS 스트리밍/폴링으로 인한 30초 타임아웃 오류 수정
- 진도 API 요청에 `duration` 파라미터 누락으로 400 오류 발생하던 문제 수정
- ARM64(Apple Silicon) Docker 환경에서 Chromium H.264 미지원 우회: VP8 WebM 더미 영상으로 MP4 요청 인터셉트
- 백그라운드 재생 Plan B(진도 API 방식)에서 `endat=0.00`으로 인한 영상 길이 오류 수정, `LectureItem.duration`을 fallback으로 사용
- Playwright 브라우저 실행 인수에 `--password-store=basic` 추가하여 macOS Keychain 접근 경고 제거

---

## [v1.0.0-beta.3] - 2026-03-09

### 추가
- learningx 플레이어 강의 지원: `canvas.ssu.ac.kr/learningx/lti/lecture_attendance` 방식의 강의를 자동 감지하여 learningx API에서 `viewer_url`을 조회, 기존 Plan B(진도 API 방식)로 출석 처리
- 재생 완료 후 강의 목록의 시청 상태(`completion`)를 즉시 갱신하여 재로드 없이 완료 표시 반영

### 수정
- 강의 페이지 이동 시 `wait_until="networkidle"` → `domcontentloaded`로 변경하여 LMS 스트리밍/폴링으로 인한 30초 타임아웃 오류 수정
- 진도 API 요청에 `duration` 파라미터 누락으로 400 오류 발생하던 문제 수정 (재생 루프 및 `sendPlayedTime` JS 오버라이드 모두 반영)
- git credential helper를 `osxkeychain`에서 `store`로 변경하여 `failed to get/store: -25308` 오류 제거
- Playwright 브라우저 실행 인수에 `--password-store=basic` 추가하여 macOS Keychain 접근 경고 제거

### 변경
- 재생 화면에서 디버그 로그 비활성화, 프로그레스 바와 현재/전체 시간만 표시하도록 UI 정리

## [v1.0.0-beta.2] - 2026-03-07

### 추가
- ARM64(Apple Silicon) Docker 환경에서 Chromium H.264 미지원 우회: VP8 WebM 더미 영상으로 MP4 요청 인터셉트
- `canPlayType` / `MediaSource.isTypeSupported` 오버라이드로 플레이어가 MP4를 요청하도록 유도
- 네트워크 리스너(`request` / `response`) 및 route 핸들러를 강의별로 정확히 해제하여 누적 방지
- `docker compose run --rm` 단일 실행 방식 문서화 (`docker compose up` 사용 금지 명시)

### 수정
- 백그라운드 재생 Plan B(진도 API 방식)에서 player URL의 `endat=0.00`으로 인해 영상 길이를 알 수 없다는 오류가 발생하던 문제 수정
- `endat` 파라미터가 없을 때 `LectureItem.duration`(강의 목록에서 스크래핑한 값)을 fallback으로 사용하도록 개선
- VP8 WebM 생성 시 `-b:v 50 -crf 63` 조합으로 깨진 파일이 생성되던 문제 수정 → `-b:v 0 -crf 10` (순수 VBR 모드)으로 변경

## [v1.0.0-beta.1] - 2026-03-06

### 추가
- 숭실대학교 LMS 강의 백그라운드 재생
- 강의 영상(mp4) / 음성(mp3) 다운로드
- OpenAI Whisper 기반 STT 변환
- Gemini / OpenAI API 기반 AI 요약
- Docker 컨테이너 기반 CUI 환경 지원
- 계정 정보 암호화 저장
