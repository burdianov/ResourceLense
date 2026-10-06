from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pwdlib import PasswordHash


password_hash = PasswordHash.recommended()

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    return password_hash.verify(
        plain_password,
        hashed_password,
    )


def create_access_token(
    subject: str | int,
    secret_key: str,
    expires_minutes: int,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)

    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
    }

    if additional_claims:
        payload.update(additional_claims)

    return jwt.encode(
        payload,
        secret_key,
        algorithm=ALGORITHM,
    )


def decode_access_token(
    token: str,
    secret_key: str,
) -> dict[str, Any]:
    return jwt.decode(
        token,
        secret_key,
        algorithms=[ALGORITHM],
    )
