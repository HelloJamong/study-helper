"""
재생 화면 UI.

백그라운드 재생 진행 상태를 rich Progress bar로 표시한다.
"""

import asyncio
import sys

from rich.console import Console
from rich.live import Live
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
)

from src.config import Config
from src.logger import get_error_logger
from src.player.background_player import PlaybackState, play_lecture
from src.scraper.models import LectureItem

console = Console()


def _fmt_time(seconds: float) -> str:
    """초를 MM:SS 형식으로 변환한다."""
    s = max(0, int(seconds))
    m, sec = divmod(s, 60)
    return f"{m:02d}:{sec:02d}"


def _parse_duration(duration_str: str | None) -> float:
    """'MM:SS' 형식의 문자열을 초로 변환한다. 파싱 실패 시 0.0 반환."""
    if not duration_str:
        return 0.0
    try:
        parts = duration_str.split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except Exception:
        pass
    return 0.0


def _tg_playback_error(lec: LectureItem, failed: bool = True) -> None:
    """재생 실패/미완료 시 텔레그램 알림을 전송한다 (설정된 경우에만)."""
    if Config.TELEGRAM_ENABLED != "true":
        return
    token = Config.TELEGRAM_BOT_TOKEN
    chat_id = Config.TELEGRAM_CHAT_ID
    if not token or not chat_id:
        return
    try:
        from src.notifier.telegram_notifier import notify_playback_error

        notify_playback_error(token, chat_id, "", lec.week_label, lec.title, failed=failed)
    except Exception:
        pass


async def run_player(page, lec: LectureItem, debug: bool = False) -> tuple[bool, bool, bool]:
    """
    강의를 백그라운드 재생하고 CUI로 진행 상태를 표시한다.

    Args:
        page: CourseScraper._page (Playwright Page)
        lec:  재생할 LectureItem

    Returns:
        (success, has_error, user_cancelled)
        - success=True: 정상 완료
        - success=False, has_error=True: 재생 오류
        - success=False, has_error=False, user_cancelled=True: 사용자 중단(q+Enter / Ctrl+C)
        - success=False, has_error=False, user_cancelled=False: 재생 미완료
    """
    console.clear()
    console.print("  [dim]q + Enter 로 재생 중단[/dim]")
    console.print()

    # LectureItem.duration에서 예상 전체 시간 추출 (없으면 나중에 영상에서 채움)
    estimated_duration = _parse_duration(lec.duration)

    progress = Progress(
        SpinnerColumn(),
        TextColumn("  [bold]{task.description}"),
        BarColumn(bar_width=40),
        TextColumn("{task.fields[time_str]}"),
        console=console,
        expand=False,
    )

    total_ticks = max(int(estimated_duration), 1)
    task_id: TaskID = progress.add_task(
        lec.title[:40],
        total=total_ticks,
        time_str="--:-- / --:--",
    )

    result: dict = {"state": None}

    # 재생 로그를 파일에 직접 스트리밍 — 오류 시에만 유지, 정상 완료 시 삭제
    _play_logger, _log_path = get_error_logger("play")
    _play_logger.info(f"강의: {lec.title}")
    _play_logger.info(f"URL: {lec.full_url}")
    _play_logger.info("--- 재생 로그 ---")

    def _log(msg: str):
        _play_logger.info(msg)

    def _close_play_logger(keep: bool) -> None:
        for h in list(_play_logger.handlers):
            h.close()
            _play_logger.removeHandler(h)
        if not keep:
            try:
                _log_path.unlink(missing_ok=True)
            except Exception:
                pass

    def on_progress(state: PlaybackState):
        """플레이어 콜백 → Progress bar 업데이트."""
        result["state"] = state

        dur = state.duration if state.duration > 0 else estimated_duration
        cur = state.current

        # duration이 실제로 확인되면 total 재설정
        if state.duration > 0 and progress.tasks[task_id].total != int(state.duration):
            progress.update(task_id, total=int(state.duration))

        time_str = f"{_fmt_time(cur)} / {_fmt_time(dur)}"
        progress.update(
            task_id,
            completed=int(cur),
            time_str=time_str,
        )

    play_task = asyncio.ensure_future(
        play_lecture(
            page=page,
            lecture_url=lec.full_url,
            on_progress=on_progress,
            debug=True,  # 항상 로그 수집 (오류 시 파일로 저장)
            fallback_duration=0,  # lec.duration은 표시용 — 실제 duration은 sniff/meta로 확보
            log_fn=_log,
        )
    )

    async def _stop_listener():
        """재생 중 'q' + Enter 입력 시 재생 태스크를 취소한다."""
        loop = asyncio.get_event_loop()
        while not play_task.done():
            try:
                line = await loop.run_in_executor(None, sys.stdin.readline)
                if line.strip().lower() == "q":
                    play_task.cancel()
                    break
            except Exception:
                break

    stop_task = asyncio.ensure_future(_stop_listener())

    with Live(progress, console=console, refresh_per_second=4):
        try:
            final_state = await play_task
        finally:
            stop_task.cancel()
            try:
                await stop_task
            except asyncio.CancelledError:
                pass
            # readline 블로킹 스레드 해제: 가짜 개행을 stdin에 주입해 스레드를 깨운 뒤 플러시.
            # stop_task.cancel() 후에도 run_in_executor 스레드는 readline에서 블로킹 중이므로
            # 다음 Prompt.ask 입력을 가로채는 문제가 생긴다. \n 주입으로 즉시 해제 후 플러시.
            try:
                import os
                import termios

                os.write(sys.stdin.fileno(), b"\n")
                await asyncio.sleep(0.05)
                termios.tcflush(sys.stdin, termios.TCIFLUSH)
            except Exception:
                pass

    console.print()

    if final_state.error:
        if final_state.error == "사용자 중단":
            console.print("  [yellow]재생이 중단되었습니다.[/yellow]")
            _close_play_logger(keep=False)
            return False, False, True
        console.print(f"  [bold red]재생 오류:[/bold red] {final_state.error}")
        _play_logger.info(f"오류: {final_state.error}")
        _close_play_logger(keep=True)
        console.print(f"  [dim]로그 저장: {_log_path}[/dim]")
        _tg_playback_error(lec, failed=True)
        return False, True, False

    if final_state.ended:
        console.print("  [bold green]재생 완료![/bold green]")
        _close_play_logger(keep=False)
        return True, False, False

    # 재생 미완료(중단)
    console.print("  [yellow]재생이 중단되었습니다.[/yellow]")
    _close_play_logger(keep=False)
    _tg_playback_error(lec, failed=False)
    return False, False, False
