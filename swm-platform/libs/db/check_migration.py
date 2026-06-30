import asyncio
import asyncpg

async def main():
    try:
        conn = await asyncpg.connect("postgresql://swm:swm@localhost:55432/swm")
        rows = await conn.fetch("SELECT version_num FROM alembic_version")
        cols = await conn.fetch("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'wards'
            ORDER BY ordinal_position
        """)
        with open("check_ver.txt", "w") as f:
            f.write("alembic_version: " + str([r[0] for r in rows]) + "\n")
            f.write("ward_columns: " + str([r[0] for r in cols]) + "\n")
        await conn.close()
    except Exception as e:
        with open("check_ver.txt", "w") as f:
            f.write(f"ERROR: {e}\n")

asyncio.run(main())
