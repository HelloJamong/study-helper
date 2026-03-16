"""
민감 정보 암호화/복호화 유틸리티.

최초 실행 시 머신 고유 Fernet 키를 생성해서 .secret_key 파일에 저장한다.
같은 기기에서만 복호화 가능하므로 .env 파일이 유출돼도 값을 읽을 수 없다.

암호화된 값은 "enc:" 접두사로 구별한다.
"""

from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

_PREFIX = "enc:"
_KEY_PATH = Path(__file__).parent.parent / ".secret_key"


def _resolve_key_path() -> Path:
    """실제 키 파일 경로를 반환한다.

    Docker 바인드 마운트 시 호스트에 파일이 없으면 .secret_key가 디렉토리로
    생성되므로, 그 경우 디렉토리 내부의 key 파일을 사용한다.
    """
    if _KEY_PATH.is_dir():
        return _KEY_PATH / "key"
    return _KEY_PATH


def _load_or_create_key() -> bytes:
    """
    .secret_key 파일에서 키를 읽거나, 없으면 새로 생성해서 저장한다.
    .secret_key는 .gitignore에 등록되어야 한다.

    Docker 볼륨 마운트 시 .secret_key가 디렉토리로 생성될 수 있으므로
    디렉토리인 경우 내부의 key 파일을 사용한다.
    """
    key_file = _KEY_PATH / "key" if _KEY_PATH.is_dir() else _KEY_PATH

    if key_file.exists() and key_file.is_file():
        return key_file.read_bytes().strip()

    key = Fernet.generate_key()
    if _KEY_PATH.is_dir():
        key_file = _KEY_PATH / "key"
    else:
        key_file = _KEY_PATH
    key_file.write_bytes(key)
    try:
        key_file.chmod(0o600)
    except OSError:
        pass  # Windows에서는 chmod가 제한적
    return key


def _fernet() -> Fernet:
    return Fernet(_load_or_create_key())


def encrypt(plaintext: str) -> str:
    """평문을 암호화하고 'enc:<base64>' 형태의 문자열을 반환한다."""
    token = _fernet().encrypt(plaintext.encode())
    return _PREFIX + token.decode()


def decrypt(value: str) -> str:
    """
    'enc:<base64>' 형태의 값을 복호화한다.
    접두사가 없으면 평문 그대로 반환한다 (하위 호환).
    복호화 실패 시 빈 문자열 반환.
    """
    if not value.startswith(_PREFIX):
        return value
    token = value[len(_PREFIX) :]
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, Exception):
        return ""


def is_encrypted(value: str) -> bool:
    return value.startswith(_PREFIX)
