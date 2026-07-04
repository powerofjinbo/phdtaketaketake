"""At-rest encryption for user-supplied API keys (Fernet keyed off JWT_SECRET)."""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from .config import JWT_SECRET

_fernet = Fernet(
    base64.urlsafe_b64encode(hashlib.sha256(JWT_SECRET.encode()).digest())
)


def encrypt(value: str) -> str:
    return _fernet.encrypt(value.encode()).decode()


def decrypt(token: str) -> str | None:
    try:
        return _fernet.decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        return None
