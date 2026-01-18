-- Migration: Add duplicate prevention columns and tables
-- File: migrations/003_add_duplicate_prevention.sql
-- Created: January 18, 2026
-- Purpose: Add fingerprinting and duplicate detection capabilities

BEGIN;

-- ============================================================================
-- Add new columns to cards table
-- ============================================================================

-- Add normalized_name for faster lookups
ALTER TABLE cards ADD COLUMN IF NOT EXISTS normalized_name TEXT;

-- Add fingerprint with UNIQUE constraint
ALTER TABLE cards ADD COLUMN IF NOT EXISTS fingerprint TEXT;

-- Add source tracking (array of source names)
ALTER TABLE cards ADD COLUMN IF NOT EXISTS sources TEXT[] DEFAULT '{}';

-- Add confidence score (0.0 to 1.0)
ALTER TABLE cards ADD COLUMN IF NOT EXISTS confidence_score DECIMAL DEFAULT 0.5;

-- Add last_verified timestamp
ALTER TABLE cards ADD COLUMN IF NOT EXISTS last_verified TIMESTAMPTZ DEFAULT NOW();

-- ============================================================================
-- Create indexes for performance
-- ============================================================================

-- Index for normalized name lookups
CREATE INDEX IF NOT EXISTS idx_cards_normalized 
ON cards(issuer, normalized_name);

-- Unique index for fingerprints (prevents duplicates)
CREATE UNIQUE INDEX IF NOT EXISTS idx_cards_fingerprint 
ON cards(fingerprint) 
WHERE fingerprint IS NOT NULL;

-- Index for source tracking
CREATE INDEX IF NOT EXISTS idx_cards_sources 
ON cards USING GIN(sources);

-- Index for confidence score filtering
CREATE INDEX IF NOT EXISTS idx_cards_confidence 
ON cards(confidence_score);

-- ============================================================================
-- Create duplicate_detection_log table
-- ============================================================================

CREATE TABLE IF NOT EXISTS duplicate_detection_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    card_key_1 TEXT NOT NULL,
    card_key_2 TEXT NOT NULL,
    fingerprint TEXT,
    similarity_score DECIMAL NOT NULL,
    action_taken TEXT NOT NULL CHECK (action_taken IN ('auto_merged', 'flagged', 'ignored', 'manual_merged')),
    merged_into_id UUID REFERENCES cards(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB,
    
    -- Ensure we don't log the same pair twice
    CONSTRAINT unique_card_pair UNIQUE (card_key_1, card_key_2)
);

-- Indexes for duplicate_detection_log
CREATE INDEX IF NOT EXISTS idx_duplicate_log_created 
ON duplicate_detection_log(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_duplicate_log_action 
ON duplicate_detection_log(action_taken);

CREATE INDEX IF NOT EXISTS idx_duplicate_log_similarity 
ON duplicate_detection_log(similarity_score DESC);

CREATE INDEX IF NOT EXISTS idx_duplicate_log_fingerprint 
ON duplicate_detection_log(fingerprint);

-- ============================================================================
-- Add comments for documentation
-- ============================================================================

COMMENT ON COLUMN cards.normalized_name IS 
'Normalized card name with formatting removed for fuzzy matching';

COMMENT ON COLUMN cards.fingerprint IS 
'Unique fingerprint hash combining issuer, normalized name, program, and fee bucket';

COMMENT ON COLUMN cards.sources IS 
'Array of data source names that provided information about this card';

COMMENT ON COLUMN cards.confidence_score IS 
'Confidence score (0.0-1.0) based on number of sources and data quality';

COMMENT ON COLUMN cards.last_verified IS 
'Timestamp of last verification or update from any source';

COMMENT ON TABLE duplicate_detection_log IS 
'Audit log of all duplicate detection and merge actions';

-- ============================================================================
-- Create function to update last_verified automatically
-- ============================================================================

CREATE OR REPLACE FUNCTION update_last_verified()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_verified = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to auto-update last_verified on card updates
DROP TRIGGER IF EXISTS trigger_update_last_verified ON cards;
CREATE TRIGGER trigger_update_last_verified
    BEFORE UPDATE ON cards
    FOR EACH ROW
    EXECUTE FUNCTION update_last_verified();

-- ============================================================================
-- Backfill existing cards with new fields
-- ============================================================================

-- Function to normalize card names (matches Python implementation)
CREATE OR REPLACE FUNCTION normalize_card_name(name TEXT)
RETURNS TEXT AS $$
BEGIN
    -- Lowercase
    name := LOWER(name);
    
    -- Remove trademark symbols
    name := REGEXP_REPLACE(name, '[®™©℠]', '', 'g');
    
    -- Remove marketing characters
    name := REGEXP_REPLACE(name, '[*†‡§]', '', 'g');
    
    -- Remove "Card" suffix
    name := REGEXP_REPLACE(name, '\s+card\s*$', '', 'i');
    
    -- Collapse multiple spaces
    name := REGEXP_REPLACE(name, '\s+', ' ', 'g');
    
    -- Remove punctuation except spaces
    name := REGEXP_REPLACE(name, '[^\w\s]', '', 'g');
    
    -- Trim
    name := TRIM(name);
    
    RETURN name;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to generate fingerprint (matches Python implementation)
CREATE OR REPLACE FUNCTION generate_card_fingerprint(
    p_issuer TEXT,
    p_name TEXT,
    p_program TEXT,
    p_fee DECIMAL
)
RETURNS TEXT AS $$
DECLARE
    normalized_name TEXT;
    normalized_program TEXT;
    fee_bucket INTEGER;
    fingerprint_str TEXT;
BEGIN
    -- Normalize name
    normalized_name := normalize_card_name(p_name);
    
    -- Normalize issuer
    p_issuer := LOWER(TRIM(p_issuer));
    
    -- Round fee to nearest $10
    fee_bucket := ROUND(p_fee / 10) * 10;
    
    -- Normalize program
    normalized_program := LOWER(TRIM(p_program));
    normalized_program := REGEXP_REPLACE(normalized_program, '[®™©℠]', '', 'g');
    normalized_program := REGEXP_REPLACE(normalized_program, '[^\w\s]', '', 'g');
    normalized_program := REGEXP_REPLACE(normalized_program, '\s+', ' ', 'g');
    normalized_program := TRIM(normalized_program);
    
    -- Combine into string
    fingerprint_str := p_issuer || '|' || normalized_name || '|' || normalized_program || '|' || fee_bucket;
    
    -- Return first 16 characters of SHA-256 hash
    RETURN SUBSTRING(ENCODE(DIGEST(fingerprint_str, 'sha256'), 'hex'), 1, 16);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Backfill normalized_name for existing cards
UPDATE cards
SET normalized_name = normalize_card_name(name)
WHERE normalized_name IS NULL;

-- Backfill fingerprint for existing cards
UPDATE cards
SET fingerprint = generate_card_fingerprint(issuer, name, reward_program, annual_fee)
WHERE fingerprint IS NULL;

-- Backfill sources from source column if it exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'cards' AND column_name = 'source'
    ) THEN
        UPDATE cards
        SET sources = ARRAY[source]
        WHERE sources = '{}' AND source IS NOT NULL;
    END IF;
END $$;

-- ============================================================================
-- Create view for duplicate detection
-- ============================================================================

CREATE OR REPLACE VIEW potential_duplicates AS
SELECT 
    c1.id AS card1_id,
    c1.name AS card1_name,
    c1.card_key AS card1_key,
    c2.id AS card2_id,
    c2.name AS card2_name,
    c2.card_key AS card2_key,
    c1.fingerprint,
    c1.issuer,
    c1.reward_program,
    ABS(c1.annual_fee - c2.annual_fee) AS fee_difference
FROM cards c1
JOIN cards c2 ON c1.fingerprint = c2.fingerprint AND c1.id < c2.id
WHERE c1.fingerprint IS NOT NULL;

COMMENT ON VIEW potential_duplicates IS 
'Shows cards with matching fingerprints (exact duplicates)';

-- ============================================================================
-- Grant permissions (adjust as needed for your setup)
-- ============================================================================

-- Grant access to service role
GRANT SELECT, INSERT, UPDATE, DELETE ON cards TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON duplicate_detection_log TO service_role;
GRANT SELECT ON potential_duplicates TO service_role;

-- Grant read access to anon role
GRANT SELECT ON cards TO anon;
GRANT SELECT ON potential_duplicates TO anon;

COMMIT;

-- ============================================================================
-- Verification queries
-- ============================================================================

-- Check for cards with duplicate fingerprints
SELECT 
    fingerprint,
    COUNT(*) as count,
    STRING_AGG(name, ' | ') as card_names
FROM cards
WHERE fingerprint IS NOT NULL
GROUP BY fingerprint
HAVING COUNT(*) > 1
ORDER BY count DESC;

-- Show statistics
SELECT 
    COUNT(*) as total_cards,
    COUNT(DISTINCT fingerprint) as unique_fingerprints,
    COUNT(*) - COUNT(DISTINCT fingerprint) as potential_duplicates,
    AVG(confidence_score) as avg_confidence,
    COUNT(*) FILTER (WHERE ARRAY_LENGTH(sources, 1) > 1) as multi_source_cards
FROM cards;
