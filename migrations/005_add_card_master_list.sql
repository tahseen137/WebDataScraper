-- Migration: 005_add_card_master_list.sql
-- Purpose: Add card master list and scraped data tables

-- Enable UUID extension if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table 1: card_master_list (canonical 106 cards)
CREATE TABLE IF NOT EXISTS card_master_list (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    canonical_name TEXT NOT NULL UNIQUE,
    canonical_issuer TEXT NOT NULL,
    card_category TEXT,
    name_aliases TEXT[] DEFAULT '{}',
    search_terms TEXT[] DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    last_scraped_at TIMESTAMPTZ,
    scrape_status TEXT DEFAULT 'pending' CHECK (scrape_status IN ('pending', 'found', 'not_found', 'error')),
    not_found_count INTEGER DEFAULT 0,
    last_found_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table 2: scraped_card_data (raw data per source)
CREATE TABLE IF NOT EXISTS scraped_card_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    master_card_id UUID REFERENCES card_master_list(id) ON DELETE CASCADE,
    match_confidence DECIMAL(4,3) DEFAULT 0.000,
    source_name TEXT NOT NULL CHECK (source_name IN ('creditcardgenius', 'ratehub', 'greedyrates', 'nerdwallet', 'moneysense')),
    source_url TEXT,
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    scraped_date DATE DEFAULT CURRENT_DATE,
    raw_data JSONB NOT NULL,
    annual_fee DECIMAL(10,2),
    base_reward_rate DECIMAL(5,2),
    category_rewards JSONB,
    signup_bonus JSONB,
    is_processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMPTZ,
    CONSTRAINT unique_source_card_date UNIQUE(master_card_id, source_name, scraped_date)
);

-- Modify cards table: add master_card_id
ALTER TABLE cards ADD COLUMN IF NOT EXISTS master_card_id UUID REFERENCES card_master_list(id);

-- Indexes for card_master_list
CREATE INDEX IF NOT EXISTS idx_master_issuer ON card_master_list(canonical_issuer);
CREATE INDEX IF NOT EXISTS idx_master_category ON card_master_list(card_category);
CREATE INDEX IF NOT EXISTS idx_master_active ON card_master_list(is_active);
CREATE INDEX IF NOT EXISTS idx_master_status ON card_master_list(scrape_status);
CREATE INDEX IF NOT EXISTS idx_master_name_gin ON card_master_list USING GIN (to_tsvector('english', canonical_name));

-- Indexes for scraped_card_data
CREATE INDEX IF NOT EXISTS idx_scraped_master ON scraped_card_data(master_card_id);
CREATE INDEX IF NOT EXISTS idx_scraped_source ON scraped_card_data(source_name);
CREATE INDEX IF NOT EXISTS idx_scraped_processed ON scraped_card_data(is_processed);
CREATE INDEX IF NOT EXISTS idx_scraped_date ON scraped_card_data(scraped_at DESC);

-- Index for cards.master_card_id
CREATE INDEX IF NOT EXISTS idx_cards_master ON cards(master_card_id);

-- Trigger: Update updated_at on card_master_list
CREATE OR REPLACE FUNCTION update_master_list_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_master_list_updated ON card_master_list;
CREATE TRIGGER trigger_master_list_updated
    BEFORE UPDATE ON card_master_list
    FOR EACH ROW EXECUTE FUNCTION update_master_list_timestamp();
