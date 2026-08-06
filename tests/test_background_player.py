"""background_player.py 순수 함수 단위 테스트."""

from src.player.background_player import _parse_player_url


def test_parse_player_url_basic_fields():
    """content_id, duration, progress_url을 URL에서 추출한다."""
    url = "https://commons.ssu.ac.kr/em/123456?endat=605.5&TargetUrl=https%3A%2F%2Fexample.com%2Fprogress"
    info = _parse_player_url(url)
    assert info["content_id"] == "123456"
    assert info["duration"] == 605.5
    assert info["progress_url"] == "https://example.com/progress"


def test_parse_player_url_normalizes_negative_sentinel_duration():
    """duration 미확정 시 LMS가 보내는 음수 sentinel 값(-8888 등)을 0으로 정규화한다."""
    url = "https://commons.ssu.ac.kr/em/123456?endat=-8888&TargetUrl="
    info = _parse_player_url(url)
    assert info["duration"] == 0.0


def test_parse_player_url_missing_params_default_safely():
    """endat/TargetUrl이 없어도 예외 없이 기본값을 반환한다."""
    url = "https://commons.ssu.ac.kr/em/123456"
    info = _parse_player_url(url)
    assert info["duration"] == 0.0
    assert info["progress_url"] == ""
