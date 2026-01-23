-- Combined Migrations for WebDataScraper
-- Apply these in Supabase SQL Editor
-- Date: January 19, 2026

-- ============================================================================
-- MIGRATION 003: Add Duplicate Prevention
-- ============================================================================

BEGIN;

-- Step 1: Add new columns to cards table
ALTER TABLE cards ADD COLUMN IF NOT EXISTS normalized_name TEXT;
ALTER TABLE cards ADD COLUMN IF NOT EXISTS fingerprint TEXT;
ALTER TABLE cards ADD COLUMN IF NOT EXISTS sources TEXT[] DEFAULT '{}';
ALTER TABLE cards ADD COLUMN IF NOT EXISTS confidence_score DECIMAL DEFAULT 0.5;

-- Step 2: Add constraints
ALTER TABLE cards DROP CONSTRAINT IF EXISTS chk_confidence;
ALTER TABLE cards ADD CONSTRAINT chk_confidence
    CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0);

-- Step 3: Create indexes
CREATE INDEX IF NOT EXISTS idx_cards_normalized ON cards(issuer, normalized_name);
CREATE UNIQUE INDEX IF NOT EXISTS idx_cards_fingerprint ON cards(fingerprint);
CREATE INDEX IF NOT EXISTS idx_cards_fee_range ON cards(annual_fee);
CREATE INDEX IF NOT EXISTS idx_cards_issuer_program ON cards(issuer, reward_program);

-- Step 4: Create trigram index if extension available
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
    action_taken TEXT NOT NULL,
    merged_into_id UUID REFERENCES cards(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT DEFAULT 'system',
    metadata JSONB
);

-- Step 6: Create indexes on log table
CREATE INDEX IF NOT EXISTS idx_duplicate_log_created ON duplicate_detection_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_duplicate_log_action ON duplicate_detection_log(action_taken);
CREATE INDEX IF NOT EXISTS idx_duplicate_log_score ON duplicate_detection_log(similarity_score DESC);

-- Step 7: Add comments
COMMENT ON COLUMN cards.normalized_name IS 'Semantically normalized card name for fuzzy matching';
COMMENT ON COLUMN cards.fingerprint IS 'SHA-256 hash of issuer|name|program|fee|network for exact duplicate detection';
COMMENT ON COLUMN cards.sources IS 'Array of data source names that reported this card (for merge tracking)';
COMMENT ON COLUMN cards.confidence_score IS 'Confidence score (0.0-1.0) for card data quality';

COMMENT ON TABLE duplicate_detection_log IS 'Audit trail for all duplicate detection and merge operations';
COMMENT ON COLUMN duplicate_detection_log.action_taken IS 'Action: auto_merged, flagged_manual_review, or ignored';
COMMENT ON COLUMN duplicate_detection_log.metadata IS 'JSON containing component scores, edge case info, etc.';

COMMIT;

-- ============================================================================
-- MIGRATION 004: Add Reward Taxonomy
-- ============================================================================

BEGIN;

-- Create reward_programs table
CREATE TABLE IF NOT EXISTS reward_programs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    program_family TEXT NOT NULL,
    program_name TEXT UNIQUE NOT NULL,
    currency_type TEXT NOT NULL,
    base_valuation DECIMAL NOT NULL,
    transfer_partners JSONB,
    redemption_options JSONB,
    issuer_banks TEXT[],
    currency_name TEXT,
    minimum_redemption INTEGER,
    expiry_policy TEXT,
    notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for reward_programs
CREATE INDEX IF NOT EXISTS idx_reward_programs_currency ON reward_programs(currency_type);
CREATE INDEX IF NOT EXISTS idx_reward_programs_family ON reward_programs(program_family);
CREATE INDEX IF NOT EXISTS idx_reward_programs_active ON reward_programs(is_active);

-- Comments
COMMENT ON TABLE reward_programs IS 'Comprehensive registry of Canadian credit card reward programs';
COMMENT ON COLUMN reward_programs.currency_type IS 'cashback, airline_miles, flexible_points, retail_points, entertainment_points, travel_points, hotel_points';
COMMENT ON COLUMN reward_programs.base_valuation IS 'Base value in cents per point/mile';

-- Create point_valuations table
CREATE TABLE IF NOT EXISTS point_valuations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    program_id UUID REFERENCES reward_programs(id) ON DELETE CASCADE,
    redemption_type TEXT NOT NULL,
    cents_per_point DECIMAL NOT NULL,
    minimum_redemption INTEGER,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_valuations_program ON point_valuations(program_id);
CREATE INDEX IF NOT EXISTS idx_valuations_type ON point_valuations(redemption_type);

COMMENT ON TABLE point_valuations IS 'Redemption-specific valuations for reward programs';
COMMENT ON COLUMN point_valuations.redemption_type IS 'travel, statement, merchandise, transfer, flight, upgrade, etc.';

-- Add new columns to cards table
ALTER TABLE cards ADD COLUMN IF NOT EXISTS reward_program_family TEXT;
ALTER TABLE cards ADD COLUMN IF NOT EXISTS reward_program_id UUID REFERENCES reward_programs(id);
ALTER TABLE cards ADD COLUMN IF NOT EXISTS currency_type TEXT;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_cards_program_family ON cards(reward_program_family);
CREATE INDEX IF NOT EXISTS idx_cards_program_id ON cards(reward_program_id);
CREATE INDEX IF NOT EXISTS idx_cards_currency_type ON cards(currency_type);

-- Comments
COMMENT ON COLUMN cards.reward_program_family IS 'Program family name (e.g., "Membership Rewards")';
COMMENT ON COLUMN cards.reward_program_id IS 'Foreign key to reward_programs table';
COMMENT ON COLUMN cards.currency_type IS 'Currency type: cashback, airline_miles, flexible_points, etc.';

COMMIT;
