from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

console = Console()


def show_login_screen() -> tuple[str, str]:
    """
    TUI 로그인 화면을 표시하고 (학번, 비밀번호)를 반환한다.
    비밀번호는 입력 시 마스킹 처리된다.
    """
    console.clear()
    console.print(
        Panel(
            Text("숭실대학교 LMS Study Helper", justify="center", style="bold cyan"),
            border_style="cyan",
            padding=(1, 4),
        )
    )
    console.print()
    console.print("  LMS 계정으로 로그인하세요.", style="dim")
    console.print()

    user_id = Prompt.ask("  [bold]학번[/bold]")
    password = Prompt.ask("  [bold]비밀번호[/bold]", password=True)

    console.print()
    return user_id.strip(), password.strip()


def show_login_progress():
    """로그인 진행 중 메시지 표시"""
    console.print("  [yellow]로그인 중...[/yellow]")


def show_login_error(message: str = "학번 또는 비밀번호가 올바르지 않습니다."):
    """로그인 실패 메시지 표시"""
    console.print()
    console.print(f"  [bold red]오류:[/bold red] {message}")
    console.print()


def show_login_success():
    """로그인 성공 메시지 표시"""
    console.print("  [bold green]로그인 성공[/bold green]")
    console.print()
