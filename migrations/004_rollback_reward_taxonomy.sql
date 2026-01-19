-- Rollback Migration: Remove reward program taxonomy
-- File: migrations/004_rollback_reward_taxonomy.sql
-- Author: WebDataScraper Team
-- Created: January 18, 2026
-- Description: Rollback script for reward taxonomy migration

BEGIN;

-- Drop indexes from cards table
DROP INDEX IF EXISTS idx_cards_currency_type;
DROP INDEX IF EXISTS idx_cards_program_id;
DROP INDEX IF EXISTS idx_cards_program_family;

-- Drop columns from cards table
ALTER TABLE cards DROP COLUMN IF EXISTS currency_type;
ALTER TABLE cards DROP COLUMN IF EXISTS reward_program_id;
ALTER TABLE cards DROP COLUMN IF EXISTS reward_program_family;

-- Drop point_valuations table
DROP TABLE IF EXISTS point_valuations CASCADE;

-- Drop reward_programs table
DROP TABLE IF EXISTS reward_programs CASCADE;

COMMIT;
