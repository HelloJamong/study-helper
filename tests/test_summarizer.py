"""summarizer.py 단위 테스트."""

from unittest.mock import patch

import pytest


def test_summarize_empty_text(tmp_path):
    """빈 텍스트 파일은 ValueError를 발생시켜야 한다."""
    txt = tmp_path / "empty.txt"
    txt.write_text("", encoding="utf-8")
    from src.summarizer.summarizer import summarize

    with pytest.raises(ValueError, match="비어 있습니다"):
        summarize(txt, agent="gemini", api_key="key", model="model")


def test_summarize_output_path(tmp_path):
    """출력 파일명이 _summarized.txt로 끝나야 한다."""
    txt = tmp_path / "lecture.txt"
    txt.write_text("강의 내용입니다.", encoding="utf-8")
    with patch("src.summarizer.summarizer._summarize_gemini", return_value="요약 결과"):
        from src.summarizer.summarizer import summarize

        result = summarize(txt, agent="gemini", api_key="key", model="model")
        assert result.name == "lecture_summarized.txt"
        assert result.read_text(encoding="utf-8") == "요약 결과"


def test_summarize_unsupported_agent(tmp_path):
    """지원하지 않는 에이전트는 ValueError."""
    txt = tmp_path / "test.txt"
    txt.write_text("내용", encoding="utf-8")
    from src.summarizer.summarizer import summarize

    with pytest.raises(ValueError, match="지원하지 않는"):
        summarize(txt, agent="claude", api_key="key", model="model")


def test_gemini_model_ids():
    """모델 ID 목록이 비어있지 않아야 한다."""
    from src.summarizer.summarizer import GEMINI_DEFAULT_MODEL, GEMINI_MODEL_IDS

    assert len(GEMINI_MODEL_IDS) > 0
    assert GEMINI_DEFAULT_MODEL in GEMINI_MODEL_IDS


def test_summarize_openai_path(tmp_path):
    """OpenAI 에이전트 경로도 동작해야 한다."""
    txt = tmp_path / "lecture.txt"
    txt.write_text("강의 내용입니다.", encoding="utf-8")
    with patch("src.summarizer.summarizer._summarize_openai_compatible", return_value="OpenAI 요약") as mock_fn:
        from src.summarizer.summarizer import summarize

        result = summarize(txt, agent="openai", api_key="key", model="gpt-4")
        assert result.name == "lecture_summarized.txt"
        assert result.read_text(encoding="utf-8") == "OpenAI 요약"
        # base_url 없이 호출돼야 한다 (OpenAI 정식 엔드포인트 사용)
        assert mock_fn.call_args.args[:2] == ("key", "gpt-4")
        assert "base_url" not in mock_fn.call_args.kwargs


def test_summarize_openrouter_path(tmp_path):
    """OpenRouter 에이전트는 OpenAI 호환 경로를 OpenRouter base_url로 호출해야 한다."""
    txt = tmp_path / "lecture.txt"
    txt.write_text("강의 내용입니다.", encoding="utf-8")
    with patch("src.summarizer.summarizer._summarize_openai_compatible", return_value="OpenRouter 요약") as mock_fn:
        from src.summarizer.summarizer import OPENROUTER_BASE_URL, summarize

        result = summarize(txt, agent="openrouter", api_key="key", model="openai/gpt-4o-mini")
        assert result.read_text(encoding="utf-8") == "OpenRouter 요약"
        assert mock_fn.call_args.kwargs["base_url"] == OPENROUTER_BASE_URL


def test_ai_default_models_cover_all_agents():
    """AI_DEFAULT_MODELS가 gemini/openai/openrouter 모두를 커버해야 한다."""
    from src.summarizer.summarizer import AI_DEFAULT_MODELS

    assert set(AI_DEFAULT_MODELS) == {"gemini", "openai", "openrouter"}
    assert all(AI_DEFAULT_MODELS.values())
