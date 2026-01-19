-- Migration: Add duplicate prevention columns and tables
-- File: migrations/003_add_duplicate_prevention.sql
-- Author: WebDataScraper Team
-- Created: January 18, 2026
-- Description: Adds fingerprinting, normalized names, and duplicate detection logging

BEGIN;

-- Step 1: Add new columns to cards table
ALTER TABLE cards ADD COLUMN IF NOT EXISTS normalized_name TEXT;
ALTER TABLE cards ADD COLUMN IF NOT EXISTS fingerprint TEXT;
ALTER TABLE cards ADD COLUMN IF NOT EXISTS sources TEXT[] DEFAULT '{}';
ALTER TABLE cards ADD COLUMN IF NOT EXISTS confidence_score DECIMAL DEFAULT 0.5;

-- Step 2: Add constraints
ALTER TABLE cards ADD CONSTRAINT IF NOT EXISTS chk_confidence
    CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0);

-- Step 3: Create indexes
CREATE INDEX IF NOT EXISTS idx_cards_normalized ON cards(issuer, normalized_name);
CREATE UNIQUE INDEX IF NOT EXISTS idx_cards_fingerprint ON cards(fingerprint);
CREATE INDEX IF NOT EXISTS idx_cards_fee_range ON cards(annual_fee);
CREATE INDEX IF NOT EXISTS idx_cards_issuer_program ON cards(issuer, reward_program);

-- Step 4: Create trigram index if extension available (PostgreSQL)
DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS pg_trgm;
    CREATE INDEX IF NOT EXISTS idx_cards_normalized_trgm
        ON cards USING gin(normalized_name gin_trgm_ops);
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'pg_trgm extension not available, skipping trigram index';
END $$;

-- Step 5: Create log table
CREATE TABLE IF NOT EXISTS duplicate_detection_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    card_key_1 TEXT NOT NULL,
    card_key_2 TEXT NOT NULL,
    fingerprint TEXT,
    similarity_score DECIMAL NOT NULL,
    action_taken TEXT NOT NULL, -- 'auto_merged', 'flagged_manual_review', 'ignored'
    merged_into_id UUID REFERENCES cards(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT DEFAULT 'system',
    metadata JSONB -- Additional context (component scores, edge case info, etc.)
);

-- Step 6: Create indexes on log table
CREATE INDEX IF NOT EXISTS idx_duplicate_log_created ON duplicate_detection_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_duplicate_log_action ON duplicate_detection_log(action_taken);
CREATE INDEX IF NOT EXISTS idx_duplicate_log_score ON duplicate_detection_log(similarity_score DESC);

-- Step 7: Add comments for documentation
COMMENT ON COLUMN cards.normalized_name IS 'Semantically normalized card name for fuzzy matching';
COMMENT ON COLUMN cards.fingerprint IS 'SHA-256 hash of issuer|name|program|fee|network for exact duplicate detection';
COMMENT ON COLUMN cards.sources IS 'Array of data source names that reported this card (for merge tracking)';
COMMENT ON COLUMN cards.confidence_score IS 'Confidence score (0.0-1.0) for card data quality';

COMMENT ON TABLE duplicate_detection_log IS 'Audit trail for all duplicate detection and merge operations';
COMMENT ON COLUMN duplicate_detection_log.action_taken IS 'Action: auto_merged, flagged_manual_review, or ignored';
COMMENT ON COLUMN duplicate_detection_log.metadata IS 'JSON containing component scores, edge case info, etc.';

COMMIT;
