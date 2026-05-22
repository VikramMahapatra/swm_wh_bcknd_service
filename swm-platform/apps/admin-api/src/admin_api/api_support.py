from csv import DictWriter
from datetime import date, datetime
from io import BytesIO, StringIO
from collections.abc import Awaitable, Callable
from csv import DictReader
from functools import lru_cache
import json
import secrets
from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import String, asc, cast, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response
from swm_auth import decode_access_token
from swm_common import get_settings
from swm_db import AuditLogORM

from jwt import InvalidTokenError


class PageResponse(BaseModel):
    items: list[dict[str, Any]]
    page: int
    page_size: int
    total: int


class RoleContext(BaseModel):
    subject: str
    role: str
    permissions: list[str]
    auth_type: str


class _ApiKeyRecord(BaseModel):
    key: str
    subject: str
    role: str
    permissions: list[str]


class _SecuritySettings(BaseModel):
    jwt_secret: str
    jwt_algorithm: str
    auth_enforce_jwt: bool
    auth_allow_legacy_role_header: bool
    auth_legacy_default_role: str
    auth_api_keys: list[_ApiKeyRecord]


class MessageResponse(BaseModel):
    message: str


class IngestionFailureRecord(BaseModel):
    id: str
    source: str
    stage: str | None = None
    vendor_id: str | None = None
    request_id: str | None = None
    reason: str | None = None
    retryable: bool | None = None
    item_index: int | None = None
    stored_at: datetime | None = None
    payload_raw: str | None = None


class IngestionFailurePage(BaseModel):
    items: list[IngestionFailureRecord]
    total: int
    source: str


class LiveMapTruckPosition(BaseModel):
    imei: str
    device_id: str | None = None
    vehicle_id: str | None = None
    lat: float
    lng: float
    speed_kph: float
    heading: int
    ignition: bool
    event_ts: datetime
    status: str | None = None
    vendor_id: str | None = None


class LiveMapSnapshotResponse(BaseModel):
    items: list[LiveMapTruckPosition]
    total: int


_ROLE_ALIASES: dict[str, str] = {
    "admin": "admin",
    "fleet manager": "fleet_manager",
    "fleet_manager": "fleet_manager",
    "supervisor": "supervisor",
    "operator": "operator",
    "ops": "operator",
    "analyst": "analyst",
    "viewer": "read_only",
    "readonly": "read_only",
    "read-only": "read_only",
    "read_only": "read_only",
}

_ROLE_DEFAULT_PERMISSIONS: dict[str, list[str]] = {
    "admin": ["*"],
    "fleet_manager": ["fleet.read", "fleet.write", "operations.read", "reports.read"],
    "supervisor": ["fleet.read", "operations.read", "operations.execute", "incidents.manage"],
    "operator": ["fleet.read", "operations.execute"],
    "analyst": ["fleet.read", "analytics.read", "reports.read"],
    "read_only": ["fleet.read", "analytics.read", "reports.read"],
}


def _canonical_role(role: str | None) -> str:
    if role is None:
        return "read_only"
    return _ROLE_ALIASES.get(role.strip().lower(), role.strip().lower())


def _normalize_permissions(values: Any, *, role: str) -> list[str]:
    if isinstance(values, list):
        out = [str(v).strip() for v in values if str(v).strip()]
        if out:
            return sorted(set(out))
    if isinstance(values, str):
        chunks = [part.strip() for part in values.split(",") if part.strip()]
        if chunks:
            return sorted(set(chunks))
    return _ROLE_DEFAULT_PERMISSIONS.get(role, ["fleet.read"])


def _parse_api_key_records(raw: str | None) -> list[_ApiKeyRecord]:
    if raw is None or not raw.strip():
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []

    rows: list[_ApiKeyRecord] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key", "")).strip()
        if not key:
            continue
        role = _canonical_role(str(item.get("role", "operator")))
        permissions = _normalize_permissions(item.get("permissions", []), role=role)
        rows.append(
            _ApiKeyRecord(
                key=key,
                subject=str(item.get("subject", "service")).strip() or "service",
                role=role,
                permissions=permissions,
            )
        )
    return rows


@lru_cache(maxsize=1)
def _get_security_settings() -> _SecuritySettings:
    settings = get_settings()
    return _SecuritySettings(
        jwt_secret=settings.jwt_secret,
        jwt_algorithm=settings.jwt_algorithm,
        auth_enforce_jwt=settings.auth_enforce_jwt,
        auth_allow_legacy_role_header=settings.auth_allow_legacy_role_header,
        auth_legacy_default_role=settings.auth_legacy_default_role,
        auth_api_keys=_parse_api_key_records(settings.auth_api_keys_json),
    )


def _find_api_key_record(provided_key: str, records: list[_ApiKeyRecord]) -> _ApiKeyRecord | None:
    for record in records:
        if secrets.compare_digest(provided_key, record.key):
            return record
    return None


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def _to_dict(obj: Any) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for col in obj.__table__.columns:
        if col.name == "metadata" and hasattr(obj, "metadata_json"):
            value = getattr(obj, "metadata_json")
        elif hasattr(obj, col.name):
            value = getattr(obj, col.name)
        elif hasattr(obj, f"{col.name}_json"):
            # Support mapped attributes where the DB column name differs
            # from the ORM attribute (e.g. value -> value_json).
            value = getattr(obj, f"{col.name}_json")
        else:
            value = None
        if isinstance(value, UUID):
            data[col.name] = str(value)
        elif isinstance(value, datetime):
            data[col.name] = value.isoformat()
        else:
            data[col.name] = value
    return data


def _serialize_scalar(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return value


def _to_str(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _to_bool(value: Any) -> bool | None:
    if value is None:
        return None
    raw = _to_str(value).strip().lower()
    if raw in {"1", "true", "yes", "y", "on"}:
        return True
    if raw in {"0", "false", "no", "n", "off"}:
        return False
    return None


def _to_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    raw = _to_str(value).strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _normalize_stream_fields(fields: Any) -> dict[str, Any]:
    if not isinstance(fields, dict):
        return {}
    normalized: dict[str, Any] = {}
    for key, value in fields.items():
        normalized[_to_str(key)] = value
    return normalized


async def _read_failure_stream(redis_client: Any, stream: str, *, source: str, limit: int) -> list[IngestionFailureRecord]:
    rows = await redis_client.xrange(stream, count=limit)
    items: list[IngestionFailureRecord] = []
    for entry in rows:
        if not isinstance(entry, (list, tuple)) or len(entry) != 2:
            continue
        entry_id, fields = entry
        data = _normalize_stream_fields(fields)
        item_index: int | None = None
        if data.get("item_index") is not None and _to_str(data.get("item_index")).isdigit():
            item_index = int(_to_str(data.get("item_index")))
        items.append(
            IngestionFailureRecord(
                id=_to_str(entry_id),
                source=source,
                stage=_to_str(data["stage"]) if data.get("stage") is not None else None,
                vendor_id=_to_str(data["vendor_id"]) if data.get("vendor_id") is not None else None,
                request_id=_to_str(data["request_id"]) if data.get("request_id") is not None else None,
                reason=_to_str(data["reason"]) if data.get("reason") is not None else None,
                retryable=_to_bool(data.get("retryable")),
                item_index=item_index,
                stored_at=_to_datetime(data.get("stored_at")),
                payload_raw=_to_str(data["payload_raw"]) if data.get("payload_raw") is not None else None,
            )
        )
    return items


def _rows_from_result(result: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in result.mappings().all():
        rows.append({key: _serialize_scalar(value) for key, value in dict(row).items()})
    return rows


def _allowed_sort(model: Any) -> set[str]:
    return {c.name for c in model.__table__.columns}


def _csv_response(rows: list[dict[str, Any]], filename: str) -> Response:
    output = StringIO()
    if rows:
        writer = DictWriter(output, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _xlsx_response(rows: list[dict[str, Any]], filename: str) -> Response:
    try:
        from openpyxl import Workbook
    except ImportError as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail="openpyxl is required for xlsx export") from exc

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Report"

    if rows:
        headers = list(rows[0].keys())
        sheet.append(headers)
        for row in rows:
            sheet.append([row.get(h) for h in headers])

    output = BytesIO()
    workbook.save(output)
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _pdf_response(rows: list[dict[str, Any]], *, filename: str, title: str) -> Response:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail="reportlab is required for pdf export") from exc

    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=A4)
    width, height = A4
    x = 40
    y = height - 40

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(x, y, title)
    y -= 24
    pdf.setFont("Helvetica", 9)

    if not rows:
        pdf.drawString(x, y, "No data")
    else:
        for row in rows:
            if y < 50:
                pdf.showPage()
                y = height - 40
                pdf.setFont("Helvetica", 9)
            line = " | ".join(f"{k}: {row.get(k)}" for k in row)
            pdf.drawString(x, y, line[:170])
            y -= 14

    pdf.save()
    return Response(
        content=output.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _export_rows(rows: list[dict[str, Any]], *, export: str, basename: str, title: str) -> Any:
    if export == "csv":
        return _csv_response(rows, f"{basename}.csv")
    if export == "xlsx":
        return _xlsx_response(rows, f"{basename}.xlsx")
    if export == "pdf":
        return _pdf_response(rows, filename=f"{basename}.pdf", title=title)
    return {"items": rows, "total": len(rows)}


def _actor_from_request(request: Request) -> str:
    actor = request.headers.get("x-user") or request.headers.get("x-actor")
    return actor if actor else "system"


async def _write_audit_log(
    session: AsyncSession,
    *,
    entity_type: str,
    entity_id: str,
    action: str,
    actor: str,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
    metadata: dict[str, Any] | None = None,
) -> None:
    session.add(
        AuditLogORM(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor=actor,
            before_json=before,
            after_json=after,
            metadata_json=metadata or {},
        )
    )
    await session.flush()


async def get_role_context(request: Request) -> RoleContext:
    sec = _get_security_settings()

    bearer_token = _extract_bearer_token(request.headers.get("authorization"))
    if bearer_token:
        try:
            claims = decode_access_token(bearer_token, sec.jwt_secret, sec.jwt_algorithm)
        except InvalidTokenError as exc:
            raise HTTPException(status_code=401, detail="invalid access token") from exc

        role = _canonical_role(str(claims.get("role", claims.get("roles", "read_only"))))
        permissions = _normalize_permissions(claims.get("permissions", []), role=role)
        return RoleContext(
            subject=str(claims.get("sub", "jwt-user")),
            role=role,
            permissions=permissions,
            auth_type="jwt",
        )

    api_key = request.headers.get("x-api-key", "").strip()
    if api_key:
        match = _find_api_key_record(api_key, sec.auth_api_keys)
        if match is None:
            raise HTTPException(status_code=401, detail="invalid api key")
        return RoleContext(
            subject=match.subject,
            role=match.role,
            permissions=match.permissions,
            auth_type="api_key",
        )

    if sec.auth_allow_legacy_role_header:
        legacy_role = request.headers.get("x-role", sec.auth_legacy_default_role)
        role = _canonical_role(legacy_role)
        return RoleContext(
            subject=request.headers.get("x-user", "legacy-user"),
            role=role,
            permissions=_ROLE_DEFAULT_PERMISSIONS.get(role, ["fleet.read"]),
            auth_type="legacy_header",
        )

    if sec.auth_enforce_jwt:
        raise HTTPException(status_code=401, detail="authentication required")

    raise HTTPException(status_code=401, detail="authentication required")


def require_roles(*roles: str):
    allowed = {_canonical_role(role) for role in roles}

    async def _require(ctx: RoleContext = Depends(get_role_context)) -> RoleContext:
        if _canonical_role(ctx.role) not in allowed:
            raise HTTPException(status_code=403, detail="forbidden")
        return ctx

    return _require


def _raise_not_found(entity: str, entity_id: UUID) -> None:
    raise HTTPException(status_code=404, detail=f"{entity} with id={entity_id} not found")


async def _fetch_or_404(getter: Callable[[UUID], Awaitable[Any | None]], entity: str, entity_id: UUID) -> Any:
    row = await getter(entity_id)
    if row is None:
        _raise_not_found(entity, entity_id)
    return row


def _parse_csv(file_content: str) -> list[dict[str, str]]:
    reader = DictReader(StringIO(file_content))
    return [dict(row) for row in reader]


def _parse_csv_with_required(file_content: str, *, required_columns: set[str]) -> list[dict[str, str]]:
    reader = DictReader(StringIO(file_content))
    headers = set(reader.fieldnames or [])
    missing = sorted(required_columns - headers)
    if missing:
        raise HTTPException(status_code=400, detail=f"missing csv columns: {', '.join(missing)}")
    return [dict(row) for row in reader]


def _parse_bool(value: str | None, *, default: bool = True) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _parse_uuid(value: str | None) -> UUID | None:
    if value is None or value == "":
        return None
    return UUID(value)


async def _list_entities(  # noqa: PLR0913
    session: AsyncSession,
    model: Any,
    *,
    page: int,
    page_size: int,
    q: str | None,
    sort_by: str,
    sort_order: str,
    filters: dict[str, Any],
) -> PageResponse:
    stmt = select(model)

    for key, value in filters.items():
        if value is None:
            continue
        stmt = stmt.where(getattr(model, key) == value)

    if q:
        q_like = f"%{q.strip()}%"
        searchable = [
            col.name
            for col in model.__table__.columns
            if isinstance(col.type, String) and col.name not in {"webhook_secret", "signature_key"}
        ]
        if searchable:
            stmt = stmt.where(or_(*[cast(getattr(model, c), String).ilike(q_like) for c in searchable]))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = int((await session.execute(count_stmt)).scalar_one())

    sort_fields = _allowed_sort(model)
    if sort_by not in sort_fields:
        sort_by = "created_at" if "created_at" in sort_fields else next(iter(sort_fields))
    order_col = getattr(model, sort_by)
    stmt = stmt.order_by(desc(order_col) if sort_order == "desc" else asc(order_col))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    rows = list((await session.execute(stmt)).scalars().all())
    return PageResponse(items=[_to_dict(r) for r in rows], page=page, page_size=page_size, total=total)
