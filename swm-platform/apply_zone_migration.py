#!/usr/bin/env python3
"""Apply zone migration directly to database"""
import asyncio
import sys
from sqlalchemy import text
from swm_common import get_settings
from swm_db.base import get_async_engine

async def apply_migration():
    """Apply zone migration"""
    settings = get_settings()
    engine = get_async_engine(settings.postgres_dsn)
    
    try:
        async with engine.begin() as conn:
            # Add columns if they don't exist
            sql = text("""
                ALTER TABLE zones
                ADD COLUMN IF NOT EXISTS description VARCHAR(512),
                ADD COLUMN IF NOT EXISTS supervisor_name VARCHAR(255),
                ADD COLUMN IF NOT EXISTS supervisor_phone VARCHAR(32);
            """)
            
            await conn.execute(sql)
            print("✅ Successfully added zone columns")
            
            # Verify columns
            verify_sql = text("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'zones' 
                AND column_name IN ('description', 'supervisor_name', 'supervisor_phone')
                ORDER BY column_name;
            """)
            
            result = await conn.execute(verify_sql)
            rows = result.fetchall()
            print("\n✅ Verified columns:")
            for row in rows:
                print(f"  - {row[0]}: {row[1]}")
            
            return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        await engine.dispose()

if __name__ == "__main__":
    success = asyncio.run(apply_migration())
    sys.exit(0 if success else 1)
