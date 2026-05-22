"""
swm_auth.webhook
================
Webhook authentication middleware for FastAPI/Starlette.

Layers (all optional but independently configurable):

1. **Secret header** — validates a pre-shared key sent in a request header
   (default: ``X-Webhook-Secret``).
2. **HMAC-SHA256 signature** — verifies an HMAC-SHA256 hex-digest of the raw
   request body sent in a configurable header
   (default: ``X-Webhook-Signature``). The value may carry a ``sha256=``
   prefix as GitHub-style webhooks do.
3. **IP whitelist** — rejects requests whose ``X-Forwarded-For`` / client IP
   does not appear in the configured allow-list. Supports individual IPv4/IPv6
   addresses and CIDR blocks.
4. **Nonce replay prevention** — validates a nonce sent in a header
   (default: ``X-Webhook-Nonce``) and records it in Redis so the same nonce
   can never be reused within ``nonce_ttl_seconds``.
5. **Audit log** — emits one structured log event per request that contains
   the outcome, source IP, vendor id (from configurable header), and which
   checks ran.

Usage::

    from fastapi import FastAPI
    from swm_auth.webhook import WebhookAuthConfig, WebhookAuthMiddleware

    app = FastAPI()
    app.add_middleware(
        WebhookAuthMiddleware,
        config=WebhookAuthConfig(
            secret="supersecret",
            hmac_secret=b"hmac-key",
            allowed_ips=["10.0.0.0/8"],
        ),
        redis_client=redis_client,  # optional; required for nonce checks
    )
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from swm_common.logger import get_logger

_logger = get_logger("swm.webhook_auth")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_DEFAULT_SECRET_HEADER = "X-Webhook-Secret"
_DEFAULT_SIGNATURE_HEADER = "X-Webhook-Signature"
_DEFAULT_NONCE_HEADER = "X-Webhook-Nonce"
_DEFAULT_VENDOR_HEADER = "X-Vendor-Id"
_NONCE_REDIS_PREFIX = "swm:wh:nonce:"


@dataclass(frozen=True)
class WebhookAuthConfig:
    """Configures which auth checks the middleware enforces.

    All checks default to *disabled*.  Enable each check by supplying the
    relevant field.

    Args:
        secret: Plain-text pre-shared secret that the caller must send in
            ``secret_header``.  ``None`` disables the check.
        secret_header: Header name carrying the secret
            (default ``X-Webhook-Secret``).
        hmac_secret: Raw bytes key used to verify the HMAC-SHA256 signature.
            ``None`` disables the check.
        signature_header: Header carrying the hex-digest
            (default ``X-Webhook-Signature``).  Accepts optional ``sha256=``
            prefix.
        allowed_ips: Non-empty list of allowed IPv4/IPv6 addresses or CIDR
            blocks.  ``None`` / empty list disables IP check.
        nonce_ttl_seconds: Seconds a nonce is remembered in Redis.  ``0``
            disables nonce replay prevention.
        nonce_header: Header carrying the nonce (default
            ``X-Webhook-Nonce``).
        vendor_header: Header carrying an opaque vendor id written into audit
            logs (default ``X-Vendor-Id``).
        audit_enabled: Whether to emit structured audit log events (default
            ``True``).
    """

    secret: str | None = None
    secret_header: str = _DEFAULT_SECRET_HEADER

    hmac_secret: bytes | None = None
    signature_header: str = _DEFAULT_SIGNATURE_HEADER

    allowed_ips: list[str] = field(default_factory=list)

    nonce_ttl_seconds: int = 0
    nonce_header: str = _DEFAULT_NONCE_HEADER

    vendor_header: str = _DEFAULT_VENDOR_HEADER
    audit_enabled: bool = True


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network


def _parse_networks(raw: list[str]) -> list[_IPNetwork]:
    networks: list[_IPNetwork] = []
    for item in raw:
        try:
            networks.append(ipaddress.ip_network(item, strict=False))
        except ValueError:
            _logger.warning("webhook_auth.invalid_ip_config", entry=item)
    return networks


def _client_ip(request: Request) -> str:
    """Return the best-effort client IP from X-Forwarded-For or the socket."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # X-Forwarded-For may be a comma-separated list; take the first
        return forwarded.split(",")[0].strip()
    if request.client:
        host = request.client.host
        # Starlette TestClient can report a non-IP host sentinel.
        if host == "testclient":
            return "127.0.0.1"
        return host
    return ""


def _ip_in_whitelist(ip_str: str, networks: list[_IPNetwork]) -> bool:
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return any(addr in net for net in networks)


def _verify_hmac(body: bytes, raw_sig: str, secret: bytes) -> bool:
    sig = raw_sig.removeprefix("sha256=").strip()
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

_REJECT_MESSAGES: dict[str, str] = {
    "secret_missing": "Webhook secret header missing",
    "secret_invalid": "Webhook secret invalid",
    "signature_missing": "Webhook signature header missing",
    "signature_invalid": "Webhook signature verification failed",
    "ip_blocked": "Request origin not permitted",
    "nonce_missing": "Nonce header missing",
    "nonce_replayed": "Nonce already used",
}


class WebhookAuthMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that enforces webhook authentication.

    Mount on a FastAPI application::

        app.add_middleware(
            WebhookAuthMiddleware,
            config=WebhookAuthConfig(secret="s3cr3t"),
        )

    ``redis_client`` must be an instance of ``swm_redis.RedisClient`` when
    nonce replay prevention is enabled (``nonce_ttl_seconds > 0``).
    """

    def __init__(
        self,
        app: object,
        *,
        config: WebhookAuthConfig,
        redis_client: object | None = None,
    ) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._cfg = config
        self._redis = redis_client
        self._networks: list[_IPNetwork] = (
            _parse_networks(config.allowed_ips) if config.allowed_ips else []
        )

    # ------------------------------------------------------------------
    # Core dispatch
    # ------------------------------------------------------------------

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start_ns = time.perf_counter_ns()
        body = await request.body()
        client_ip = _client_ip(request)
        vendor_id = request.headers.get(self._cfg.vendor_header, "")
        checks_run: list[str] = []
        reject_reason: str | None = None

        # 1. Secret header --------------------------------------------------
        if self._cfg.secret is not None:
            checks_run.append("secret")
            raw = request.headers.get(self._cfg.secret_header)
            if not raw:
                reject_reason = "secret_missing"
            elif not hmac.compare_digest(raw, self._cfg.secret):
                reject_reason = "secret_invalid"

        # 2. HMAC signature -------------------------------------------------
        if reject_reason is None and self._cfg.hmac_secret is not None:
            checks_run.append("signature")
            raw_sig = request.headers.get(self._cfg.signature_header)
            if not raw_sig:
                reject_reason = "signature_missing"
            elif not _verify_hmac(body, raw_sig, self._cfg.hmac_secret):
                reject_reason = "signature_invalid"

        # 3. IP whitelist ---------------------------------------------------
        if reject_reason is None and self._networks:
            checks_run.append("ip_whitelist")
            if not _ip_in_whitelist(client_ip, self._networks):
                reject_reason = "ip_blocked"

        # 4. Nonce replay prevention ----------------------------------------
        if reject_reason is None and self._cfg.nonce_ttl_seconds > 0:
            checks_run.append("nonce")
            nonce = request.headers.get(self._cfg.nonce_header)
            if not nonce:
                reject_reason = "nonce_missing"
            else:
                reject_reason = await self._check_nonce(nonce)

        # 5. Emit audit log -------------------------------------------------
        latency_ms = (time.perf_counter_ns() - start_ns) / 1_000_000
        if self._cfg.audit_enabled:
            _logger.info(
                "webhook_auth.audit",
                outcome="reject" if reject_reason else "allow",
                reason=reject_reason,
                checks_run=checks_run,
                client_ip=client_ip,
                vendor_id=vendor_id,
                method=request.method,
                path=request.url.path,
                latency_ms=round(latency_ms, 3),
            )

        if reject_reason:
            return JSONResponse(
                status_code=401,
                content={"error": _REJECT_MESSAGES.get(reject_reason, reject_reason)},
            )

        return await call_next(request)

    # ------------------------------------------------------------------
    # Nonce helpers
    # ------------------------------------------------------------------

    async def _check_nonce(self, nonce: str) -> str | None:
        """Return a reject-reason string or None if the nonce is fresh."""
        if self._redis is None:
            # No Redis; skip nonce check rather than hard-fail
            _logger.warning("webhook_auth.nonce_check_skipped", reason="no_redis_client")
            return None
        key = f"{_NONCE_REDIS_PREFIX}{nonce}"
        # Atomically SET key if it does not exist (NX) with expiry
        stored = await self._redis.set(key, "1", ex=self._cfg.nonce_ttl_seconds, nx=True)
        if not stored:
            return "nonce_replayed"
        return None
