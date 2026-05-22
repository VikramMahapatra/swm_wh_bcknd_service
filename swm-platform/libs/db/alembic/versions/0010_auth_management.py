"""add auth management tables

Revision ID: 0010_auth_management
Revises: 0009_admin_operations_epic
Create Date: 2026-05-22 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_auth_management"
down_revision: str | None = "0009_admin_operations_epic"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "auth_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.Column("role_key", sa.String(length=64), nullable=False),
        sa.Column("role_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id", name="pk_auth_roles"),
        sa.UniqueConstraint("role_key", name="uq_auth_roles_role_key"),
    )
    op.create_index("ix_auth_roles_active", "auth_roles", ["active"])
    op.create_index("ix_auth_roles_role_name", "auth_roles", ["role_name"])
    op.create_index("ix_auth_roles_deleted_at", "auth_roles", ["deleted_at"])

    op.create_table(
        "auth_permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.Column("permission_key", sa.String(length=128), nullable=False),
        sa.Column("permission_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id", name="pk_auth_permissions"),
        sa.UniqueConstraint("permission_key", name="uq_auth_permissions_permission_key"),
    )
    op.create_index("ix_auth_permissions_active", "auth_permissions", ["active"])
    op.create_index("ix_auth_permissions_permission_name", "auth_permissions", ["permission_name"])
    op.create_index("ix_auth_permissions_deleted_at", "auth_permissions", ["deleted_at"])

    op.create_table(
        "auth_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.Column("username", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("token_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_ip", sa.String(length=64), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint("id", name="pk_auth_users"),
        sa.UniqueConstraint("username", name="uq_auth_users_username"),
        sa.UniqueConstraint("email", name="uq_auth_users_email"),
    )
    op.create_index("ix_auth_users_username", "auth_users", ["username"])
    op.create_index("ix_auth_users_email", "auth_users", ["email"])
    op.create_index("ix_auth_users_active", "auth_users", ["active"])
    op.create_index("ix_auth_users_deleted_at", "auth_users", ["deleted_at"])

    op.create_table(
        "auth_role_permissions",
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("permission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("assigned_by", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["permission_id"], ["auth_permissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["auth_roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "permission_id", name="pk_auth_role_permissions"),
    )

    op.create_table(
        "auth_user_roles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("assigned_by", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["role_id"], ["auth_roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["auth_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "role_id", name="pk_auth_user_roles"),
    )

    op.create_table(
        "auth_refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("token_family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("replaced_by_token_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["replaced_by_token_id"], ["auth_refresh_tokens.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["auth_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_auth_refresh_tokens"),
        sa.UniqueConstraint("token_hash", name="uq_auth_refresh_tokens_token_hash"),
    )
    op.create_index("ix_auth_refresh_tokens_user_id", "auth_refresh_tokens", ["user_id"])
    op.create_index("ix_auth_refresh_tokens_expires_at", "auth_refresh_tokens", ["expires_at"])
    op.create_index("ix_auth_refresh_tokens_revoked_at", "auth_refresh_tokens", ["revoked_at"])
    op.create_index("ix_auth_refresh_tokens_token_family_id", "auth_refresh_tokens", ["token_family_id"])


def downgrade() -> None:
    op.drop_index("ix_auth_refresh_tokens_token_family_id", table_name="auth_refresh_tokens")
    op.drop_index("ix_auth_refresh_tokens_revoked_at", table_name="auth_refresh_tokens")
    op.drop_index("ix_auth_refresh_tokens_expires_at", table_name="auth_refresh_tokens")
    op.drop_index("ix_auth_refresh_tokens_user_id", table_name="auth_refresh_tokens")
    op.drop_table("auth_refresh_tokens")

    op.drop_table("auth_user_roles")
    op.drop_table("auth_role_permissions")

    op.drop_index("ix_auth_users_deleted_at", table_name="auth_users")
    op.drop_index("ix_auth_users_active", table_name="auth_users")
    op.drop_index("ix_auth_users_email", table_name="auth_users")
    op.drop_index("ix_auth_users_username", table_name="auth_users")
    op.drop_table("auth_users")

    op.drop_index("ix_auth_permissions_deleted_at", table_name="auth_permissions")
    op.drop_index("ix_auth_permissions_permission_name", table_name="auth_permissions")
    op.drop_index("ix_auth_permissions_active", table_name="auth_permissions")
    op.drop_table("auth_permissions")

    op.drop_index("ix_auth_roles_deleted_at", table_name="auth_roles")
    op.drop_index("ix_auth_roles_role_name", table_name="auth_roles")
    op.drop_index("ix_auth_roles_active", table_name="auth_roles")
    op.drop_table("auth_roles")
