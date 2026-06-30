-- Check if columns already exist, if not add them
-- This script applies the 0029_zone_extra_fields migration manually

-- Add columns if they don't exist
ALTER TABLE zones
ADD COLUMN IF NOT EXISTS description VARCHAR(512),
ADD COLUMN IF NOT EXISTS supervisor_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS supervisor_phone VARCHAR(32);

-- Verify the columns exist
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'zones' 
AND column_name IN ('description', 'supervisor_name', 'supervisor_phone');

-- Mark migration as applied in alembic_version table
INSERT INTO alembic_version (version_num) 
VALUES ('0029_zone_extra_fields')
ON CONFLICT (version_num) DO NOTHING;

SELECT * FROM alembic_version ORDER BY version_num DESC LIMIT 10;
