from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from swm_db import TicketCommentORM, TicketORM, get_db_session

from admin_api.api_support import RoleContext, get_role_context
from admin_api.main import app


class _FakeResult:
    def __init__(self, *, rows=None, scalar_value=None):
        self._rows = rows or []
        self._scalar_value = scalar_value

    def scalars(self):
        return self

    def all(self):
        return list(self._rows)

    def first(self):
        if self._rows:
            return self._rows[0]
        return None

    def scalar(self):
        return self._scalar_value


class _TicketSession:
    def __init__(self):
        self.tickets: list[TicketORM] = []
        self.comments: list[TicketCommentORM] = []

    def add(self, obj):
        now = datetime.now(UTC)
        if isinstance(obj, TicketORM):
            if getattr(obj, "id", None) is None:
                obj.id = uuid4()
            if getattr(obj, "created_at", None) is None:
                obj.created_at = now
            obj.updated_at = now
            self.tickets.append(obj)
            return

        if isinstance(obj, TicketCommentORM):
            if getattr(obj, "id", None) is None:
                obj.id = uuid4()
            if getattr(obj, "created_at", None) is None:
                obj.created_at = now
            self.comments.append(obj)

    async def commit(self):
        return None

    async def refresh(self, _obj):
        return None

    def _extract_eq_value(self, statement_text: str, criteria, field_token: str):
        if field_token not in statement_text:
            return None
        for criterion in criteria:
            left = getattr(criterion, "left", None)
            right = getattr(criterion, "right", None)
            if getattr(left, "key", None) and field_token.endswith(getattr(left, "key", "")):
                return getattr(right, "value", None)
        return None

    async def execute(self, statement):
        stmt_text = str(statement)
        criteria = list(getattr(statement, "_where_criteria", []))
        column_descriptions = list(getattr(statement, "column_descriptions", []))

        is_ticket_id_only_select = (
            len(column_descriptions) == 1
            and column_descriptions[0].get("entity") is TicketORM
            and getattr(column_descriptions[0].get("expr"), "key", None) == "id"
        )

        if "count(tickets.id)" in stmt_text:
            rows = list(self.tickets)
            status_value = self._extract_eq_value(stmt_text, criteria, "tickets.status")
            if status_value is not None:
                rows = [row for row in rows if row.status == status_value]
            if "tickets.sla_breached IS true" in stmt_text:
                rows = [row for row in rows if bool(row.sla_breached)]
            return _FakeResult(scalar_value=len(rows))

        if "FROM tickets" in stmt_text:
            ticket_id_value = self._extract_eq_value(stmt_text, criteria, "tickets.id")
            status_value = self._extract_eq_value(stmt_text, criteria, "tickets.status")
            priority_value = self._extract_eq_value(stmt_text, criteria, "tickets.priority")
            category_value = self._extract_eq_value(stmt_text, criteria, "tickets.category")

            rows = list(self.tickets)
            if ticket_id_value is not None:
                rows = [row for row in rows if row.id == ticket_id_value]
            if status_value is not None:
                rows = [row for row in rows if row.status == status_value]
            if priority_value is not None:
                rows = [row for row in rows if row.priority == priority_value]
            if category_value is not None:
                rows = [row for row in rows if row.category == category_value]
            rows.sort(key=lambda item: item.created_at, reverse=True)

            if is_ticket_id_only_select:
                row = rows[0] if rows else None
                return _FakeResult(rows=[(row.id,)] if row else [])

            return _FakeResult(rows=rows)

        if "FROM ticket_comments" in stmt_text:
            ticket_id_value = self._extract_eq_value(stmt_text, criteria, "ticket_comments.ticket_id")
            rows = list(self.comments)
            if ticket_id_value is not None:
                rows = [row for row in rows if row.ticket_id == ticket_id_value]
            rows.sort(key=lambda item: item.created_at)
            return _FakeResult(rows=rows)

        return _FakeResult(rows=[])


def _build_client(fake_session: _TicketSession, *, role: str = "admin", roles: list[str] | None = None) -> TestClient:
    async def _override_db_session():
        yield fake_session

    async def _override_role_context() -> RoleContext:
        effective_roles = roles if roles is not None else [role]
        return RoleContext(
            subject="test-user",
            role=role,
            roles=effective_roles,
            permissions=["*"],
            auth_type="test",
        )

    app.dependency_overrides[get_db_session] = _override_db_session
    app.dependency_overrides[get_role_context] = _override_role_context
    return TestClient(app)


def test_ticket_create_update_comment_and_detail_flow():
    fake_session = _TicketSession()
    with _build_client(fake_session) as client:
        create_resp = client.post(
            "/tickets",
            json={
                "title": "Ticket One",
                "description": "First issue",
                "category": "complaint",
                "priority": "high",
                "status": "open",
                "assignedTo": "Zone Supervisor",
            },
            headers={"x-role": "admin"},
        )
        assert create_resp.status_code == 200
        ticket_id = create_resp.json()["id"]
        UUID(ticket_id)

        update_resp = client.put(
            f"/tickets/{ticket_id}",
            json={"status": "in_progress", "escalationLevel": 1},
            headers={"x-role": "ops"},
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["status"] == "in_progress"
        assert update_resp.json()["escalationLevel"] == 1

        comment_resp = client.post(
            f"/tickets/{ticket_id}/comments",
            json={"comment": "Investigating now", "is_internal": False},
            headers={"x-role": "viewer"},
        )
        assert comment_resp.status_code == 200
        assert comment_resp.json()["content"] == "Investigating now"

        comments_resp = client.get(f"/tickets/{ticket_id}/comments", headers={"x-role": "viewer"})
        assert comments_resp.status_code == 200
        assert len(comments_resp.json()) == 1

        detail_resp = client.get(f"/tickets/{ticket_id}", headers={"x-role": "viewer"})
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["id"] == ticket_id
        assert detail["status"] == "in_progress"
        assert len(detail["comments"]) == 1

    app.dependency_overrides.clear()


def test_ticket_filters_and_statistics_summary():
    fake_session = _TicketSession()
    with _build_client(fake_session) as client:
        payloads = [
            {
                "title": "Open Critical",
                "description": "A",
                "category": "route_issue",
                "priority": "critical",
                "status": "open",
                "slaBreached": True,
            },
            {
                "title": "Pending Medium",
                "description": "B",
                "category": "maintenance",
                "priority": "medium",
                "status": "pending",
            },
        ]

        for payload in payloads:
            resp = client.post("/tickets", json=payload, headers={"x-role": "admin"})
            assert resp.status_code == 200

        list_resp = client.get(
            "/tickets",
            params={"status": "open", "priority": "critical", "category": "route_issue"},
            headers={"x-role": "viewer"},
        )
        assert list_resp.status_code == 200
        items = list_resp.json()
        assert len(items) == 1
        assert items[0]["title"] == "Open Critical"

        stats_resp = client.get("/tickets/statistics/summary", headers={"x-role": "viewer"})
        assert stats_resp.status_code == 200
        stats = stats_resp.json()
        assert stats["total"] == 2
        assert stats["open"] == 1
        assert stats["pending"] == 1
        assert stats["sla_breached"] == 1

    app.dependency_overrides.clear()


def test_ticket_missing_ticket_and_empty_comment_validation():
    fake_session = _TicketSession()
    with _build_client(fake_session) as client:
        create_resp = client.post(
            "/tickets",
            json={
                "title": "Validation Ticket",
                "description": "Testing invalid comment",
                "category": "other",
                "priority": "low",
                "status": "open",
            },
        )
        assert create_resp.status_code == 200
        ticket_id = create_resp.json()["id"]

        empty_comment_resp = client.post(
            f"/tickets/{ticket_id}/comments",
            json={"comment": "   ", "is_internal": False},
        )
        assert empty_comment_resp.status_code == 400
        assert empty_comment_resp.json()["detail"] == "comment is required"

        missing_ticket_id = str(uuid4())
        missing_ticket_resp = client.get(f"/tickets/{missing_ticket_id}")
        assert missing_ticket_resp.status_code == 404

        missing_comment_resp = client.post(
            f"/tickets/{missing_ticket_id}/comments",
            json={"comment": "comment"},
        )
        assert missing_comment_resp.status_code == 404

    app.dependency_overrides.clear()


def test_ticket_write_endpoints_forbid_viewer_role():
    fake_session = _TicketSession()

    with _build_client(fake_session, role="admin") as admin_client:
        create_resp = admin_client.post(
            "/tickets",
            json={
                "title": "Auth Seed",
                "description": "seed",
                "category": "complaint",
                "priority": "medium",
                "status": "open",
            },
        )
        assert create_resp.status_code == 200
        ticket_id = create_resp.json()["id"]

    app.dependency_overrides.clear()


def test_ticket_malformed_uuid_returns_not_found():
    fake_session = _TicketSession()
    with _build_client(fake_session) as client:
        detail_resp = client.get("/tickets/not-a-uuid")
        assert detail_resp.status_code == 404

        update_resp = client.put("/tickets/not-a-uuid", json={"status": "resolved"})
        assert update_resp.status_code == 404

        comments_resp = client.get("/tickets/not-a-uuid/comments")
        assert comments_resp.status_code == 404

        create_comment_resp = client.post("/tickets/not-a-uuid/comments", json={"comment": "x"})
        assert create_comment_resp.status_code == 404

    app.dependency_overrides.clear()


def test_ticket_create_requires_non_empty_title():
    fake_session = _TicketSession()
    with _build_client(fake_session) as client:
        create_resp = client.post(
            "/tickets",
            json={
                "title": "",
                "description": "missing title",
                "category": "complaint",
                "priority": "medium",
                "status": "open",
            },
        )
        assert create_resp.status_code == 422

    app.dependency_overrides.clear()


def test_ticket_create_rejects_invalid_status_priority_and_category():
    fake_session = _TicketSession()
    with _build_client(fake_session) as client:
        create_resp = client.post(
            "/tickets",
            json={
                "title": "Invalid Enums",
                "description": "should fail request validation",
                "category": "custom_category",
                "priority": "urgent_plus",
                "status": "queued_external",
            },
        )
        assert create_resp.status_code == 422

        valid_create_resp = client.post(
            "/tickets",
            json={
                "title": "Valid Ticket",
                "description": "seed for invalid update",
                "category": "complaint",
                "priority": "medium",
                "status": "open",
            },
        )
        assert valid_create_resp.status_code == 200
        ticket_id = valid_create_resp.json()["id"]

        update_resp = client.put(
            f"/tickets/{ticket_id}",
            json={"status": "bad_status", "priority": "bad_priority", "category": "bad_category"},
        )
        assert update_resp.status_code == 422

    app.dependency_overrides.clear()


def test_ticket_related_ids_accept_legacy_string_codes():
    fake_session = _TicketSession()
    with _build_client(fake_session) as client:
        create_resp = client.post(
            "/tickets",
            json={
                "title": "Legacy IDs",
                "description": "preserve UI compatibility for related identifiers",
                "category": "complaint",
                "priority": "medium",
                "status": "open",
                "relatedAlertId": "ALT-2024-0160",
                "relatedTruckId": "TRK001",
                "relatedDriverId": "DRV001",
            },
        )
        assert create_resp.status_code == 200
        created = create_resp.json()
        assert created["relatedAlertId"] == "ALT-2024-0160"
        assert created["relatedTruckId"] == "TRK001"
        assert created["relatedDriverId"] == "DRV001"

        update_resp = client.put(
            f"/tickets/{created['id']}",
            json={
                "relatedAlertId": "ALT-2024-0999",
                "relatedTruckId": "TRK099",
                "relatedDriverId": "DRV099",
            },
        )
        assert update_resp.status_code == 200
        updated = update_resp.json()
        assert updated["relatedAlertId"] == "ALT-2024-0999"
        assert updated["relatedTruckId"] == "TRK099"
        assert updated["relatedDriverId"] == "DRV099"

    app.dependency_overrides.clear()


def test_ticket_write_endpoints_forbid_viewer_role():
    fake_session = _TicketSession()

    with _build_client(fake_session, role="admin") as admin_client:
        create_resp = admin_client.post(
            "/tickets",
            json={
                "title": "Auth Seed",
                "description": "seed",
                "category": "complaint",
                "priority": "medium",
                "status": "open",
            },
        )
        assert create_resp.status_code == 200
        ticket_id = create_resp.json()["id"]

    app.dependency_overrides.clear()

    with _build_client(fake_session, role="viewer") as viewer_client:
        viewer_create_resp = viewer_client.post(
            "/tickets",
            json={
                "title": "Viewer Create",
                "description": "forbidden",
                "category": "other",
                "priority": "low",
                "status": "open",
            },
        )
        assert viewer_create_resp.status_code == 403

        viewer_update_resp = viewer_client.put(
            f"/tickets/{ticket_id}",
            json={"status": "resolved"},
        )
        assert viewer_update_resp.status_code == 403

    app.dependency_overrides.clear()
