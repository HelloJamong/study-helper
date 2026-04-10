# Changelog

## [v26.04.01] - 2026-04-11

### 수정
- **Chromium 메모리 누수 방지 플래그 추가** (`src/scraper/course_scraper.py`)
  - `--js-flags=--max-old-space-size=1024`: V8 JS 힙 상한을 1 GB로 제한 — 상한 초과 시 강제 GC 트리거
  - `--aggressive-cache-discard`: 메모리 압박 감지 시 탭 캐시를 적극 해제
  - `--renderer-process-limit=2`: 렌더러 프로세스 수 제한 — 탭 하나만 사용하므로 기본값(CPU 코어 수) 대비 메모리 절감
- **자동 모드 강의 간 페이지 초기화** (`src/ui/auto.py`)
  - 강의 처리 완료 후 `about:blank`로 이동하여 Chromium 렌더러 메모리(비디오 디코드 버퍼, JS 힙, DOM) 즉시 해제
  - `finally` 블록에 추가 — 재생 성공·실패·예외 모든 경우에 실행
  - 다수 강의 연속 처리 시 메모리가 7~8 GB까지 증가하던 문제 해소

---

## [v26.03.18] - 2026-03-23

### 수정
- **README curl 다운로드 경로 수정** (`README.md`)
  - GitHub 사용자명 오기 수정: `igor0670` → `HelloJamong`
  - `.env.example` 다운로드 URL: `default.env.example` → `.env.example` (릴리즈 asset 파일명 일치)
- **릴리즈 asset 파일명 수정** (`.github/workflows/release.yml`)
  - 릴리즈 업로드 파일명이 `default.env.example`로 올라가던 문제 수정 — `.env.example`로 통일

---

## [v26.03.17] - 2026-03-23

### 수정
- **readystream(content_type=15) 강의 진도 미등록 문제 수정** (`src/player/background_player.py`)
  - 원인 1: `route.abort()`로 `flashErrorPage.html` 차단 시 Playwright frame이 `chrome-error://chromewebdata/` broken state로 전환되어 이후 JSONP `<script>` cross-origin 로드 차단
  - 원인 2: `flashErrorPage`로 navigate된 frame을 재사용 불가로 판단하여 sl=1 세션을 폐기하고 새 세션 생성 → 서버가 기존 세션을 여전히 점유 중으로 인식해 `ErrAlreadyInView` 반복
  - `_block_flash_global` / `_block_flash_error_page`: `route.abort()` → `route.fulfill(빈 HTML)`로 변경 — fulfill은 서버에 요청이 도달하지 않으므로 서버 측 sl=1 세션을 살려둔 채 frame을 정상 상태로 유지
  - frame 재사용 조건 완화: fulfill 방식으로 대체된 flashErrorPage URL이어도 live frame이면 기존 sl=1 세션 그대로 재사용
  - fake video route(VP8 WebM)를 `fallback_duration` 유무와 무관하게 항상 등록 — preloader.mp4 codec check를 초기화 시점에 확실히 통과시켜 H.264 미지원 환경에서 flashErrorPage 진입 자체를 차단

### 추가
- **과목 강의 목록 로딩 실패 시 에러 로그 파일 저장** (`src/scraper/course_scraper.py`)
  - `fetch_all_details()`에서 예외 발생 시 전체 traceback을 `logs/YYYYMMDD_HHMMSS_scraper_error.log`에 저장
  - 기존에는 TUI 화면에만 출력되어 `- / -` 원인 파악 불가 → 파일 저장으로 사후 분석 가능

---

## [v26.03.16] - 2026-03-21

### 추가
- **비전채플 과목 전용 AI 요약 섹션** (`src/summarizer/summarizer.py`, `src/ui/download.py`)
  - 과목명에 "비전채플"이 포함된 경우 요약 결과에 두 섹션을 자동 추가
  - `[강연자 소개]`: 강연자 이름·소속·직함·운영 단체 (텍스트 미언급 시 생략)
  - `[성경 말씀]`: 강연 중 인용·언급된 성경 구절 목록 (미언급 시 생략)
  - `run_download()`에서 `course.long_name`을 `summarize()`에 전달하여 과목별 프롬프트 분기

### 수정
- **`ErrAlreadyInView` 반복 발생으로 진도 미등록 문제 수정** (`src/player/background_player.py`)
  - 원인 1: Plan B(`_play_via_progress_api`) 진입 시 commons 프레임을 `sl=0`으로 재로드하면 서버 측 sl=1 세션이 닫히지 않아 이후 JSONP 호출이 계속 `ErrAlreadyInView`를 반환
  - 원인 2: play 버튼 클릭 후 원본 `em/...` commons 프레임이 `flashErrorPage.html`로 navigate되어 Python Frame 객체가 `page.frames`에서 분리(detach)되는데, 이를 감지하지 못해 재로드 경로가 비정상 동작
  - `existing_commons_frame` 유효성 검증을 `is not None` 단순 체크에서 `page.frames` 멤버십 체크로 강화
  - detach된 경우 `player_url`(sl=1 포함)로 `page.goto` 재로드 — 서버에 현재 세션을 active viewer로 재등록 후 JSONP 호출하여 ErrAlreadyInView 우회
  - Plan A→B 전환 시 `existing_commons_frame=player_frame` 전달로, commons frame이 살아있는 경우 재로드 없이 동일 sl=1 세션에서 JSONP 직접 주입

---

## [v26.03.15] - 2026-03-20

### 수정
- **업그레이드 알림에 `[dim]`/`[/dim]` 태그가 그대로 출력되는 문제 수정** (`src/ui/courses.py`)
  - 원인: `Panel` 내 `Text()` 객체는 Rich 마크업을 파싱하지 않아 태그가 문자열로 노출
  - `Text()` 제거 후 마크업 문자열을 `Panel`에 직접 전달하도록 수정

---

## [v26.03.14] - 2026-03-20

### 수정
- **`endat` 이전 시청 위치를 강의 길이로 오인하는 문제 수정** (`src/player/background_player.py`)
  - 원인: `_play_via_progress_api()`에서 `_parse_player_url()`이 파싱한 `endat` 파라미터(이전 시청 위치)를 그대로 강의 총 길이(`duration`)로 사용하여 실제 강의(4407초)를 330초로 진도 보고 → LMS가 미시청으로 유지
  - `fallback_duration`이 `endat` 기반 `duration`보다 10초 이상 크면 실제 강의 길이로 교체하도록 수정
  - 결과: 자동 모드에서 이미 시청 완료된 강의가 매 스케줄마다 반복 재생·요약되던 문제 해소
- **재생 완료 후 `0 + Enter` 종료 시 여러 번 입력해야 동작하는 문제 수정** (`src/ui/player.py`, `src/ui/auto.py`)
  - 원인: `_stop_listener`(player.py) / `_input_listener`(auto.py)의 `run_in_executor(readline)` 블로킹 스레드가 asyncio 태스크 취소 후에도 계속 대기하다 다음 Enter 입력을 소비
  - `finally` 블록에 `termios.tcflush(sys.stdin, TCIFLUSH)` 추가하여 stdin 버퍼 잔존 입력 제거

---

## [v26.03.13] - 2026-03-17

### 수정
- **재생 시 세션 만료 자동 재로그인** (`src/player/background_player.py`)
  - `page.goto(lecture_url)` 후 로그인 페이지로 리다이렉트된 경우(`/login` 포함 URL) 감지
  - `ensure_logged_in()`으로 자동 재로그인 후 강의 페이지 재이동 — "비디오 프레임을 찾지 못했습니다" 오류 방지
- **재생 시간 5분 30초 고정 문제 근본 해결** (`src/player/background_player.py`)
  - 원인: LMS `attendance_items` API의 `viewer_url`에 이전 진도(`startat=330.00&endat=330.00`)가 고정값으로 내려와 commons 플레이어가 330초 기준으로 동작
  - `_fix_commons_endat` route 핸들러 추가: `commons.ssu.ac.kr/em/` 요청을 가로채 `endat`를 sniff된 실제 duration으로 교정 후 302 redirect
  - `_play_via_learningx_api()`에서 `viewer_url`의 `endat` 파라미터도 직접 교정
  - `fallback_duration=0`으로 변경하여 fake webm 비활성화 — 실제 duration은 sniff/meta에서 확보
  - `_shared_duration: list[float]`(mutable container)로 duration을 공유하여 클로저 스코프 문제 해소
- **q+Enter 사용자 중단 시 텔레그램 오류 알림 발송 방지** (`src/ui/player.py`, `src/ui/auto.py`, `src/main.py`)
  - `run_player()` 반환값을 `(success, has_error)` → `(success, has_error, user_cancelled)` 3-tuple로 변경
  - 사용자가 q+Enter로 의도적으로 중단한 경우 `user_cancelled=True` — 텔레그램 오류 알림 발송 안 함
- **q+Enter / 0+Enter 두 번 입력해야 동작하는 문제 수정** (`src/ui/auto.py`)
  - 원인: 자동 모드 `_input_listener`와 player의 `_stop_listener`가 동시에 `sys.stdin.readline()`을 경쟁하여 한 입력을 두 태스크가 나눠 소비
  - `playing_event = asyncio.Event()` 추가: 재생 중 `_input_listener`가 stdin을 읽어도 버리도록 처리
- **AI 요약 500 INTERNAL 오류 시 재시도** (`src/ui/download.py`)
  - Gemini 서버 일시 오류 발생 시 최대 3회, 5초 간격으로 자동 재시도

---

## [v26.03.12] - 2026-03-17

### 수정
- **`endat=0.00` 강의 잘못된 재생 시간 사용 문제 수정** (`src/player/background_player.py`)
  - LectureItem의 `duration` 필드(강의 목록 표시용, 예: "05:30")가 `fallback_duration`으로 전달되어 실제 영상 길이(1시간 13분)와 무관한 짧은 시간으로 재생되던 문제 해소
  - sniff 리스너(`page.on("response")`)가 `attendance_items` 응답의 `text()`를 debug 리스너와 동시에 읽다 실패해 실제 duration(4407초)을 캡처하지 못하는 경우 대비책 추가
  - Plan B 진입 시 sniff 실패한 경우 commons frame DOM의 `<meta name="commons.duration">` 값을 직접 읽어 duration 추출 — `page.request.get()` 없이 이미 로드된 HTML에서 읽으므로 401 문제 없음
  - sniff 값이 있을 때 기존 `fallback_duration` 값과 무관하게 항상 덮어쓰도록 변경 (기존 `fallback_duration <= 0` 조건 제거)
  - learningx 플레이어 감지 분기에서도 `_fetch_learningx_duration` 결과를 항상 적용하도록 동일 조건 제거
- **자동 모드 `auto_progress.json` 의존성 제거** (`src/ui/auto.py`)
  - 처리 완료된 강의 URL을 파일에 영구 저장하고 LMS 상태와 무관하게 건너뛰던 구조 제거
  - 이제 LMS의 `completion` 상태(`lec.needs_watch`)만으로 미시청 여부 판단 — 스케줄마다 LMS를 재스크래핑하므로 LMS에 완료 반영 시 자동으로 건너뜀
  - 기존 `data/auto_progress.json` 파일은 더 이상 참조되지 않음
- **재생 중 Ctrl+C로 현재 강의만 중단 가능** (`src/player/background_player.py`, `src/ui/player.py`)
  - `play_lecture()`에서 `asyncio.CancelledError`를 잡아 `state.error = "사용자 중단"`으로 반환 — 예외가 상위로 전파되어 프로세스 전체가 비정상 종료되던 문제 해소
  - 개별 재생: Ctrl+C 시 "재생이 중단되었습니다." 출력 후 과목 선택 화면으로 복귀 (텔레그램 알림·로그 저장 없음)
  - 자동 모드: Ctrl+C 시 현재 강의만 중단 후 auto 루프 계속 진행. 전체 종료는 "0 + Enter" 또는 재생 대기 중 Ctrl+C

---

## [v26.03.11] - 2026-03-17

### 기타
- **버전 형식 변경**: `v1.x.x` → `v연도.월.릴리즈순번` (예: `v26.03.11` = 26년 3월 11번째 릴리즈)

### 변경
- **자동 모드 진입 시 즉시 1회 실행** (`src/ui/auto.py`)
  - 기존: 자동 모드 진입 후 다음 스케줄 시각까지 대기한 뒤 첫 실행
  - 변경: 진입 즉시 1회 스케줄 체크·처리 실행 후 이후부터 스케줄 주기에 맞춰 동작
- **자동 모드 스케줄 설정 화면에 즉시 실행 안내 추가** (`src/ui/auto.py`)
  - 스케줄 설정 진입 시 "자동 모드 시작 시 즉시 1회 실행된 후 스케줄에 따라 반복됩니다" 안내 문구 표시

### 수정
- **강의 목록 `- / -` 표시 문제 수정** (`src/scraper/course_scraper.py`)
  - `_fetch_lectures_on()`에서 `domcontentloaded` + iframe src 폴링 방식이 Canvas JS 실행 타이밍과 맞지 않아 iframe 연결에 실패하던 문제 해소
  - 강의 목록 페이지 이동을 `networkidle` (timeout 60초)로 복원 — Canvas JS 실행 및 `iframe#tool_content` 로드까지 자연스럽게 대기
  - `.xnmb-module-list` 출현 시까지 명시적 대기 추가로 SPA 렌더링 완료 보장
- **전체 펼치기 버튼 클릭 실패 수정** (`src/scraper/course_scraper.py`)
  - Canvas 상단 네비게이션 바(`ic-app-nav-toggle-and-crumbs`)가 `.xnmb-all_fold-btn` 위에 겹쳐 pointer events를 intercept하여 `ElementHandle.click()` 30초 타임아웃으로 실패하던 문제 해소
  - `await expand_btn.click()` → `await expand_btn.evaluate("el => el.click()")` 로 변경하여 오버레이 무관하게 JS 직접 클릭 실행
- **병렬 로딩 복원** (`src/scraper/course_scraper.py`)
  - 디버깅 목적으로 순차 처리로 변경했던 `fetch_all_details()`를 `asyncio.Semaphore(concurrency=3)` + `asyncio.gather` 병렬 방식으로 재복원
  - 각 과목을 독립 탭(`new_page()`)에서 처리하므로 Canvas nav 오버레이가 다른 탭에 영향 없음
- **`re` 모듈 미import로 인한 재생 실패 수정** (`src/player/background_player.py`)
  - `_play_via_progress_api()` 내 `attendance_items` fallback 코드에서 `re.search()` 사용 시 `name 're' is not defined` 오류 발생
  - 파일 상단에 `import re` 추가
- **learningx 플레이어 LTI 500 오류 시 재생 실패 수정** (`src/player/background_player.py`)
  - LTI POST가 500으로 실패하면 `tool_content` iframe이 초기화되지 않아 commons frame 탐색 실패 → learningx API 401 오류로 재생 불가했던 문제 해소
  - learningx 플레이어 감지 시 즉시 API 호출 대신 `networkidle` 대기 후 commons frame 재탐색 — LTI 세션이 지연 수립되는 경우 Plan A(DOM 재생)로 정상 진행
  - `networkidle` 후에도 commons frame이 없을 경우에만 Plan B(`_play_via_learningx_api`) 진입
  - learningx API 호출 시 `page.evaluate(fetch)` 방식이 401이면 `page.request.get()`(브라우저 컨텍스트 전체 쿠키 포함)으로 자동 재시도
- **`endat=-8888` / `endat=0.00` 강의 "영상 길이를 알 수 없습니다" 오류 수정** (`src/player/background_player.py`)
  - `page.request.get()`으로 `attendance_items` API 직접 호출 시 항상 401이 반환되는 문제 해소
  - `page.on("response")` sniff 리스너로 브라우저가 자동 전송하는 `attendance_items` 응답을 가로채 `duration`을 `_sniffed_duration` 컨테이너에 캡처
  - video frame 없음(Plan B 진입) 시점에 sniff된 duration을 `fallback_duration`으로 적용하여 진도 API 시뮬레이션 정상 동작

---

## [v1.1.5] - 2026-03-17

### 수정
- **강의 목록 로딩 속도 개선** (`src/scraper/course_scraper.py`)
  - `start()` / `fetch_courses()` 대시보드 이동: `networkidle` → `domcontentloaded` + `wait_for_function`으로 `STUDENT_PLANNER_COURSES` JS 변수 주입 명시적 대기
  - `_fetch_lectures_on()` 강의 목록 이동: `networkidle` → `domcontentloaded` + `wait_for_function`으로 `iframe#tool_content` src 설정 명시적 대기
  - `networkidle`은 Learning X SPA 폴링으로 인해 최대 30초 타임아웃까지 블로킹되는 경우가 있어 병렬 로딩 시 전체 소요 시간이 증가하는 문제 해소
- **과목 목록 잘못된 과목 표시 수정** (`src/scraper/course_scraper.py`)
  - `fetch_courses`에서 `term` 필드 유무만으로 필터링하던 방식을 개선 — `term` 값별 과목 수를 집계해 가장 많이 등장하는 학기를 현재 학기로 간주, 해당 학기 과목만 반환
  - 이전 학기 과목(비전 채플 등)이 즐겨찾기 등으로 잔존해 목록에 표시되던 문제 해소
- **과목 선택 시 주차 화면으로 이동 안 되는 문제 수정** (`src/ui/courses.py`, `src/main.py`)
  - `show_course_list`가 `Course` 객체만 반환하고 `main.py`에서 `courses.index(selected)`로 인덱스를 재탐색하던 방식을 `(Course, idx)` 튜플 반환으로 변경
  - `courses.index()`의 equality 비교로 과목명·학기가 동일한 항목이 있을 때 잘못된 인덱스가 반환되어 `detail`이 매핑되지 않던 문제 제거

---

## [v1.1.4] - 2026-03-17

### 수정
- **learningx `endat=-8888` sentinel 값으로 인한 재생 실패 수정** (`src/player/background_player.py`)
  - `_parse_player_url`에서 `endat` 파라미터가 음수(Learning X가 duration 미확정 강의에 사용하는 `-8888` 등 sentinel 값)인 경우 `0`으로 정규화하도록 수정
  - 이전: `endat=-8888` → `duration = -8888.0` → `fallback_duration`이 있어도 `duration <= 0` 분기에서 활용되지 못하고 "영상 길이를 알 수 없습니다" 오류로 실패
  - 이후: `endat=-8888` → `duration = 0.0` → `fallback_duration`(learningx API `item_content_data.duration`)으로 정상 fallback
  - `content_type=movie` 강의(대면 강의 등) 재생 실패 사례 해소

---

## [v1.1.3] - 2026-03-16

### 추가
- **마감 임박 텔레그램 알림**: 퀴즈, 과제, 토론 등 비디오 외 항목의 마감 24시간·12시간 전 텔레그램 알림 전송 (`src/notifier/deadline_checker.py` 신규)
  - 중복 알림 방지: `deadline_notified.json`으로 전송 이력 관리
  - 완료(completion)·출석(attendance)·예정(is_upcoming) 상태 항목은 알림 제외
  - 연도 전환기(12월→1월, 1월→12월) 날짜 파싱 보정
- **강의 상세 병렬 로딩**: `fetch_all_details(concurrency=3)`으로 전체 과목 강의 정보를 동시에 스크래핑하여 초기 로딩 속도 개선
  - 병렬 재로그인 중복 방지 플래그(`_session_restored`) 추가
  - 로딩 진행 상황 실시간 표시 (`강의 정보 병렬 로딩 중... N/총수`)
- **다운로드 경로 구조화**: 저장 경로를 `과목명/N주차/강의명.mp4` 계층 구조로 변경 (기존: `과목명_강의명.mp4` 단일 파일)
- **`Config.get_telegram_credentials()`**: 텔레그램 활성화 여부와 credential 유효성을 한 번에 검증하는 헬퍼 메서드 추가
- **`KST` 공용 상수**: `config.py`에 KST 타임존 상수 추가, 여러 모듈에서 재사용

### 수정
- **Path Traversal 방어 강화**: `_sanitize_filename`에서 `..` 완전 제거(`re.sub`), `is_relative_to()`로 경로 경계 이중 검증
- **이벤트 루프 블로킹 해소**: 버전 체크(`check_update`) 호출을 `run_in_executor`로 스레드풀에 위임하여 비동기 루프 블로킹 방지 (`get_event_loop()` → `get_running_loop()`)
- **마감 알림 제외 조건 강화**: `completion` 외 `attendance`(출석/지각/면제), `is_upcoming`(예정) 상태도 알림 제외 처리
- **`download.py` 텔레그램 오류 알림 통일**: `_tg_error` 함수를 `Config.get_telegram_credentials()` 방식으로 통일
- **`auto.py` 진행 상태 저장/복원 에러 로깅**: `_load/_save_progress`에 예외 발생 시 로그 출력 추가

---

## [v1.1.2] - 2026-03-13

### 추가
- **CI/CD 파이프라인**: GitHub Actions에서 Lint, 단위 테스트, Docker 빌드 자동 검증
- **단위 테스트 26개**: `crypto`, `models`, `config`, `summarizer`, `converter`, `transcriber` 모듈 커버리지 확보
- **STT 언어 선택**: 한국어(ko) / 영어(en) / 자동 감지(auto) 옵션 추가
- **AI 요약 커스텀 프롬프트**: 사용자 정의 프롬프트 지원
- **세션 만료 자동 재로그인**: Learning X 세션 만료 감지 시 자동으로 재인증
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
- 강의 페이지 이동 시 `wait_until="networkidle"` → `domcontentloaded`로 변경하여 Learning X 스트리밍/폴링으로 인한 30초 타임아웃 오류 수정
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
- 강의 페이지 이동 시 `wait_until="networkidle"` → `domcontentloaded`로 변경하여 Learning X 스트리밍/폴링으로 인한 30초 타임아웃 오류 수정
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
- 숭실대학교 Learning X 강의 백그라운드 재생
- 강의 영상(mp4) / 음성(mp3) 다운로드
- OpenAI Whisper 기반 STT 변환
- Gemini / OpenAI API 기반 AI 요약
- Docker 컨테이너 기반 CUI 환경 지원
- 계정 정보 암호화 저장
