-- Rollback: 005_rollback_card_master_list.sql

DROP TRIGGER IF EXISTS trigger_master_list_updated ON card_master_list;
DROP FUNCTION IF EXISTS update_master_list_timestamp();
DROP INDEX IF EXISTS idx_cards_master;
ALTER TABLE cards DROP COLUMN IF EXISTS master_card_id;
DROP TABLE IF EXISTS scraped_card_data;
DROP TABLE IF EXISTS card_master_list;
