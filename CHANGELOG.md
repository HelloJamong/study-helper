# Changelog

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
