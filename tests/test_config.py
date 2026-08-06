"""config.py 단위 테스트."""

from src.config import Config, _default_download_dir, _read_version


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


def test_get_ai_credentials_none_when_disabled(monkeypatch):
    """AI_ENABLED가 아니면 None을 반환한다."""
    monkeypatch.setattr(Config, "AI_ENABLED", "false")
    assert Config.get_ai_credentials() is None


def test_get_ai_credentials_none_when_key_missing(monkeypatch):
    """선택된 에이전트의 API 키가 비어 있으면 None을 반환한다."""
    monkeypatch.setattr(Config, "AI_ENABLED", "true")
    monkeypatch.setattr(Config, "AI_AGENT", "openai")
    monkeypatch.setattr(Config, "OPENAI_API_KEY", "")
    assert Config.get_ai_credentials() is None


def test_get_ai_credentials_openai_uses_openai_key_and_model(monkeypatch):
    """OpenAI 선택 시 Gemini 값이 아닌 OpenAI 전용 키/모델을 반환해야 한다.

    회귀 방지: 과거 ui 레이어의 삼항연산이 OpenAI를 선택해도 모델을 항상
    Gemini 기본 모델로 강제해 OpenAI 요약이 실패하던 버그가 있었다.
    """
    monkeypatch.setattr(Config, "AI_ENABLED", "true")
    monkeypatch.setattr(Config, "AI_AGENT", "openai")
    monkeypatch.setattr(Config, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(Config, "OPENAI_MODEL", "gpt-4o-mini")
    monkeypatch.setattr(Config, "GOOGLE_API_KEY", "should-not-be-used")
    assert Config.get_ai_credentials() == ("openai", "sk-test", "gpt-4o-mini")


def test_get_ai_credentials_openrouter_falls_back_to_default_model(monkeypatch):
    """OpenRouter 모델을 설정하지 않았으면 기본 모델로 폴백한다."""
    monkeypatch.setattr(Config, "AI_ENABLED", "true")
    monkeypatch.setattr(Config, "AI_AGENT", "openrouter")
    monkeypatch.setattr(Config, "OPENROUTER_API_KEY", "key")
    monkeypatch.setattr(Config, "OPENROUTER_MODEL", "")
    agent, api_key, model = Config.get_ai_credentials()
    assert agent == "openrouter"
    assert api_key == "key"
    assert model
