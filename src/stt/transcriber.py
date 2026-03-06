"""
Whisper STT 변환기.

mp3/mp4 파일을 Whisper에 직접 전달해 텍스트로 변환한다.
wav 중간 파일은 생성하지 않는다.
"""

import warnings
from pathlib import Path


def transcribe(audio_path: Path, model_size: str = "base") -> Path:
    """
    Whisper로 음성 파일을 텍스트로 변환한다.

    Args:
        audio_path: mp3 또는 mp4 파일 경로
        model_size: Whisper 모델 크기 (tiny/base/small/medium/large)

    Returns:
        생성된 .txt 파일 경로
    """
    try:
        import whisper
    except ImportError:
        raise RuntimeError(
            "whisper 패키지가 설치되어 있지 않습니다.\n"
            "설치: pip install openai-whisper"
        )

    model = whisper.load_model(model_size)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = model.transcribe(str(audio_path))

    txt_path = audio_path.with_suffix(".txt")
    txt_path.write_text(result["text"], encoding="utf-8")
    return txt_path
