from datetime import UTC, datetime, timedelta
from typing import Any

import jwt


def create_access_token(
    *,
    subject: str,
    secret: str,
    algorithm: str,
    expires_minutes: int,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(tz=UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_minutes)).timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload=payload, key=secret, algorithm=algorithm)


def decode_access_token(token: str, secret: str, algorithm: str) -> dict[str, Any]:
    return jwt.decode(jwt=token, key=secret, algorithms=[algorithm])
