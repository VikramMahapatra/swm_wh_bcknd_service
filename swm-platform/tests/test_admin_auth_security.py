from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from admin_api import api_support
from swm_auth import create_access_token


@pytest.fixture(autouse=True)
def _clear_security_cache() -> None:
    api_support._get_security_settings.cache_clear()
    yield
    api_support._get_security_settings.cache_clear()


def _request(headers: dict[str, str] | None = None) -> Request:
    raw_headers = []
    for k, v in (headers or {}).items():
        raw_headers.append((k.lower().encode("utf-8"), v.encode("utf-8")))
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": raw_headers,
            "query_string": b"",
            "client": ("127.0.0.1", 50000),
            "server": ("testserver", 80),
            "scheme": "http",
        }
    )


def _mock_settings(**overrides: object) -> SimpleNamespace:
    data = {
        "jwt_secret": "test-secret",
        "jwt_algorithm": "HS256",
        "auth_enforce_jwt": False,
        "auth_allow_legacy_role_header": True,
        "auth_legacy_default_role": "admin",
        "auth_api_keys_json": "[]",
    }
    data.update(overrides)
    return SimpleNamespace(**data)


@pytest.mark.asyncio
async def test_role_context_from_jwt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api_support, "get_settings", lambda: _mock_settings())

    token = create_access_token(
        subject="alice",
        secret="test-secret",
        algorithm="HS256",
        expires_minutes=30,
        extra_claims={"role": "viewer", "permissions": ["reports.read"]},
    )
    request = _request({"authorization": f"Bearer {token}"})

    ctx = await api_support.get_role_context(request)
    assert ctx.subject == "alice"
    assert ctx.role == "read_only"
    assert ctx.permissions == ["reports.read"]
    assert ctx.auth_type == "jwt"


@pytest.mark.asyncio
async def test_role_context_from_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    key_json = (
        '[{"key":"svc-key-1","subject":"svc-ingestion","role":"operator",'
        '"permissions":["ingestion.write"]}]'
    )
    monkeypatch.setattr(api_support, "get_settings", lambda: _mock_settings(auth_api_keys_json=key_json))

    ctx = await api_support.get_role_context(_request({"x-api-key": "svc-key-1"}))
    assert ctx.subject == "svc-ingestion"
    assert ctx.role == "operator"
    assert ctx.permissions == ["ingestion.write"]
    assert ctx.auth_type == "api_key"


@pytest.mark.asyncio
async def test_auth_required_when_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        api_support,
        "get_settings",
        lambda: _mock_settings(auth_enforce_jwt=True, auth_allow_legacy_role_header=False),
    )
    with pytest.raises(HTTPException) as exc:
        await api_support.get_role_context(_request())
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_require_roles_handles_legacy_aliases() -> None:
    checker = api_support.require_roles("viewer")
    ctx = api_support.RoleContext(
        subject="legacy-user",
        role="read_only",
        permissions=["fleet.read"],
        auth_type="legacy_header",
    )

    allowed = await checker(ctx)
    assert allowed.role == "read_only"
