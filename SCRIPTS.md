# Scripts Reference

This document describes all Python scripts in the WebDataScraper project.

## 🚀 Main Scripts (Start Here)

### `seed_cards.py`
**Primary script** for populating the database with curated Canadian credit card data.
- Uploads 34 cards from `data/curated_cards.json`
- Includes category rewards and signup bonuses
- **Usage:** `python seed_cards.py`

### `scrape_workflow.py`
Orchestrates the complete scraping workflow with duplicate prevention.
- Scrapes from multiple sources
- Validates and deduplicates data
- Uploads to Supabase
- **Usage:** `python scrape_workflow.py`

### `scraper.py`
Core scraper module with parsing utilities for credit card data.

### `credit_card_uploader.py`
Handles all Supabase database operations for cards, rewards, and bonuses.

## 🔍 Data Management

### Duplicate Detection & Cleanup

- **`check_duplicates.py`** - Quickly check for duplicate cards in database
- **`review_duplicates.py`** - Generate detailed duplicate analysis reports
- **`monitor_duplicates.py`** - Continuous monitoring of duplicate entries
- **`deduplicate_cards.py`** - Remove duplicate cards (basic)
- **`advanced_deduplicate.py`** - Advanced deduplication with ML-based matching
- **`bulk_deduplicate.py`** - Batch deduplication operations
- **`cleanup_duplicates.py`** - Remove cards without category rewards
- **`show_duplicates_report.py`** - Display duplicate statistics
- **`simple_duplicate_prevention.py`** - Basic duplicate prevention utilities

### Data Merging & Matching

- **`data_merger.py`** - Merge card data from multiple sources
- **`card_matcher.py`** - Match and compare card records using fuzzy matching
- **`program_matcher.py`** - Match and normalize reward program names

### Card Identity & Master Records

- **`card_identity_manager.py`** - Manage unique card identities and deduplication
- **`card_master_manager.py`** - Maintain master card records

## 🌐 Scraping Scripts

### `credit_card_scraper.py`
Base scraper class with HTML parsing utilities for extracting card data.

### `targeted_scraper.py`
Focused scraper for specific credit cards or issuers.

### `scrape_and_upload.py`
Combined scraping and uploading in a single workflow.

### `upload_cards.py`
Standalone uploader for manually prepared card data.

## 🔧 Configuration & Utilities

### Core Modules

- **`config.py`** - Centralized configuration management (loads from `.env`)
- **`logger_config.py`** - Logging setup with file and console handlers
- **`rate_limiter.py`** - Adaptive rate limiting with domain tracking
- **`retry_util.py`** - Retry decorators with exponential backoff
- **`error_handler.py`** - Custom exceptions and error tracking
- **`supabase_client.py`** - Generic Supabase client wrapper

## 💾 Database Management

### Reward Programs

- **`reward_programs.py`** - Manage reward program taxonomy
- **`seed_reward_programs.py`** - Populate reward programs table
- **`backfill_card_programs.py`** - Backfill missing reward program associations

### Migrations & Schema

- **`apply_migration.py`** - Show SQL migration instructions
- **`apply_migrations_simple.py`** - Simple migration application guide
- **`run_migration.py`** - Migration runner utility
- **`schema.sql`** - Database schema definition
- **`combined_migrations.sql`** - Combined migration scripts

### Data Operations

- **`reset_to_seed_data.py`** - Reset database to seed data state
- **`clear_all_supabase_data.py`** - **⚠️ DANGER:** Clear all data from Supabase tables
- **`check_tables.py`** - Verify database table structure and contents

## 📝 Documentation Files

- **`README.md`** - Main project documentation
- **`SCRIPTS.md`** - This file (script reference)
- **`PROJECT_ANALYSIS.md`** - Detailed project analysis and architecture
- **`Claude.md`** - Claude AI assistant context and prompts
- **`docs/`** - Additional documentation
  - `TASK_REWARD_TAXONOMY.md` - Reward taxonomy implementation
  - `IMPLEMENTATION_SUMMARY.md` - Feature implementation details

## 🧪 Testing

- **`tests/`** - Unit tests with pytest
  - `test_scraper.py` - Scraper functionality tests
  - `test_data_merger.py` - Data merging tests
  - `test_card_matcher.py` - Card matching tests
  - `test_duplicate_prevention.py` - Duplicate detection tests
  - `test_reward_taxonomy.py` - Reward taxonomy tests

**Run tests:** `pytest tests/ -v`

## 📊 Typical Workflows

### Initial Setup
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your Supabase credentials

# 3. Seed database
python seed_cards.py
```

### Scraping New Data
```bash
# Full workflow (recommended)
python scrape_workflow.py

# Or manually
python credit_card_scraper.py
python upload_cards.py
```

### Maintenance
```bash
# Check for duplicates
python check_duplicates.py

# Review and clean
python review_duplicates.py
python cleanup_duplicates.py

# Reset if needed
python reset_to_seed_data.py
```

## ⚠️ Dangerous Scripts

These scripts can delete data. Use with caution:

- **`clear_all_supabase_data.py`** - Deletes ALL data from Supabase
- **`cleanup_duplicates.py`** - Removes cards without category rewards
- **`deduplicate_cards.py`** - Removes duplicate cards

Always backup your database before running destructive operations.

## 🔍 Script Categories Summary

| Category | Count | Key Scripts |
|----------|-------|-------------|
| **Main** | 4 | seed_cards, scrape_workflow, scraper, uploader |
| **Duplicate Management** | 9 | check, review, monitor, deduplicate variants |
| **Data Operations** | 3 | data_merger, card_matcher, program_matcher |
| **Scraping** | 3 | credit_card_scraper, targeted_scraper, scrape_and_upload |
| **Configuration** | 6 | config, logger, rate_limiter, retry_util, error_handler |
| **Database** | 8 | migrations, schema, seed programs, backfill |
| **Utilities** | 4 | check_tables, reset, clear data |

**Total:** 37 Python scripts

---

*For more details on any script, run `python <script_name>.py --help` or read the docstrings in the source code.*
