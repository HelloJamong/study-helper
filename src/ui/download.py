"""
다운로드 관련 UI.

다운로드 진행률 화면을 제공한다.
다운로드 경로는 설정(settings)에서 관리하며, Config에서 직접 읽는다.
"""

from pathlib import Path

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, DownloadColumn, Progress, SpinnerColumn, TextColumn, TransferSpeedColumn
from rich.text import Text

from src.config import Config

console = Console()


async def run_download(page, lec, course, audio_only: bool = False, both: bool = False) -> bool:
    """
    강의 영상을 다운로드하고 진행률을 Progress bar로 표시한다.

    Args:
        page:       CourseScraper._page (Playwright Page)
        lec:        다운로드할 LectureItem
        course:     과목 Course (파일명 생성에 사용)
        audio_only: True면 mp3로 변환 후 mp4 삭제
        both:       True면 mp4 유지 + mp3도 추가 생성

    Returns:
        True: 정상 완료 / False: 오류
    """
    from src.downloader.video_downloader import extract_video_url, download_video_with_browser, make_filename
    from src.converter.audio_converter import convert_to_mp3

    console.print()
    console.print(Panel(
        Text(lec.title, justify="center", style="bold cyan"),
        border_style="cyan",
        padding=(0, 4),
    ))
    console.print()

    download_dir = Config.get_download_dir()

    # 1. video URL 추출
    console.print("  [dim]영상 URL 추출 중...[/dim]")
    video_url = await extract_video_url(page, lec.full_url)
    if not video_url:
        console.print("  [bold red]오류:[/bold red] 영상 URL을 찾지 못했습니다.")
        return False

    # 2. 파일 경로 결정
    mp4_filename = make_filename(course.long_name, lec.title)
    mp4_path = Path(download_dir) / mp4_filename

    if audio_only:
        final_path = mp4_path.with_suffix(".mp3")
    elif both:
        final_path = mp4_path  # mp4 + mp3 둘 다 저장
    else:
        final_path = mp4_path
    console.print(f"  [dim]저장 경로: {final_path}[/dim]")
    console.print()

    # 3. mp4 다운로드 + Progress bar
    progress = Progress(
        SpinnerColumn(),
        TextColumn("  [bold]{task.description}"),
        BarColumn(bar_width=36),
        DownloadColumn(),
        TransferSpeedColumn(),
        console=console,
        expand=False,
    )
    task_id = progress.add_task(lec.title[:40], total=None)

    try:
        with Live(progress, console=console, refresh_per_second=8):
            def on_progress(downloaded: int, total: int):
                progress.update(task_id, completed=downloaded, total=total)

            await download_video_with_browser(page, video_url, mp4_path, on_progress=on_progress)
    except Exception as e:
        console.print(f"  [bold red]다운로드 실패:[/bold red] {e}")
        return False

    # 4. mp3 변환 (audio_only 또는 both)
    mp3_path: Path | None = None
    if audio_only or both:
        console.print()
        console.print("  [dim]mp3 변환 중...[/dim]")
        try:
            mp3_path = convert_to_mp3(mp4_path)
            if audio_only:
                mp4_path.unlink()  # 음성 전용: 원본 mp4 삭제
        except Exception as e:
            console.print(f"  [bold red]mp3 변환 실패:[/bold red] {e}")
            return False

        console.print()
        console.print(f"  [bold green]다운로드 완료![/bold green]")
        if both:
            console.print(f"  [dim]{mp4_path}[/dim]")
        console.print(f"  [dim]{mp3_path}[/dim]")
    else:
        console.print()
        console.print(f"  [bold green]다운로드 완료![/bold green]")
        console.print(f"  [dim]{mp4_path}[/dim]")

    # 5. STT 변환 (mp3가 있고 STT_ENABLED=true인 경우)
    if mp3_path and Config.STT_ENABLED == "true":
        console.print()
        console.print("  [dim]STT 변환 중... (시간이 걸릴 수 있습니다)[/dim]")
        try:
            from src.stt.transcriber import transcribe
            txt_path = transcribe(mp3_path, model_size=Config.WHISPER_MODEL or "base")
            console.print(f"  [bold green]STT 완료![/bold green]")
            console.print(f"  [dim]{txt_path}[/dim]")
        except Exception as e:
            console.print(f"  [bold red]STT 실패:[/bold red] {e}")

    return True
