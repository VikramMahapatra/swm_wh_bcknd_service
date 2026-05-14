import asyncio

import asyncpg


async def check() -> None:
    conn = await asyncpg.connect(
        host="ec2-13-203-201-10.ap-south-1.compute.amazonaws.com",
        port=5432,
        user="zenadmin",
        password="Zen$123",  # noqa: S106
        database="swm_bknd_db",
        ssl="require",
        timeout=10,
    )
    row = await conn.fetchrow("SELECT version()")
    await conn.close()
    if row:
        print("PostgreSQL OK:", str(row[0])[:80])


asyncio.run(check())
