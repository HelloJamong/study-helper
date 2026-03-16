import asyncio
import sys

from rich.console import Console
from rich.live import Live
from rich.text import Text

from src.config import Config
from src.scraper.course_scraper import CourseScraper
from src.scraper.models import Course
from src.ui.courses import _AUTO_SENTINEL, LectureAction, show_course_list, show_week_list
from src.ui.download import run_download
from src.ui.login import (
    show_login_error,
    show_login_progress,
    show_login_screen,
    show_login_success,
)
from src.ui.player import run_player
from src.ui.settings import run_settings
from src.updater import check_update

console = Console()

_MAX_LOGIN_ATTEMPTS = 3


async def run():
    # .env 파일이 없으면 빈 파일 생성 (볼륨 마운트 후 디렉토리가 생성되는 것 방지)
    from pathlib import Path

    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        env_path.touch()

    # ── 1. 인증 ──────────────────────────────────────────────────
    scraper: CourseScraper | None = None

    # .env에 저장된 계정이 있으면 자동 로그인 시도
    if Config.has_credentials():
        user_id = Config.LMS_USER_ID
        password = Config.LMS_PASSWORD
        show_login_progress()
        scraper = await _try_login(user_id, password)
        if scraper is None:
            show_login_error("저장된 계정으로 로그인 실패. 다시 입력해주세요.")
            # 자격증명을 삭제하지 않음 — 네트워크 오류일 수 있음

    # 로그인 실패 또는 저장된 계정 없으면 입력 받기
    attempts = 0
    while scraper is None:
        if attempts >= _MAX_LOGIN_ATTEMPTS:
            console.print("\n  [bold red]로그인 시도 초과. 프로그램을 종료합니다.[/bold red]")
            sys.exit(1)

        user_id, password = show_login_screen()
        if not user_id or not password:
            show_login_error("학번과 비밀번호를 모두 입력하세요.")
            attempts += 1
            continue

        show_login_progress()
        scraper = await _try_login(user_id, password)

        if scraper is None:
            attempts += 1
            show_login_error()
        else:
            show_login_success()
            Config.save_credentials(user_id, password)

    # ── 2. 최초 설정 (설정이 없으면 진행) ────────────────────────
    if not Config.has_settings():
        run_settings()

    # ── 3. 과목 목록 로드 + 버전 체크 (병렬) ─────────────────────
    try:
        (courses, details), latest_version = await asyncio.gather(
            _load_courses_task(scraper),
            _check_update_compat(),
        )
    except Exception as e:
        console.print(f"\n  [bold red]과목 목록 로드 실패:[/bold red] {e}")
        await scraper.close()
        sys.exit(1)

    # ── 3.5. 마감 임박 알림 체크 ─────────────────────────────────
    tg = Config.get_telegram_credentials()
    if tg:
        from src.notifier.deadline_checker import check_and_notify_deadlines

        deadline_count = check_and_notify_deadlines(courses, details, token=tg[0], chat_id=tg[1])
        if deadline_count > 0:
            console.print(f"  [yellow]마감 임박 항목 {deadline_count}건 — 텔레그램 알림 전송 완료[/yellow]")

    # ── 4. 과목 선택 루프 ────────────────────────────────────────
    while True:
        selected = show_course_list(courses, details, user_id=user_id, latest_version=latest_version)
        if selected is None:
            console.print("\n  [dim]종료합니다.[/dim]\n")
            break

        if selected is _AUTO_SENTINEL:
            from src.ui.auto import run_auto_mode

            await run_auto_mode(scraper, courses, details)
            continue

        idx = courses.index(selected)
        detail = details[idx]
        if detail is None:
            console.print("\n  [red]강의 정보를 불러오지 못했습니다.[/red]\n")
            continue

        result = show_week_list(selected, detail)
        if result is None:
            continue

        lec, action = result
        if action == LectureAction.PLAY:
            success, has_error = await run_player(scraper._page, lec, debug=False)
            if success:
                lec.completion = "completed"
                _tg_notify_playback_complete(selected.long_name, lec)
            else:
                _tg_notify_playback_error(selected.long_name, lec, failed=has_error)
            input("\n  Enter를 눌러 계속...")
        elif action == LectureAction.DOWNLOAD:
            rule = Config.DOWNLOAD_RULE or "both"
            audio_only = rule == "audio"
            both = rule == "both"
            await run_download(scraper._page, lec, selected, audio_only=audio_only, both=both)
            input("\n  Enter를 눌러 계속...")

    await scraper.close()


async def _try_login(user_id: str, password: str) -> CourseScraper | None:
    """CourseScraper로 로그인을 시도한다. 실패 시 None 반환."""
    scraper = CourseScraper(username=user_id, password=password)
    try:
        await scraper.start()
        return scraper
    except RuntimeError:
        await scraper.close()
        return None
    except Exception:
        await scraper.close()
        return None


async def _load_courses_task(scraper: CourseScraper):
    """_load_courses를 asyncio.gather용으로 래핑한다."""
    return await _load_courses(scraper)


async def _check_update_compat():
    """버전 체크를 스레드풀에 위임하여 이벤트 루프 블로킹을 방지한다."""
    from src.config import APP_VERSION

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, check_update, APP_VERSION)


async def _load_courses(scraper: CourseScraper):
    """과목 목록을 가져온 뒤 각 과목의 강의 상세를 병렬로 로드한다."""
    with Live(
        Text("  과목 목록 불러오는 중...", style="yellow"),
        console=console,
        transient=True,
    ):
        courses: list[Course] = await scraper.fetch_courses()

    completed_count = 0
    total = len(courses)

    def _progress_text():
        return Text(f"  강의 정보 병렬 로딩 중... ({completed_count}/{total})", style="yellow")

    with Live(_progress_text(), console=console, transient=True) as live:

        def _on_complete():
            nonlocal completed_count
            completed_count += 1
            live.update(_progress_text())

        details = await scraper.fetch_all_details(courses, concurrency=3, on_complete=_on_complete)

    return courses, details


def _tg_notify_playback_complete(course_name: str, lec) -> None:
    """재생 완료 텔레그램 알림 전송."""
    creds = Config.get_telegram_credentials()
    if not creds:
        return
    token, chat_id = creds
    from src.notifier.telegram_notifier import notify_playback_complete

    notify_playback_complete(
        bot_token=token,
        chat_id=chat_id,
        course_name=course_name,
        week_label=lec.week_label,
        lecture_title=lec.title,
    )


def _tg_notify_playback_error(course_name: str, lec, failed: bool = True) -> None:
    """재생 실패/미완료 텔레그램 알림 전송.

    Args:
        failed: True면 재생 오류, False면 재생 미완료(중단)
    """
    creds = Config.get_telegram_credentials()
    if not creds:
        return
    token, chat_id = creds
    from src.notifier.telegram_notifier import notify_playback_error

    notify_playback_error(
        bot_token=token,
        chat_id=chat_id,
        course_name=course_name,
        week_label=lec.week_label,
        lecture_title=lec.title,
        failed=failed,
    )


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
