-- Rollback Migration: Remove duplicate prevention columns and tables
-- File: migrations/003_rollback_duplicate_prevention.sql
-- Author: WebDataScraper Team
-- Created: January 18, 2026
-- Description: Rollback script for duplicate prevention migration

BEGIN;

-- Step 1: Drop log table
DROP TABLE IF EXISTS duplicate_detection_log CASCADE;

-- Step 2: Drop indexes on cards table
DROP INDEX IF EXISTS idx_cards_normalized_trgm;
DROP INDEX IF EXISTS idx_cards_issuer_program;
DROP INDEX IF EXISTS idx_cards_fee_range;
DROP INDEX IF EXISTS idx_cards_fingerprint;
DROP INDEX IF EXISTS idx_cards_normalized;

-- Step 3: Drop constraints
ALTER TABLE cards DROP CONSTRAINT IF EXISTS chk_confidence;

-- Step 4: Drop columns from cards table
ALTER TABLE cards DROP COLUMN IF EXISTS confidence_score;
ALTER TABLE cards DROP COLUMN IF EXISTS sources;
ALTER TABLE cards DROP COLUMN IF EXISTS fingerprint;
ALTER TABLE cards DROP COLUMN IF EXISTS normalized_name;

COMMIT;
