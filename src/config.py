import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.crypto import decrypt, encrypt, is_encrypted

# .env 파일 로드 (없으면 환경변수만 사용)
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(_env_path)


def _load_credential(env_key: str) -> str:
    """
    환경변수를 읽어 복호화한다.
    enc: 접두사가 있는데 복호화 실패 시(키 불일치) .env의 해당 키를 비워 재입력을 유도한다.
    """
    raw = os.getenv(env_key, "")
    if not raw:
        return ""
    if is_encrypted(raw):
        result = decrypt(raw)
        if not result:
            # 복호화 실패 → .env에서 해당 키 초기화
            _clear_env_key(env_key)
        return result
    return raw


def _clear_env_key(env_key: str) -> None:
    """복호화 실패한 키를 .env에서 비운다."""
    try:
        lines = _env_path.read_text(encoding="utf-8").splitlines(keepends=True)
        new_lines = []
        for line in lines:
            stripped = line.strip()
            if "=" in stripped and not stripped.startswith("#"):
                key = stripped.split("=", 1)[0].strip()
                if key == env_key:
                    new_lines.append(f"{key}=\n")
                    continue
            new_lines.append(line)
        _env_path.write_text("".join(new_lines), encoding="utf-8")
    except Exception:
        pass


def _default_download_dir() -> str:
    """OS별 기본 다운로드 경로를 반환한다."""
    if sys.platform == "win32":
        return str(Path.home() / "Downloads")
    # Docker 컨테이너 환경: /data 볼륨이 마운트된 경우 사용
    if Path("/data").exists() and str(Path.home()) == "/root":
        return "/data/downloads"
    # macOS / 일반 Linux
    return str(Path.home() / "Downloads")


def _read_version() -> str:
    """CHANGELOG.md의 첫 번째 ## [vX.Y.Z] 항목에서 버전을 읽어온다."""
    import re

    changelog = Path(__file__).parent.parent / "CHANGELOG.md"
    try:
        for line in changelog.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^## \[v(.+?)\]", line)
            if m:
                return m.group(1)
    except Exception:
        pass
    return "unknown"


APP_VERSION = _read_version()


class Config:
    LMS_USER_ID: str = _load_credential("LMS_USER_ID")
    LMS_PASSWORD: str = _load_credential("LMS_PASSWORD")
    GOOGLE_API_KEY: str = _load_credential("GOOGLE_API_KEY")
    OPENAI_API_KEY: str = _load_credential("OPENAI_API_KEY")
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")
    # STT 언어: ko, en, 빈 문자열(자동 감지)
    STT_LANGUAGE: str = os.getenv("STT_LANGUAGE", "ko")
    DOWNLOAD_DIR: str = os.getenv("DOWNLOAD_DIR", "")
    # 다운로드 규칙: video / audio / both
    DOWNLOAD_RULE: str = os.getenv("DOWNLOAD_RULE", "")
    # STT 사용 여부: true / false
    STT_ENABLED: str = os.getenv("STT_ENABLED", "")
    # AI 요약 사용 여부: true / false
    AI_ENABLED: str = os.getenv("AI_ENABLED", "")
    # AI 에이전트 종류: gemini / openai
    AI_AGENT: str = os.getenv("AI_AGENT", "")
    # Gemini 모델 ID
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "")
    # 요약 프롬프트 추가 지시사항
    SUMMARY_PROMPT_EXTRA: str = os.getenv("SUMMARY_PROMPT_EXTRA", "")
    # 텔레그램 봇 연동
    TELEGRAM_ENABLED: str = os.getenv("TELEGRAM_ENABLED", "")
    TELEGRAM_BOT_TOKEN: str = _load_credential("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
    # 텔레그램 전송 후 파일 자동 삭제
    TELEGRAM_AUTO_DELETE: str = os.getenv("TELEGRAM_AUTO_DELETE", "")

    @classmethod
    def has_credentials(cls) -> bool:
        return bool(cls.LMS_USER_ID and cls.LMS_PASSWORD)

    @classmethod
    def has_settings(cls) -> bool:
        """최초 설정이 완료됐는지 확인 (다운로드 규칙 기준)."""
        return bool(cls.DOWNLOAD_RULE)

    @classmethod
    def get_download_dir(cls) -> str:
        """저장된 경로가 없으면 OS 기본 다운로드 폴더를 반환한다."""
        return cls.DOWNLOAD_DIR or _default_download_dir()

    @classmethod
    def save_settings(
        cls,
        download_dir: str,
        download_rule: str,
        stt_enabled: bool,
        ai_enabled: bool,
        ai_agent: str,
        api_key: str,
        gemini_model: str = "",
        summary_prompt_extra: str = "",
    ) -> None:
        """설정 항목을 .env 파일에 저장한다."""
        cls.DOWNLOAD_DIR = download_dir
        cls.DOWNLOAD_RULE = download_rule
        cls.STT_ENABLED = "true" if stt_enabled else "false"
        cls.AI_ENABLED = "true" if ai_enabled else "false"
        cls.AI_AGENT = ai_agent
        cls.SUMMARY_PROMPT_EXTRA = summary_prompt_extra
        if gemini_model:
            cls.GEMINI_MODEL = gemini_model
        # API 키는 선택한 에이전트에 맞게 저장
        if ai_enabled and ai_agent == "gemini":
            cls.GOOGLE_API_KEY = api_key
        elif ai_enabled and ai_agent == "openai":
            cls.OPENAI_API_KEY = api_key

        to_save: dict = {
            "DOWNLOAD_DIR": download_dir,
            "DOWNLOAD_RULE": download_rule,
            "STT_ENABLED": cls.STT_ENABLED,
            "AI_ENABLED": cls.AI_ENABLED,
            "AI_AGENT": ai_agent,
            "SUMMARY_PROMPT_EXTRA": summary_prompt_extra,
        }
        if gemini_model:
            to_save["GEMINI_MODEL"] = gemini_model
        if ai_enabled and ai_agent == "gemini":
            to_save["GOOGLE_API_KEY"] = encrypt(api_key) if api_key else ""
        elif ai_enabled and ai_agent == "openai":
            to_save["OPENAI_API_KEY"] = encrypt(api_key) if api_key else ""
        cls._save_env(to_save)

    @classmethod
    def save_telegram(cls, enabled: bool, bot_token: str, chat_id: str, auto_delete: bool) -> None:
        """텔레그램 설정을 .env 파일에 저장한다."""
        cls.TELEGRAM_ENABLED = "true" if enabled else "false"
        cls.TELEGRAM_BOT_TOKEN = bot_token
        cls.TELEGRAM_CHAT_ID = chat_id
        cls.TELEGRAM_AUTO_DELETE = "true" if auto_delete else "false"
        cls._save_env(
            {
                "TELEGRAM_ENABLED": cls.TELEGRAM_ENABLED,
                "TELEGRAM_BOT_TOKEN": encrypt(bot_token) if bot_token else "",
                "TELEGRAM_CHAT_ID": chat_id,
                "TELEGRAM_AUTO_DELETE": cls.TELEGRAM_AUTO_DELETE,
            }
        )

    @classmethod
    def save_credentials(cls, user_id: str, password: str) -> None:
        """계정 정보를 암호화해서 .env 파일에 저장"""
        cls.LMS_USER_ID = user_id
        cls.LMS_PASSWORD = password
        cls._save_env(
            {
                "LMS_USER_ID": encrypt(user_id),
                "LMS_PASSWORD": encrypt(password),
            }
        )

    @classmethod
    def _save_env(cls, keys_to_update: dict) -> None:
        """지정한 키/값을 .env 파일에 저장(덮어쓰기)한다."""
        env_path = Path(__file__).parent.parent / ".env"
        lines = []

        if env_path.exists():
            with open(env_path, encoding="utf-8") as f:
                lines = f.readlines()

        updated_keys = set()
        new_lines = []

        for line in lines:
            stripped = line.strip()
            if "=" in stripped and not stripped.startswith("#"):
                key = stripped.split("=", 1)[0].strip()
                if key in keys_to_update:
                    new_lines.append(f"{key}={keys_to_update[key]}\n")
                    updated_keys.add(key)
                    continue
            new_lines.append(line)

        for key, value in keys_to_update.items():
            if key not in updated_keys:
                new_lines.append(f"{key}={value}\n")

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
