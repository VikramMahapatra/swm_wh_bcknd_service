from __future__ import annotations

from pathlib import Path

import clickhouse_connect
from swm_common import get_settings


def _split_statements(sql: str) -> list[str]:
    statements: list[str] = []
    chunk: list[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        chunk.append(line)
        if stripped.endswith(";"):
            statements.append("\n".join(chunk).rstrip(";\n "))
            chunk = []
    if chunk:
        statements.append("\n".join(chunk))
    return [s for s in statements if s.strip()]


def main() -> None:
    settings = get_settings()
    migration_file = (
        Path(__file__).resolve().parent.parent
        / "libs"
        / "clickhouse"
        / "migrations"
        / "0001_raw_telemetry.sql"
    )
    sql = migration_file.read_text(encoding="utf-8")
    statements = _split_statements(sql)

    client = clickhouse_connect.get_client(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        database=settings.clickhouse_db,
        username=settings.clickhouse_user,
        password=settings.clickhouse_password,
    )

    try:
        for stmt in statements:
            client.command(stmt)
        print(f"Applied ClickHouse migration: {migration_file.name}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
