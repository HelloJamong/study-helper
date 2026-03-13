"""config.py 단위 테스트."""

from src.config import _default_download_dir, _read_version


def test_read_version():
    """CHANGELOG.md에서 버전을 정상적으로 파싱한다."""
    version = _read_version()
    assert version != "unknown"
    parts = version.split("-")[0].split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)


def test_default_download_dir():
    """OS별 기본 다운로드 경로가 빈 문자열이 아니어야 한다."""
    path = _default_download_dir()
    assert path
    assert isinstance(path, str)
