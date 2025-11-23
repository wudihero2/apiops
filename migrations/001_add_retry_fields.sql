-- Migration: Add retry fields to ops_job table
-- Created: 2025-01-15
-- Description: Add retry_count and max_retries columns for job retry mechanism

-- Add retry_count column (default 0)
ALTER TABLE ops_job
ADD COLUMN IF NOT EXISTS retry_count INTEGER NOT NULL DEFAULT 0;

-- Add max_retries column (default 3)
ALTER TABLE ops_job
ADD COLUMN IF NOT EXISTS max_retries INTEGER NOT NULL DEFAULT 3;

-- Update existing jobs to have default retry values
UPDATE ops_job
SET retry_count = 0, max_retries = 3
WHERE retry_count IS NULL OR max_retries IS NULL;

-- Verify migration
SELECT
    column_name,
    data_type,
    column_default
FROM information_schema.columns
WHERE table_name = 'ops_job'
    AND column_name IN ('retry_count', 'max_retries');
