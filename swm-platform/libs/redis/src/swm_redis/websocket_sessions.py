"""Redis-backed WebSocket session management.

Keys:
- ws:connections                 (set of active session_ids)
- user:sessions:<user_id>        (set of session_ids for a user)
- ws:user:<session_id>           (JSON session payload)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from prometheus_client import Counter, Gauge

from swm_common import get_logger
from swm_redis.client import RedisClient

logger = get_logger("swm_redis.websocket_sessions")


_WS_CONNECT_TOTAL = Counter(
    "swm_ws_connect_total",
    "Total websocket session connect events",
    ["status"],
)
_WS_DISCONNECT_TOTAL = Counter(
    "swm_ws_disconnect_total",
    "Total websocket session disconnect events",
    ["status"],
)
_WS_HEARTBEAT_TOTAL = Counter(
    "swm_ws_heartbeat_total",
    "Total websocket heartbeat events",
    ["status"],
)
_WS_ACTIVE_CONNECTIONS = Gauge(
    "swm_ws_active_connections",
    "Active websocket connection count",
)


@dataclass(slots=True)
class WebSocketSessionConfig:
    key_prefix: str = ""
    session_ttl_seconds: int = 300
    user_sessions_ttl_seconds: int = 300


@dataclass(slots=True)
class WebSocketSession:
    session_id: str
    user_id: str
    connected_at: datetime
    last_seen_at: datetime
    device_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class WebSocketSessionKeys:
    def __init__(self, *, prefix: str = "") -> None:
        self.prefix = prefix.strip(":")

    def ws_connections(self) -> str:
        return self._k("ws:connections")

    def user_sessions(self, user_id: str) -> str:
        return self._k(f"user:sessions:{user_id}")

    def ws_user(self, session_id: str) -> str:
        return self._k(f"ws:user:{session_id}")

    def _k(self, suffix: str) -> str:
        return f"{self.prefix}:{suffix}" if self.prefix else suffix


class WebSocketSessionService:
    """Typed API for websocket session lifecycle with heartbeat and cleanup."""

    def __init__(
        self,
        redis_client: RedisClient,
        *,
        config: WebSocketSessionConfig | None = None,
    ) -> None:
        self.redis = redis_client
        self.config = config or WebSocketSessionConfig()
        self.keys = WebSocketSessionKeys(prefix=self.config.key_prefix)

    async def connect(
        self,
        *,
        user_id: str,
        device_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> WebSocketSession:
        now = datetime.now(UTC)
        resolved_session_id = session_id or uuid4().hex
        model = WebSocketSession(
            session_id=resolved_session_id,
            user_id=user_id,
            connected_at=now,
            last_seen_at=now,
            device_id=device_id,
            metadata=metadata or {},
        )

        await self.redis.set_json(
            self.keys.ws_user(resolved_session_id),
            self._serialize(model),
            ttl=self.config.session_ttl_seconds,
        )
        await self.redis.sadd(self.keys.ws_connections(), resolved_session_id)
        await self.redis.sadd(self.keys.user_sessions(user_id), resolved_session_id)
        await self.redis.expire(self.keys.user_sessions(user_id), self.config.user_sessions_ttl_seconds)
        await self._update_active_connections_gauge()
        _WS_CONNECT_TOTAL.labels(status="ok").inc()

        logger.debug(
            "ws_session_connected",
            user_id=user_id,
            session_id=resolved_session_id,
            device_id=device_id,
        )
        return model

    async def get_session(self, session_id: str) -> WebSocketSession | None:
        payload = await self.redis.get_json(self.keys.ws_user(session_id))
        if payload is None:
            return None
        return self._deserialize(payload)

    async def heartbeat(self, session_id: str, *, ts: datetime | None = None) -> bool:
        session = await self.get_session(session_id)
        if session is None:
            _WS_HEARTBEAT_TOTAL.labels(status="missing").inc()
            return False

        session.last_seen_at = ts or datetime.now(UTC)
        await self.redis.set_json(
            self.keys.ws_user(session_id),
            self._serialize(session),
            ttl=self.config.session_ttl_seconds,
        )
        await self.redis.expire(self.keys.user_sessions(session.user_id), self.config.user_sessions_ttl_seconds)
        _WS_HEARTBEAT_TOTAL.labels(status="ok").inc()
        return True

    async def refresh_ttl(self, session_id: str) -> bool:
        """Refresh TTLs without mutating payload fields."""
        session = await self.get_session(session_id)
        if session is None:
            return False
        await self.redis.expire(self.keys.ws_user(session_id), self.config.session_ttl_seconds)
        await self.redis.expire(self.keys.user_sessions(session.user_id), self.config.user_sessions_ttl_seconds)
        return True

    async def disconnect(self, session_id: str) -> bool:
        session = await self.get_session(session_id)
        await self.redis.srem(self.keys.ws_connections(), session_id)

        if session is None:
            await self._update_active_connections_gauge()
            _WS_DISCONNECT_TOTAL.labels(status="missing").inc()
            return False

        await self.redis.srem(self.keys.user_sessions(session.user_id), session_id)
        await self.redis.delete(self.keys.ws_user(session_id))
        await self._update_active_connections_gauge()
        _WS_DISCONNECT_TOTAL.labels(status="ok").inc()
        logger.debug("ws_session_disconnected", user_id=session.user_id, session_id=session_id)
        return True

    async def disconnect_user(self, user_id: str) -> int:
        session_ids = await self.get_user_session_ids(user_id)
        disconnected = 0
        for session_id in session_ids:
            if await self.disconnect(session_id):
                disconnected += 1
        return disconnected

    async def get_user_session_ids(self, user_id: str) -> list[str]:
        members = await self.redis.smembers(self.keys.user_sessions(user_id))
        return sorted(members)

    async def get_user_sessions(self, user_id: str) -> list[WebSocketSession]:
        session_ids = await self.get_user_session_ids(user_id)
        sessions: list[WebSocketSession] = []
        for session_id in session_ids:
            session = await self.get_session(session_id)
            if session is None:
                # stale pointer cleanup
                await self.redis.srem(self.keys.user_sessions(user_id), session_id)
                await self.redis.srem(self.keys.ws_connections(), session_id)
                continue
            sessions.append(session)
        return sessions

    async def is_connected(self, session_id: str) -> bool:
        return await self.redis.sismember(self.keys.ws_connections(), session_id)

    async def active_connection_count(self) -> int:
        return await self.redis.scard(self.keys.ws_connections())

    async def _update_active_connections_gauge(self) -> None:
        try:
            _WS_ACTIVE_CONNECTIONS.set(await self.active_connection_count())
        except Exception as exc:
            logger.debug("ws_active_connections_gauge_update_failed", error=str(exc))

    def _serialize(self, session: WebSocketSession) -> dict[str, Any]:
        data = asdict(session)
        data["connected_at"] = session.connected_at.isoformat()
        data["last_seen_at"] = session.last_seen_at.isoformat()
        return data

    def _deserialize(self, payload: dict[str, Any]) -> WebSocketSession:
        return WebSocketSession(
            session_id=str(payload["session_id"]),
            user_id=str(payload["user_id"]),
            connected_at=datetime.fromisoformat(str(payload["connected_at"])),
            last_seen_at=datetime.fromisoformat(str(payload["last_seen_at"])),
            device_id=str(payload["device_id"]) if payload.get("device_id") is not None else None,
            metadata=dict(payload.get("metadata") or {}),
        )
