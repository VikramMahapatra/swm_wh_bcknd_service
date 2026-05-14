"""Tests for swm_auth.webhook middleware."""
from __future__ import annotations

import hashlib
import hmac
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from swm_auth.webhook import WebhookAuthConfig, WebhookAuthMiddleware


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_app(config: WebhookAuthConfig, redis_client: object | None = None) -> FastAPI:
    app = FastAPI()
    app.add_middleware(WebhookAuthMiddleware, config=config, redis_client=redis_client)

    @app.post("/hook")
    async def hook() -> dict[str, str]:
        return {"ok": "true"}

    return app


def _hmac_sig(body: bytes, secret: bytes) -> str:
    return "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# Secret header
# ---------------------------------------------------------------------------

class TestSecretHeader:
    def test_valid_secret_passes(self) -> None:
        client = TestClient(_make_app(WebhookAuthConfig(secret="tok123")))
        resp = client.post("/hook", headers={"X-Webhook-Secret": "tok123"})
        assert resp.status_code == 200

    def test_missing_secret_rejects(self) -> None:
        client = TestClient(_make_app(WebhookAuthConfig(secret="tok123")))
        resp = client.post("/hook")
        assert resp.status_code == 401
        assert "missing" in resp.json()["error"].lower()

    def test_wrong_secret_rejects(self) -> None:
        client = TestClient(_make_app(WebhookAuthConfig(secret="tok123")))
        resp = client.post("/hook", headers={"X-Webhook-Secret": "wrong"})
        assert resp.status_code == 401
        assert "invalid" in resp.json()["error"].lower()

    def test_custom_header_name(self) -> None:
        cfg = WebhookAuthConfig(secret="abc", secret_header="X-My-Token")
        client = TestClient(_make_app(cfg))
        resp = client.post("/hook", headers={"X-My-Token": "abc"})
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# HMAC signature
# ---------------------------------------------------------------------------

class TestHmacSignature:
    _KEY = b"webhook-key"
    _BODY = b'{"event":"ping"}'

    def test_valid_signature_passes(self) -> None:
        sig = _hmac_sig(self._BODY, self._KEY)
        cfg = WebhookAuthConfig(hmac_secret=self._KEY)
        client = TestClient(_make_app(cfg))
        resp = client.post("/hook", content=self._BODY, headers={"X-Webhook-Signature": sig})
        assert resp.status_code == 200

    def test_missing_signature_rejects(self) -> None:
        cfg = WebhookAuthConfig(hmac_secret=self._KEY)
        client = TestClient(_make_app(cfg))
        resp = client.post("/hook", content=self._BODY)
        assert resp.status_code == 401
        assert "missing" in resp.json()["error"].lower()

    def test_invalid_signature_rejects(self) -> None:
        cfg = WebhookAuthConfig(hmac_secret=self._KEY)
        client = TestClient(_make_app(cfg))
        resp = client.post(
            "/hook",
            content=self._BODY,
            headers={"X-Webhook-Signature": "sha256=badhash"},
        )
        assert resp.status_code == 401

    def test_signature_without_prefix_also_accepted(self) -> None:
        raw_sig = hmac.new(self._KEY, self._BODY, hashlib.sha256).hexdigest()
        cfg = WebhookAuthConfig(hmac_secret=self._KEY)
        client = TestClient(_make_app(cfg))
        resp = client.post(
            "/hook",
            content=self._BODY,
            headers={"X-Webhook-Signature": raw_sig},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# IP whitelist
# ---------------------------------------------------------------------------

class TestIpWhitelist:
    def test_allowed_ip_passes(self) -> None:
        cfg = WebhookAuthConfig(allowed_ips=["127.0.0.1"])
        client = TestClient(_make_app(cfg))
        # TestClient sends from 127.0.0.1 by default
        resp = client.post("/hook")
        assert resp.status_code == 200

    def test_cidr_block_passes(self) -> None:
        cfg = WebhookAuthConfig(allowed_ips=["127.0.0.0/8"])
        client = TestClient(_make_app(cfg))
        resp = client.post("/hook")
        assert resp.status_code == 200

    def test_blocked_ip_rejects(self) -> None:
        cfg = WebhookAuthConfig(allowed_ips=["10.0.0.1"])
        client = TestClient(_make_app(cfg))
        resp = client.post("/hook")
        assert resp.status_code == 401
        assert "not permitted" in resp.json()["error"].lower()

    def test_x_forwarded_for_used(self) -> None:
        cfg = WebhookAuthConfig(allowed_ips=["203.0.113.5"])
        client = TestClient(_make_app(cfg))
        resp = client.post("/hook", headers={"X-Forwarded-For": "203.0.113.5"})
        assert resp.status_code == 200

    def test_x_forwarded_for_blocked(self) -> None:
        cfg = WebhookAuthConfig(allowed_ips=["203.0.113.5"])
        client = TestClient(_make_app(cfg))
        resp = client.post("/hook", headers={"X-Forwarded-For": "1.2.3.4"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Nonce replay prevention
# ---------------------------------------------------------------------------

class TestNonceReplay:
    def _mock_redis(self, *, nx_return: bool = True) -> MagicMock:
        r = MagicMock()
        r.set = AsyncMock(return_value=nx_return)
        return r

    def test_fresh_nonce_passes(self) -> None:
        redis = self._mock_redis(nx_return=True)
        cfg = WebhookAuthConfig(nonce_ttl_seconds=300)
        client = TestClient(_make_app(cfg, redis_client=redis))
        resp = client.post("/hook", headers={"X-Webhook-Nonce": "abc123"})
        assert resp.status_code == 200

    def test_replayed_nonce_rejects(self) -> None:
        redis = self._mock_redis(nx_return=False)
        cfg = WebhookAuthConfig(nonce_ttl_seconds=300)
        client = TestClient(_make_app(cfg, redis_client=redis))
        resp = client.post("/hook", headers={"X-Webhook-Nonce": "abc123"})
        assert resp.status_code == 401
        assert "already used" in resp.json()["error"].lower()

    def test_missing_nonce_rejects(self) -> None:
        redis = self._mock_redis()
        cfg = WebhookAuthConfig(nonce_ttl_seconds=300)
        client = TestClient(_make_app(cfg, redis_client=redis))
        resp = client.post("/hook")
        assert resp.status_code == 401
        assert "missing" in resp.json()["error"].lower()

    def test_nonce_skipped_without_redis(self) -> None:
        cfg = WebhookAuthConfig(nonce_ttl_seconds=300)
        client = TestClient(_make_app(cfg, redis_client=None))
        resp = client.post("/hook", headers={"X-Webhook-Nonce": "abc123"})
        # No redis → skip nonce check, allow through
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

class TestAuditLog:
    def test_audit_allow_emitted(self, capsys: pytest.CaptureFixture[str]) -> None:
        client = TestClient(_make_app(WebhookAuthConfig(audit_enabled=True)))
        client.post("/hook")
        captured = capsys.readouterr()
        assert "webhook_auth.audit" in captured.out

    def test_audit_disabled_emits_nothing(self, capsys: pytest.CaptureFixture[str]) -> None:
        client = TestClient(_make_app(WebhookAuthConfig(audit_enabled=False)))
        client.post("/hook")
        captured = capsys.readouterr()
        assert "webhook_auth.audit" not in captured.out


# ---------------------------------------------------------------------------
# Combined checks — all enabled
# ---------------------------------------------------------------------------

class TestCombinedChecks:
    _KEY = b"combined-key"

    def test_all_checks_pass(self) -> None:
        body = b'{"x":1}'
        redis = MagicMock()
        redis.set = AsyncMock(return_value=True)
        cfg = WebhookAuthConfig(
            secret="s3cr3t",
            hmac_secret=self._KEY,
            allowed_ips=["127.0.0.0/8"],
            nonce_ttl_seconds=60,
        )
        client = TestClient(_make_app(cfg, redis_client=redis))
        resp = client.post(
            "/hook",
            content=body,
            headers={
                "X-Webhook-Secret": "s3cr3t",
                "X-Webhook-Signature": _hmac_sig(body, self._KEY),
                "X-Webhook-Nonce": "unique-nonce-xyz",
            },
        )
        assert resp.status_code == 200

    def test_first_failing_check_short_circuits(self) -> None:
        """Secret fails → signature not attempted (body is moot)."""
        cfg = WebhookAuthConfig(secret="right", hmac_secret=self._KEY)
        client = TestClient(_make_app(cfg))
        resp = client.post(
            "/hook",
            headers={
                "X-Webhook-Secret": "wrong",
                "X-Webhook-Signature": "sha256=whatever",
            },
        )
        assert resp.status_code == 401
        assert "invalid" in resp.json()["error"].lower()
