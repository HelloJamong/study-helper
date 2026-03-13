"""crypto.py 단위 테스트."""

from unittest.mock import patch


def test_encrypt_decrypt_roundtrip(tmp_path):
    """암호화 후 복호화하면 원본과 동일해야 한다."""
    key_file = tmp_path / ".secret_key"
    with patch("src.crypto._KEY_PATH", key_file):
        from src.crypto import decrypt, encrypt, is_encrypted

        original = "test_password_123!@#"
        encrypted = encrypt(original)
        assert is_encrypted(encrypted)
        assert encrypted.startswith("enc:")
        assert decrypt(encrypted) == original


def test_decrypt_plaintext():
    """enc: 접두사 없는 평문은 그대로 반환해야 한다."""
    from src.crypto import decrypt

    assert decrypt("plain_value") == "plain_value"


def test_is_encrypted():
    """enc: 접두사 판별이 정확해야 한다."""
    from src.crypto import is_encrypted

    assert is_encrypted("enc:abc123") is True
    assert is_encrypted("plain") is False
    assert is_encrypted("") is False


def test_encrypt_empty_string(tmp_path):
    """빈 문자열도 암호화/복호화 가능해야 한다."""
    key_file = tmp_path / ".secret_key"
    with patch("src.crypto._KEY_PATH", key_file):
        from src.crypto import decrypt, encrypt

        encrypted = encrypt("")
        assert decrypt(encrypted) == ""


def test_different_keys_cannot_decrypt(tmp_path):
    """다른 키로는 복호화할 수 없어야 한다 (빈 문자열 반환)."""
    key_file_1 = tmp_path / "key1"
    key_file_2 = tmp_path / "key2"

    with patch("src.crypto._KEY_PATH", key_file_1):
        from src.crypto import encrypt

        encrypted = encrypt("secret")

    with patch("src.crypto._KEY_PATH", key_file_2):
        from src.crypto import decrypt

        assert decrypt(encrypted) == ""
