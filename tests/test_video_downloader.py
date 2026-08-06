"""video_downloader.py 순수 함수 단위 테스트."""

from pathlib import Path

from src.downloader.video_downloader import _sanitize_filename, make_filepath


def test_sanitize_filename_removes_forbidden_chars():
    """OS에서 사용 불가한 문자를 제거한다."""
    assert _sanitize_filename('a<b>c:d"e/f\\g|h?i*j') == "abcdefghij"


def test_sanitize_filename_blocks_path_traversal():
    """연속된 점(..)을 제거해 상위 디렉토리 순회를 방지한다."""
    assert ".." not in _sanitize_filename("../../etc/passwd")


def test_sanitize_filename_collapses_whitespace_and_trims():
    """중복 공백을 하나로 합치고 앞뒤 공백/점을 제거한다."""
    assert _sanitize_filename("  hello   world.  ") == "hello world"


def test_sanitize_filename_empty_falls_back():
    """빈 문자열이 되면 기본값 'lecture'를 반환한다."""
    assert _sanitize_filename("...") == "lecture"


def test_make_filepath_extracts_week_number():
    """week_label에서 'N주차'만 추출해 디렉토리로 사용한다."""
    path = make_filepath("자료구조", "3주차(총 15주 중)", "3강 트리")
    assert path == Path("자료구조") / "3주차" / "3강 트리.mp4"


def test_make_filepath_falls_back_when_no_week_number():
    """week_label에 'N주차' 패턴이 없으면 sanitize된 원문을 디렉토리로 쓴다."""
    path = make_filepath("자료구조", "특강", "3강 트리")
    assert path == Path("자료구조") / "특강" / "3강 트리.mp4"


def test_make_filepath_empty_week_label_falls_back_to_default_dir():
    """week_label이 빈 문자열이면 '기타' 디렉토리를 사용한다."""
    path = make_filepath("자료구조", "", "3강 트리")
    assert path == Path("자료구조") / "기타" / "3강 트리.mp4"
