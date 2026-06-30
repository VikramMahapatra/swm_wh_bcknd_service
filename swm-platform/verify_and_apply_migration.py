#!/usr/bin/env python3
"""Verify and apply zone migration"""
import asyncpg
import asyncio
import sys

# AWS Database credentials from .env
DB_HOST = "ec2-13-203-201-10.ap-south-1.compute.amazonaws.com"
DB_PORT = 5432
DB_USER = "zenadmin"
DB_PASSWORD = "Zen$123"
DB_NAME = "swm_bknd_db"

async def verify_and_apply():
    """Connect to database and apply migration if needed"""
    try:
        # Connect to database
        conn = await asyncpg.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            ssl="require",
            timeout=10,
        )
        
        print("✅ Connected to AWS Postgres database")
        
        # Check if columns exist
        check_sql = """
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'zones' 
            AND column_name IN ('description', 'supervisor_name', 'supervisor_phone')
        """
        
        existing_cols = await conn.fetch(check_sql)
        existing_col_names = {row['column_name'] for row in existing_cols}
        
        needed_cols = {'description', 'supervisor_name', 'supervisor_phone'}
        missing_cols = needed_cols - existing_col_names
        
        if not missing_cols:
            print("✅ All zone columns already exist!")
            print(f"   Found: {existing_col_names}")
        else:
            print(f"❌ Missing columns: {missing_cols}")
            print("Applying migration...")
            
            # Apply migration
            await conn.execute("""
                ALTER TABLE zones
                ADD COLUMN IF NOT EXISTS description VARCHAR(512),
                ADD COLUMN IF NOT EXISTS supervisor_name VARCHAR(255),
                ADD COLUMN IF NOT EXISTS supervisor_phone VARCHAR(32)
            """)
            
            print("✅ Columns added successfully!")
            
            # Mark migration as applied
            await conn.execute(
                "INSERT INTO alembic_version (version_num) VALUES ($1) ON CONFLICT DO NOTHING",
                "0029_zone_extra_fields"
            )
            
            print("✅ Migration marked as applied in alembic_version")
        
        # Verify final state
        final_cols = await conn.fetch(check_sql)
        print(f"\n✅ Final verification: {len(final_cols)} columns present")
        for row in final_cols:
            print(f"   - {row['column_name']}")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(verify_and_apply())
    sys.exit(0 if success else 1)
