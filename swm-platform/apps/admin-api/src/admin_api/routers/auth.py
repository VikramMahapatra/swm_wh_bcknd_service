from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from functools import lru_cache
import base64
import hashlib
import json
import secrets
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from admin_api.api_support import RoleContext, _canonical_role, _normalize_permissions, get_role_context, require_roles
from swm_auth import create_access_token
from swm_common import get_settings
from swm_db import (
    AuthPermissionORM,
    AuthRefreshTokenORM,
    AuthRoleORM,
    AuthUserORM,
    auth_role_permissions,
    auth_user_roles,
    get_db_session,
)

router = APIRouter(prefix="/v1/auth", tags=["auth"])

_REFRESH_TOKEN_TTL_MINUTES = 60 * 24 * 30
_PBKDF2_ITERATIONS = 120_000
_ROLE_PRIORITY = ["admin", "supervisor", "operator", "fleet_manager", "analyst", "read_only"]


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: int
    subject: str
    roles: list[str]
    permissions: list[str]


class TokenIntrospectionResponse(BaseModel):
    active: bool
    subject: str | None = None
    role: str | None = None
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)


class AuthPermissionCreate(BaseModel):
    permission_key: str
    permission_name: str
    description: str | None = None
    active: bool = True


class AuthPermissionUpdate(BaseModel):
    permission_name: str | None = None
    description: str | None = None
    active: bool | None = None


class AuthPermissionResponse(BaseModel):
    id: uuid.UUID
    permission_key: str
    permission_name: str
    description: str | None = None
    active: bool
    created_at: datetime
    updated_at: datetime


class AuthRoleCreate(BaseModel):
    role_key: str
    role_name: str
    description: str | None = None
    active: bool = True
    permissions: list[str] = Field(default_factory=list)


class AuthRoleUpdate(BaseModel):
    role_name: str | None = None
    description: str | None = None
    active: bool | None = None
    permissions: list[str] | None = None


class AuthRoleResponse(BaseModel):
    id: uuid.UUID
    role_key: str
    role_name: str
    description: str | None = None
    active: bool
    permissions: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class AuthUserCreate(BaseModel):
    username: str
    password: str
    email: str | None = None
    display_name: str | None = None
    active: bool = True
    must_change_password: bool = False
    roles: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuthUserUpdate(BaseModel):
    password: str | None = None
    email: str | None = None
    display_name: str | None = None
    active: bool | None = None
    must_change_password: bool | None = None
    roles: list[str] | None = None
    metadata: dict[str, Any] | None = None


class AuthUserResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: str | None = None
    display_name: str | None = None
    active: bool
    must_change_password: bool
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    token_version: int
    last_login_at: datetime | None = None
    last_login_ip: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class _BootstrapUser(BaseModel):
    username: str
    password: str
    role: str
    subject: str
    active: bool = True
    permissions: list[str] = Field(default_factory=list)


@lru_cache(maxsize=1)
def _get_bootstrap_users() -> list[_BootstrapUser]:
    settings = get_settings()
    raw = getattr(settings, "auth_users_json", "[]")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []

    users: list[_BootstrapUser] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        username = str(item.get("username", "")).strip()
        password = str(item.get("password", "")).strip()
        if not username or not password:
            continue
        role = _canonical_role(str(item.get("role", "viewer")))
        subject = str(item.get("subject", username)).strip() or username
        permissions = _normalize_permissions(item.get("permissions", []), role=role)
        users.append(
            _BootstrapUser(
                username=username,
                password=password,
                role=role,
                subject=subject,
                active=bool(item.get("active", True)),
                permissions=permissions,
            )
        )
    return users


def _normalize_email(value: str | None) -> str | None:
    if value is None:
        return None
    email = value.strip().lower()
    return email or None


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _PBKDF2_ITERATIONS,
    )
    return "pbkdf2_sha256${iterations}${salt}${digest}".format(
        iterations=_PBKDF2_ITERATIONS,
        salt=base64.urlsafe_b64encode(salt).decode("ascii").rstrip("="),
        digest=base64.urlsafe_b64encode(digest).decode("ascii").rstrip("="),
    )


def _verify_password(plain_password: str, stored_password: str) -> bool:
    if stored_password.startswith("pbkdf2_sha256$"):
        try:
            _, iterations_text, salt_b64, digest_b64 = stored_password.split("$", 3)
            iterations = int(iterations_text)
            salt = base64.urlsafe_b64decode(salt_b64 + "===")
            expected = base64.urlsafe_b64decode(digest_b64 + "===")
        except Exception:
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt,
            iterations,
        )
        return secrets.compare_digest(actual, expected)
    if stored_password.startswith("sha256:"):
        expected = stored_password.removeprefix("sha256:").strip().lower()
        actual = hashlib.sha256(plain_password.encode("utf-8")).hexdigest().lower()
        return bool(expected) and secrets.compare_digest(actual, expected)
    return secrets.compare_digest(plain_password, stored_password)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _primary_role(roles: Iterable[str]) -> str:
    normalized = [_canonical_role(role) for role in roles]
    for candidate in _ROLE_PRIORITY:
        if candidate in normalized:
            return candidate
    return normalized[0] if normalized else "read_only"


def _unique_sorted(values: Iterable[str]) -> list[str]:
    return sorted({value for value in values if value})


def _user_permissions(user: AuthUserORM) -> list[str]:
    permissions: set[str] = set()
    for role in user.roles:
        if role.deleted_at is not None or not role.active:
            continue
        for permission in role.permissions:
            if permission.deleted_at is not None or not permission.active:
                continue
            permissions.add(permission.permission_key)
    return sorted(permissions)


def _user_roles(user: AuthUserORM) -> list[str]:
    roles = [role.role_key for role in user.roles if role.deleted_at is None and role.active]
    return _unique_sorted(roles)


def _user_to_response(user: AuthUserORM) -> AuthUserResponse:
    return AuthUserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        active=user.active,
        must_change_password=user.must_change_password,
        roles=_user_roles(user),
        permissions=_user_permissions(user),
        token_version=user.token_version,
        last_login_at=user.last_login_at,
        last_login_ip=user.last_login_ip,
        metadata=user.metadata_json,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def _role_to_response(role: AuthRoleORM) -> AuthRoleResponse:
    permissions = [permission.permission_key for permission in role.permissions if permission.deleted_at is None and permission.active]
    return AuthRoleResponse(
        id=role.id,
        role_key=role.role_key,
        role_name=role.role_name,
        description=role.description,
        active=role.active,
        permissions=_unique_sorted(permissions),
        created_at=role.created_at,
        updated_at=role.updated_at,
    )


def _permission_to_response(permission: AuthPermissionORM) -> AuthPermissionResponse:
    return AuthPermissionResponse(
        id=permission.id,
        permission_key=permission.permission_key,
        permission_name=permission.permission_name,
        description=permission.description,
        active=permission.active,
        created_at=permission.created_at,
        updated_at=permission.updated_at,
    )


async def _ensure_bootstrap_users(session: AsyncSession) -> None:
    user_count = await session.scalar(select(func.count()).select_from(AuthUserORM).where(AuthUserORM.deleted_at.is_(None)))
    if int(user_count or 0) > 0:
        return

    bootstrap_users = _get_bootstrap_users()
    if not bootstrap_users:
        return

    for bootstrap in bootstrap_users:
        role = await _get_or_create_role(
            session,
            role_key=bootstrap.role,
            role_name=bootstrap.role.replace("_", " ").title(),
            active=True,
        )
        for permission_key in bootstrap.permissions or ["*"]:
            permission = await _get_or_create_permission(
                session,
                permission_key=permission_key,
                permission_name=permission_key.replace(".", " ").replace("_", " ").title(),
                active=True,
            )
            link_exists = await session.scalar(
                select(func.count())
                .select_from(auth_role_permissions)
                .where(
                    auth_role_permissions.c.role_id == role.id,
                    auth_role_permissions.c.permission_id == permission.id,
                )
            )
            if not int(link_exists or 0):
                await session.execute(
                    insert(auth_role_permissions).values(role_id=role.id, permission_id=permission.id)
                )

        user = AuthUserORM(
            username=bootstrap.username,
            display_name=bootstrap.subject,
            password_hash=_hash_password(bootstrap.password),
            active=bootstrap.active,
            must_change_password=False,
            metadata_json={},
        )
        session.add(user)
        await session.flush()
        await session.execute(insert(auth_user_roles).values(user_id=user.id, role_id=role.id))

    await session.commit()


async def _get_or_create_role(
    session: AsyncSession,
    *,
    role_key: str,
    role_name: str,
    description: str | None = None,
    active: bool = True,
) -> AuthRoleORM:
    normalized = _canonical_role(role_key)
    existing = await session.scalar(
        select(AuthRoleORM)
        .where(AuthRoleORM.role_key == normalized)
        .options(selectinload(AuthRoleORM.permissions))
    )
    if existing is not None:
        return existing
    role = AuthRoleORM(role_key=normalized, role_name=role_name, description=description, active=active)
    session.add(role)
    await session.flush()
    return role


async def _get_or_create_permission(
    session: AsyncSession,
    *,
    permission_key: str,
    permission_name: str,
    description: str | None = None,
    active: bool = True,
) -> AuthPermissionORM:
    normalized = permission_key.strip().lower()
    existing = await session.scalar(select(AuthPermissionORM).where(AuthPermissionORM.permission_key == normalized))
    if existing is not None:
        return existing
    permission = AuthPermissionORM(
        permission_key=normalized,
        permission_name=permission_name,
        description=description,
        active=active,
    )
    session.add(permission)
    await session.flush()
    return permission


async def _load_user(session: AsyncSession, username: str) -> AuthUserORM | None:
    return await session.scalar(
        select(AuthUserORM)
        .where(AuthUserORM.username == username.strip().lower(), AuthUserORM.deleted_at.is_(None))
        .options(selectinload(AuthUserORM.roles).selectinload(AuthRoleORM.permissions))
    )


async def _load_role(session: AsyncSession, role_key: str) -> AuthRoleORM | None:
    return await session.scalar(
        select(AuthRoleORM)
        .where(AuthRoleORM.role_key == _canonical_role(role_key), AuthRoleORM.deleted_at.is_(None))
        .options(selectinload(AuthRoleORM.permissions))
    )


async def _load_permission(session: AsyncSession, permission_key: str) -> AuthPermissionORM | None:
    return await session.scalar(
        select(AuthPermissionORM).where(
            AuthPermissionORM.permission_key == permission_key.strip().lower(),
            AuthPermissionORM.deleted_at.is_(None),
        )
    )


async def _issue_refresh_token(
    session: AsyncSession,
    *,
    user: AuthUserORM,
    request: Request | None = None,
    family_id: uuid.UUID | None = None,
    expires_in_minutes: int = _REFRESH_TOKEN_TTL_MINUTES,
) -> tuple[str, AuthRefreshTokenORM]:
    raw_refresh_token = secrets.token_urlsafe(48)
    now = datetime.now(tz=UTC)
    record = AuthRefreshTokenORM(
        user_id=user.id,
        token_hash=_hash_token(raw_refresh_token),
        token_family_id=family_id or uuid.uuid4(),
        issued_at=now,
        expires_at=now + timedelta(minutes=expires_in_minutes),
        user_agent=(request.headers.get("user-agent") if request is not None else None),
        ip_address=(request.client.host if request is not None and request.client else None),
    )
    session.add(record)
    await session.flush()
    return raw_refresh_token, record


async def _load_refresh_token(session: AsyncSession, raw_refresh_token: str) -> AuthRefreshTokenORM | None:
    token_hash = _hash_token(raw_refresh_token)
    return await session.scalar(
        select(AuthRefreshTokenORM)
        .where(
            AuthRefreshTokenORM.token_hash == token_hash,
            AuthRefreshTokenORM.revoked_at.is_(None),
            AuthRefreshTokenORM.expires_at > datetime.now(tz=UTC),
        )
        .options(selectinload(AuthRefreshTokenORM.user).selectinload(AuthUserORM.roles).selectinload(AuthRoleORM.permissions))
    )


async def _build_login_response(session: AsyncSession, user: AuthUserORM, request: Request | None = None) -> LoginResponse:
    settings = get_settings()
    roles = _user_roles(user)
    permissions = _user_permissions(user)
    primary_role = _primary_role(roles)
    access_token = create_access_token(
        subject=user.username,
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        expires_minutes=settings.jwt_expiry_minutes,
        extra_claims={
            "role": primary_role,
            "roles": roles,
            "permissions": permissions,
            "token_version": user.token_version,
        },
    )
    refresh_token, _record = await _issue_refresh_token(session, user=user, request=request)
    user.last_login_at = datetime.now(tz=UTC)
    user.last_login_ip = request.client.host if request is not None and request.client else None
    await session.flush()
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_expiry_minutes * 60,
        refresh_expires_in=_REFRESH_TOKEN_TTL_MINUTES * 60,
        subject=user.username,
        roles=roles,
        permissions=permissions,
    )


async def _add_role_to_user(session: AsyncSession, user: AuthUserORM, role: AuthRoleORM, *, actor: str | None = None) -> None:
    if role not in user.roles:
        user.roles.append(role)
        await session.flush()


async def _remove_role_from_user(session: AsyncSession, user: AuthUserORM, role: AuthRoleORM) -> None:
    if role in user.roles:
        user.roles.remove(role)
        await session.flush()


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, request: Request, session: AsyncSession = Depends(get_db_session)) -> LoginResponse:
    await _ensure_bootstrap_users(session)
    user = await _load_user(session, payload.username)
    if user is None or not user.active or user.deleted_at is not None:
        raise HTTPException(status_code=401, detail="invalid credentials")
    if not _verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
    response = await _build_login_response(session, user, request)
    await session.commit()
    return response


@router.post("/refresh", response_model=LoginResponse)
async def refresh(payload: RefreshRequest, session: AsyncSession = Depends(get_db_session)) -> LoginResponse:
    record = await _load_refresh_token(session, payload.refresh_token)
    if record is None or record.user.deleted_at is not None or not record.user.active:
        raise HTTPException(status_code=401, detail="invalid refresh token")
    now = datetime.now(tz=UTC)
    record.last_used_at = now
    record.revoked_at = now
    new_refresh_token, new_record = await _issue_refresh_token(
        session,
        user=record.user,
        family_id=record.token_family_id,
    )
    record.replaced_by_token_id = new_record.id
    settings = get_settings()
    roles = _user_roles(record.user)
    permissions = _user_permissions(record.user)
    access_token = create_access_token(
        subject=record.user.username,
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        expires_minutes=settings.jwt_expiry_minutes,
        extra_claims={
            "role": _primary_role(roles),
            "roles": roles,
            "permissions": permissions,
            "token_version": record.user.token_version,
        },
    )
    await session.commit()
    return LoginResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.jwt_expiry_minutes * 60,
        refresh_expires_in=_REFRESH_TOKEN_TTL_MINUTES * 60,
        subject=record.user.username,
        roles=roles,
        permissions=permissions,
    )


@router.post("/logout")
async def logout(payload: LogoutRequest, session: AsyncSession = Depends(get_db_session)) -> dict[str, bool]:
    record = await _load_refresh_token(session, payload.refresh_token)
    if record is not None:
        record.revoked_at = datetime.now(tz=UTC)
        await session.commit()
    return {"ok": True}


@router.get("/me", response_model=TokenIntrospectionResponse)
async def me(ctx: RoleContext = Depends(get_role_context)) -> TokenIntrospectionResponse:
    return TokenIntrospectionResponse(
        active=True,
        subject=ctx.subject,
        role=ctx.role,
        roles=ctx.roles,
        permissions=ctx.permissions,
    )


@router.get("/users", response_model=list[AuthUserResponse])
async def list_users(
    _: RoleContext = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> list[AuthUserResponse]:
    rows = (
        await session.execute(
            select(AuthUserORM)
            .where(AuthUserORM.deleted_at.is_(None))
            .options(selectinload(AuthUserORM.roles).selectinload(AuthRoleORM.permissions))
            .order_by(AuthUserORM.username.asc())
        )
    ).scalars().all()
    return [_user_to_response(row) for row in rows]


@router.post("/users", response_model=AuthUserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: AuthUserCreate,
    _: RoleContext = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> AuthUserResponse:
    existing = await _load_user(session, payload.username)
    if existing is not None:
        raise HTTPException(status_code=409, detail="user already exists")

    user = AuthUserORM(
        username=payload.username,
        email=_normalize_email(payload.email),
        display_name=payload.display_name,
        password_hash=_hash_password(payload.password),
        active=payload.active,
        must_change_password=payload.must_change_password,
        metadata_json=payload.metadata,
    )
    session.add(user)
    await session.flush()

    role_keys = payload.roles or ["read_only"]
    for role_key in role_keys:
        role = await _get_or_create_role(session, role_key=role_key, role_name=_canonical_role(role_key).replace("_", " ").title())
        await _add_role_to_user(session, user, role)

    await session.commit()
    await session.refresh(user)
    user = await _load_user(session, payload.username) or user
    return _user_to_response(user)


@router.get("/users/{username}", response_model=AuthUserResponse)
async def get_user(
    username: str,
    _: RoleContext = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> AuthUserResponse:
    user = await _load_user(session, username)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    return _user_to_response(user)


@router.patch("/users/{username}", response_model=AuthUserResponse)
async def update_user(
    username: str,
    payload: AuthUserUpdate,
    _: RoleContext = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> AuthUserResponse:
    user = await _load_user(session, username)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")

    if payload.password is not None:
        user.password_hash = _hash_password(payload.password)
        user.token_version += 1
    if payload.email is not None:
        user.email = _normalize_email(payload.email)
    if payload.display_name is not None:
        user.display_name = payload.display_name
    if payload.active is not None:
        user.active = payload.active
    if payload.must_change_password is not None:
        user.must_change_password = payload.must_change_password
    if payload.metadata is not None:
        user.metadata_json = payload.metadata
    if payload.roles is not None:
        current_roles = list(user.roles)
        for role in current_roles:
            await _remove_role_from_user(session, user, role)
        for role_key in (payload.roles or ["read_only"]):
            role = await _get_or_create_role(session, role_key=role_key, role_name=_canonical_role(role_key).replace("_", " ").title())
            await _add_role_to_user(session, user, role)

    await session.commit()
    user = await _load_user(session, username) or user
    return _user_to_response(user)


@router.delete("/users/{username}")
async def delete_user(
    username: str,
    _: RoleContext = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    user = await _load_user(session, username)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    user.soft_delete(actor="admin")
    user.active = False
    user.token_version += 1
    await session.commit()
    return {"ok": True}


@router.post("/users/{username}/roles/{role_key}", response_model=AuthUserResponse)
async def add_user_role(
    username: str,
    role_key: str,
    _: RoleContext = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> AuthUserResponse:
    user = await _load_user(session, username)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    role = await _get_or_create_role(session, role_key=role_key, role_name=_canonical_role(role_key).replace("_", " ").title())
    await _add_role_to_user(session, user, role)
    await session.commit()
    user = await _load_user(session, username) or user
    return _user_to_response(user)


@router.delete("/users/{username}/roles/{role_key}", response_model=AuthUserResponse)
async def remove_user_role(
    username: str,
    role_key: str,
    _: RoleContext = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> AuthUserResponse:
    user = await _load_user(session, username)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    role = await _load_role(session, role_key)
    if role is None:
        raise HTTPException(status_code=404, detail="role not found")
    await _remove_role_from_user(session, user, role)
    user.token_version += 1
    await session.commit()
    user = await _load_user(session, username) or user
    return _user_to_response(user)


@router.get("/roles", response_model=list[AuthRoleResponse])
async def list_roles(
    _: RoleContext = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> list[AuthRoleResponse]:
    rows = (
        await session.execute(
            select(AuthRoleORM)
            .where(AuthRoleORM.deleted_at.is_(None))
            .options(selectinload(AuthRoleORM.permissions))
            .order_by(AuthRoleORM.role_key.asc())
        )
    ).scalars().all()
    return [_role_to_response(row) for row in rows]


@router.post("/roles", response_model=AuthRoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    payload: AuthRoleCreate,
    _: RoleContext = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> AuthRoleResponse:
    role = await _get_or_create_role(
        session,
        role_key=payload.role_key,
        role_name=payload.role_name,
        description=payload.description,
        active=payload.active,
    )
    role.role_name = payload.role_name
    role.description = payload.description
    role.active = payload.active
    if payload.permissions:
        for permission_key in payload.permissions:
            permission = await _get_or_create_permission(
                session,
                permission_key=permission_key,
                permission_name=permission_key.replace(".", " ").replace("_", " ").title(),
            )
            if permission not in role.permissions:
                role.permissions.append(permission)
    await session.commit()
    role = await _load_role(session, payload.role_key) or role
    return _role_to_response(role)


@router.patch("/roles/{role_key}", response_model=AuthRoleResponse)
async def update_role(
    role_key: str,
    payload: AuthRoleUpdate,
    _: RoleContext = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> AuthRoleResponse:
    role = await _load_role(session, role_key)
    if role is None:
        raise HTTPException(status_code=404, detail="role not found")
    if payload.role_name is not None:
        role.role_name = payload.role_name
    if payload.description is not None:
        role.description = payload.description
    if payload.active is not None:
        role.active = payload.active
    if payload.permissions is not None:
        role.permissions[:] = []
        for permission_key in payload.permissions:
            permission = await _get_or_create_permission(
                session,
                permission_key=permission_key,
                permission_name=permission_key.replace(".", " ").replace("_", " ").title(),
            )
            if permission not in role.permissions:
                role.permissions.append(permission)
    await session.commit()
    role = await _load_role(session, role_key) or role
    return _role_to_response(role)


@router.delete("/roles/{role_key}")
async def delete_role(
    role_key: str,
    _: RoleContext = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    role = await _load_role(session, role_key)
    if role is None:
        raise HTTPException(status_code=404, detail="role not found")
    role.soft_delete(actor="admin")
    role.active = False
    await session.commit()
    return {"ok": True}


@router.post("/roles/{role_key}/permissions/{permission_key}", response_model=AuthRoleResponse)
async def add_role_permission(
    role_key: str,
    permission_key: str,
    _: RoleContext = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> AuthRoleResponse:
    role = await _load_role(session, role_key)
    if role is None:
        raise HTTPException(status_code=404, detail="role not found")
    permission = await _get_or_create_permission(
        session,
        permission_key=permission_key,
        permission_name=permission_key.replace(".", " ").replace("_", " ").title(),
    )
    if permission not in role.permissions:
        role.permissions.append(permission)
    await session.commit()
    role = await _load_role(session, role_key) or role
    return _role_to_response(role)


@router.delete("/roles/{role_key}/permissions/{permission_key}", response_model=AuthRoleResponse)
async def remove_role_permission(
    role_key: str,
    permission_key: str,
    _: RoleContext = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> AuthRoleResponse:
    role = await _load_role(session, role_key)
    if role is None:
        raise HTTPException(status_code=404, detail="role not found")
    permission = await _load_permission(session, permission_key)
    if permission is None:
        raise HTTPException(status_code=404, detail="permission not found")
    if permission in role.permissions:
        role.permissions.remove(permission)
    await session.commit()
    role = await _load_role(session, role_key) or role
    return _role_to_response(role)


@router.get("/permissions", response_model=list[AuthPermissionResponse])
async def list_permissions(
    _: RoleContext = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> list[AuthPermissionResponse]:
    rows = (
        await session.execute(
            select(AuthPermissionORM)
            .where(AuthPermissionORM.deleted_at.is_(None))
            .order_by(AuthPermissionORM.permission_key.asc())
        )
    ).scalars().all()
    return [_permission_to_response(row) for row in rows]


@router.post("/permissions", response_model=AuthPermissionResponse, status_code=status.HTTP_201_CREATED)
async def create_permission(
    payload: AuthPermissionCreate,
    _: RoleContext = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> AuthPermissionResponse:
    permission = await _get_or_create_permission(
        session,
        permission_key=payload.permission_key,
        permission_name=payload.permission_name,
        description=payload.description,
        active=payload.active,
    )
    permission.permission_name = payload.permission_name
    permission.description = payload.description
    permission.active = payload.active
    await session.commit()
    permission = await _load_permission(session, payload.permission_key) or permission
    return _permission_to_response(permission)
