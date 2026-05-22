from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from websocket_api.main import app


class _PubSubStub:
    def __init__(self) -> None:
        self._sent = False

    async def subscribe(self, _channel: str) -> None:
        return None

    async def unsubscribe(self, _channel: str) -> None:
        return None

    async def close(self) -> None:
        return None

    async def get_message(self, timeout: float = 1.0):
        await asyncio.sleep(0)
        if not self._sent:
            self._sent = True
            return {"data": '{"imei":"123456789012345","lat":18.5,"lon":73.8}'}
        return None


class _RedisStub:
    def pubsub(self, ignore_subscribe_messages: bool = True):
        return _PubSubStub()


def test_websocket_api_healthz():
    with TestClient(app) as client:
        response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["service"] == "websocket-api"


def test_websocket_realtime_stream(monkeypatch):
    from websocket_api import main as ws_main

    monkeypatch.setattr(ws_main, "redis_client", _RedisStub())

    with TestClient(app) as client:
        with client.websocket_connect("/ws/realtime") as ws:
            payload = ws.receive_text()
            assert "imei" in payload
