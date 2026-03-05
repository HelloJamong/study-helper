import asyncio
import sys
from typing import List, Optional

from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text

from src.config import Config
from src.scraper.course_scraper import CourseScraper
from src.scraper.models import Course, CourseDetail
from src.ui.login import (
    show_login_screen,
    show_login_progress,
    show_login_error,
    show_login_success,
)
from src.ui.courses import show_course_list, show_loading

console = Console()

_MAX_LOGIN_ATTEMPTS = 3


async def run():
    # .env 파일이 없으면 빈 파일 생성 (볼륨 마운트 후 디렉토리가 생성되는 것 방지)
    from pathlib import Path
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        env_path.touch()

    # ── 1. 인증 ──────────────────────────────────────────────────
    scraper: Optional[CourseScraper] = None

    # .env에 저장된 계정이 있으면 자동 로그인 시도
    if Config.has_credentials():
        user_id = Config.LMS_USER_ID
        password = Config.LMS_PASSWORD
        show_login_progress()
        scraper = await _try_login(user_id, password)
        if scraper is None:
            show_login_error("저장된 계정으로 로그인 실패. 다시 입력해주세요.")
            Config.LMS_USER_ID = ""
            Config.LMS_PASSWORD = ""

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

    # ── 2. 과목 목록 로드 ────────────────────────────────────────
    try:
        courses, details = await _load_courses(scraper)
    except Exception as e:
        console.print(f"\n  [bold red]과목 목록 로드 실패:[/bold red] {e}")
        await scraper.close()
        sys.exit(1)

    # ── 3. 과목 선택 루프 ────────────────────────────────────────
    while True:
        selected = show_course_list(courses, details)
        if selected is None:
            console.print("\n  [dim]종료합니다.[/dim]\n")
            break

        # 다음 Phase에서 강의 목록 화면으로 연결
        console.print(f"\n  [cyan]{selected.long_name}[/cyan] 선택됨 — 강의 목록은 다음 업데이트에서 제공됩니다.\n")
        input("  Enter를 눌러 돌아가기...")

    await scraper.close()


async def _try_login(user_id: str, password: str) -> Optional[CourseScraper]:
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


async def _load_courses(scraper: CourseScraper):
    """과목 목록과 각 과목의 강의 상세를 병렬로 로드한다."""
    with Live(
        Text("  과목 목록 불러오는 중...", style="yellow"),
        console=console,
        transient=True,
    ):
        courses: List[Course] = await scraper.fetch_courses()

    details: List[Optional[CourseDetail]] = []
    for i, course in enumerate(courses, 1):
        with Live(
            Text(f"  강의 정보 로딩 중... ({i}/{len(courses)}) {course.long_name}", style="yellow"),
            console=console,
            transient=True,
        ):
            try:
                detail = await scraper.fetch_lectures(course)
            except Exception:
                detail = None
        details.append(detail)

    return courses, details


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
