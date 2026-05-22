from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from admin_api import api_support
from admin_api.main import app
from admin_api.routers import auth as auth_router
from swm_auth import decode_access_token


class _DummySession:
    def add(self, *_args, **_kwargs):
        return None

    async def flush(self):
        return None

    async def commit(self):
        return None


async def _override_db_session():
    yield _DummySession()


@pytest.fixture(autouse=True)
def _clear_auth_caches() -> None:
    api_support._get_security_settings.cache_clear()
    auth_router._get_bootstrap_users.cache_clear()
    app.dependency_overrides.clear()
    app.dependency_overrides[auth_router.get_db_session] = _override_db_session
    yield
    api_support._get_security_settings.cache_clear()
    auth_router._get_bootstrap_users.cache_clear()
    app.dependency_overrides.clear()


def _mock_settings(**overrides: object) -> SimpleNamespace:
    data = {
        "jwt_secret": "test-secret",
        "jwt_algorithm": "HS256",
        "jwt_expiry_minutes": 30,
        "auth_users_json": "[]",
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _fake_user(username: str = "admin", roles: list[str] | None = None, permissions: list[str] | None = None):
    return SimpleNamespace(
        username=username,
        active=True,
        deleted_at=None,
        password_hash="pbkdf2_sha256$120000$c2FsdA$dG9rZW4",
        token_version=1,
        last_login_at=None,
        last_login_ip=None,
        roles=roles or [SimpleNamespace(role_key="admin", active=True, deleted_at=None, permissions=[SimpleNamespace(permission_key="*", active=True, deleted_at=None)])],
        permissions=permissions or ["*"],
    )


def test_login_success_issues_jwt(monkeypatch) -> None:
    monkeypatch.setattr(auth_router, "get_settings", lambda: _mock_settings())
    async def _ensure_bootstrap_users(_session):
        return None

    async def _load_user(_session, _username):
        return _fake_user()

    monkeypatch.setattr(auth_router, "_ensure_bootstrap_users", _ensure_bootstrap_users)
    monkeypatch.setattr(auth_router, "_load_user", _load_user)

    async def _issue_refresh_token(_session, *, user, request=None, family_id=None, expires_in_minutes=0):
        return "refresh-token-1", SimpleNamespace(id="refresh-id")

    monkeypatch.setattr(auth_router, "_issue_refresh_token", _issue_refresh_token)

    client = TestClient(app)
    resp = client.post("/v1/auth/login", json={"username": "admin", "password": "admin123"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["subject"] == "admin"
    assert body["roles"] == ["admin"]
    assert body["permissions"] == ["*"]
    assert body["refresh_token"] == "refresh-token-1"

    claims = decode_access_token(body["access_token"], "test-secret", "HS256")
    assert claims["sub"] == "admin"
    assert claims["role"] == "admin"
    assert claims["roles"] == ["admin"]


def test_me_returns_current_principal(monkeypatch) -> None:
    monkeypatch.setattr(api_support, "get_settings", lambda: _mock_settings())

    token = auth_router.create_access_token(
        subject="alice",
        secret="test-secret",
        algorithm="HS256",
        expires_minutes=30,
        extra_claims={"role": "operator", "roles": ["operator", "viewer"], "permissions": ["fleet.read", "operations.execute"]},
    )

    client = TestClient(app)
    resp = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["active"] is True
    assert body["subject"] == "alice"
    assert body["role"] == "operator"
    assert body["roles"] == ["operator", "viewer"]
    assert body["permissions"] == ["fleet.read", "operations.execute"]


def test_login_rejects_invalid_credentials(monkeypatch) -> None:
    monkeypatch.setattr(auth_router, "get_settings", lambda: _mock_settings())
    async def _ensure_bootstrap_users(_session):
        return None

    async def _load_user(_session, _username):
        return _fake_user()

    monkeypatch.setattr(auth_router, "_ensure_bootstrap_users", _ensure_bootstrap_users)
    monkeypatch.setattr(auth_router, "_load_user", _load_user)

    async def _issue_refresh_token(_session, *, user, request=None, family_id=None, expires_in_minutes=0):
        return "refresh-token-1", SimpleNamespace(id="refresh-id")

    monkeypatch.setattr(auth_router, "_issue_refresh_token", _issue_refresh_token)

    client = TestClient(app)
    resp = client.post("/v1/auth/login", json={"username": "admin", "password": "wrong"})

    assert resp.status_code == 401
    assert resp.json()["detail"] == "invalid credentials"


def test_login_bootstraps_when_configured(monkeypatch) -> None:
    users = '[{"username":"admin","password":"admin123","role":"admin","subject":"alice","permissions":["*"]}]'
    monkeypatch.setattr(auth_router, "get_settings", lambda: _mock_settings(auth_users_json=users))

    called = {"seed": 0}

    async def _seed(_session):
        called["seed"] += 1

    monkeypatch.setattr(auth_router, "_ensure_bootstrap_users", _seed)
    async def _load_user(_session, _username):
        return _fake_user(username="admin")

    monkeypatch.setattr(auth_router, "_load_user", _load_user)

    async def _issue_refresh_token(_session, *, user, request=None, family_id=None, expires_in_minutes=0):
        return "refresh-token-1", SimpleNamespace(id="refresh-id")

    monkeypatch.setattr(auth_router, "_issue_refresh_token", _issue_refresh_token)

    client = TestClient(app)
    resp = client.post("/v1/auth/login", json={"username": "admin", "password": "admin123"})

    assert resp.status_code == 200
    assert called["seed"] == 1
