# WebDataScraper - Claude Context

**Project**: Canadian Credit Card Data Scraper and Database Manager
**Language**: Python 3.12
**Database**: Supabase (PostgreSQL)
**Last Updated**: January 20, 2026
**Architecture Version**: 2.0 (Master-List Based)

---

## Project Overview

WebDataScraper is a comprehensive system for scraping, managing, and analyzing Canadian credit card data. The system includes:

- **Master-List Based Scraping**: Targeted scraping of 106 canonical cards from database
- **Multi-Source Data Merging**: Priority-based merging from 5 Canadian websites
- **Duplicate Prevention**: Advanced fingerprinting and identity management
- **Reward Taxonomy**: Comprehensive classification of 15+ Canadian reward programs
- **Database Management**: Automated upload, verification, and migration system

---

## Project Structure

```
WebDataScraper/
├── docs/                          # Documentation
│   ├── REWARD_TAXONOMY_STATUS.md
│   ├── REWARD_TAXONOMY_IMPLEMENTATION_SUMMARY.md
│   ├── TASK_DUPLICATE_PREVENTION.md
│   ├── IMPLEMENTATION_SUMMARY.md
│   └── DUPLICATE_PREVENTION_QUICKSTART.md
├── migrations/                    # Database migrations
│   ├── 003_add_duplicate_prevention.sql
│   ├── 003_rollback_duplicate_prevention.sql
│   ├── 004_add_reward_taxonomy.sql
│   ├── 004_rollback_reward_taxonomy.sql
│   ├── 005_add_card_master_list.sql        # NEW: Master list tables
│   └── 005_rollback_card_master_list.sql   # NEW: Rollback master list
├── tests/                         # Test suite
│   ├── test_reward_taxonomy.py    # 44 tests for reward taxonomy
│   ├── test_duplicate_prevention.py
│   ├── test_scraper.py
│   ├── test_card_matcher.py       # NEW: Card matching tests
│   └── test_data_merger.py        # NEW: Data merger tests
├── Core Scripts (v2.0)
│   ├── card_master_manager.py     # NEW: Manage master card list
│   ├── card_matcher.py            # NEW: Fuzzy card matching
│   ├── targeted_scraper.py        # NEW: Target-specific scraper
│   ├── data_merger.py             # NEW: Multi-source merger
│   ├── scrape_workflow.py         # NEW: Workflow orchestrator
│   ├── credit_card_uploader.py    # Database upload (enhanced)
│   ├── card_identity_manager.py   # Duplicate prevention
│   ├── program_matcher.py         # Reward program matching
│   └── reward_programs.py         # 15+ program registry
├── Archive (deprecated v1.0)
│   ├── enhanced_scraper.py.bak    # Old discovery-based scraper
│   └── canadian_credit_cards.json.bak  # Backup before DB migration
├── Management Scripts
│   ├── seed_reward_programs.py    # Populate reward programs
│   ├── backfill_card_programs.py  # Update existing cards
│   ├── monitor_duplicates.py      # Duplicate monitoring
│   ├── review_duplicates.py       # Manual duplicate review
│   └── bulk_deduplicate.py        # Batch deduplication
└── Configuration
    ├── config.py                  # Config loader
    ├── logger_config.py           # Logging setup
    ├── .env                       # Credentials (DO NOT COMMIT)
    └── requirements.txt           # Dependencies
```

---

## Core Components

### 1. Master-List Based Scraping (v2.0)

**NEW ARCHITECTURE**: Scrapes specific cards from database instead of discovering cards.

#### Workflow:
1. **Load Master Cards** (`card_master_manager.py`): Get 106 cards from `card_master_list` table
2. **Target Scraping** (`targeted_scraper.py`): Search 5 sources for each specific card
3. **Store Raw Data**: Save to `scraped_card_data` table (one row per source)
4. **Merge Data** (`data_merger.py`): Combine sources using priority rules
5. **Deduplicate**: Final deduplication using fingerprints
6. **Upload**: Save to `cards` table

#### Key Files:
- `card_master_manager.py`: CRUD operations on master list
- `card_matcher.py`: Fuzzy matching (85%+ confidence threshold)
- `targeted_scraper.py`: Source-specific scrapers with matching
- `data_merger.py`: Priority-based merging (CreditCardGenius > Ratehub > etc.)
- `scrape_workflow.py`: Orchestrates complete pipeline

**Usage**:
```bash
# Load master cards from JSON (one-time setup)
python card_master_manager.py --load docs/canadian_credit_cards.json --clear

# Run complete workflow
python scrape_workflow.py --limit 10  # Test with 10 cards
python scrape_workflow.py             # Full scrape (all 106 cards)

# Check statistics
python card_master_manager.py --stats
```

**Key Features**:
- Guaranteed 106 cards (no discovery variation)
- Multi-source verification (5 sources per card)
- Priority-based merging (best data from each source)
- Confidence scoring per card and per source
- Tracks which cards are found/not found

### 2. Reward Program Taxonomy

**Complete classification system for Canadian reward programs**

**Components**:
- `reward_programs.py`: Registry of 15+ programs with valuations
- `program_matcher.py`: Smart pattern matching (90%+ accuracy)
- Database tables: `reward_programs`, `point_valuations`

**Programs Included**:
- **Airline Miles**: Aeroplan, AIR MILES, WestJet Rewards
- **Flexible Points**: Membership Rewards, Avion, Aventura
- **Retail Points**: TD Rewards, BMO Rewards, PC Optimum, Triangle Rewards, MBNA Rewards
- **Entertainment**: Scene+
- **Travel**: Odyssey Rewards
- **Cashback**: Generic cashback programs

**Currency Types**:
1. `cashback` - Direct cash back (1.0¢ per dollar)
2. `airline_miles` - Airline loyalty points (0.1-2.1¢)
3. `flexible_points` - Transferable points (1.0-2.0¢)
4. `retail_points` - Store-specific points (0.1-1.0¢)
5. `entertainment_points` - Entertainment rewards (0.8-1.0¢)
6. `travel_points` - Travel-specific points (0.8-1.0¢)

**Usage**:
```python
from program_matcher import match_reward_program, get_program_info

# Match a card
program, confidence = match_reward_program("TD Aeroplan Visa Infinite", "TD")
# Returns: ('aeroplan', 0.95)

# Get full details
info = get_program_info("Amex Cobalt Card", "American Express")
# Returns: {'program_name': 'Membership Rewards', 'currency_type': 'flexible_points', ...}
```

### 3. Duplicate Prevention System

**Advanced fingerprinting and identity management**

**Components**:
- `card_identity_manager.py`: Core fingerprinting and duplicate detection
- Database table: `duplicate_detection_log`
- Monitoring: `monitor_duplicates.py`, `review_duplicates.py`

**Features**:
- Multi-factor fingerprinting (name, issuer, fee, program)
- Fuzzy matching with 80%+ similarity threshold
- Automatic merging of sources
- Manual review workflow
- Batch deduplication

**Fingerprint Algorithm**:
```
fingerprint = hash(normalized_name + issuer + fee_bucket + program_family)
```

**Usage**:
```bash
# Monitor duplicates
python monitor_duplicates.py --days 7

# Manual review
python review_duplicates.py

# Batch deduplicate
python bulk_deduplicate.py --execute
```

### 4. Database Schema

**Tables**:

#### `card_master_list` (NEW in v2.0)
Canonical 106 cards (source of truth):
- `id`, `canonical_name`, `canonical_issuer`, `card_category`
- `name_aliases[]`, `search_terms[]`, `is_active`
- `scrape_status` (pending, found, not_found, error)
- `not_found_count`, `last_scraped_at`, `last_found_at`

#### `scraped_card_data` (NEW in v2.0)
Raw scraped data per source:
- `id`, `master_card_id` (FK to card_master_list)
- `source_name` (creditcardgenius, ratehub, etc.)
- `match_confidence`, `source_url`, `scraped_at`
- `raw_data` (JSONB), `annual_fee`, `base_reward_rate`
- `category_rewards` (JSONB), `signup_bonus` (JSONB)
- Unique constraint: (master_card_id, source_name, scraped_at::DATE)

#### `cards`
Primary card data with taxonomy fields:
- Core: `id`, `card_key`, `name`, `issuer`, `annual_fee`
- Legacy: `reward_program`, `reward_currency`, `point_valuation`
- Taxonomy: `reward_program_id`, `reward_program_family`, `currency_type`
- Duplicate Prevention: `fingerprint`, `sources`, `data_quality_score`
- Master List Link: `master_card_id` (FK to card_master_list) **NEW**

#### `reward_programs`
Reward program registry:
- `id`, `program_family`, `program_name`, `currency_type`
- `base_valuation`, `transfer_partners`, `redemption_options`
- `issuer_banks`, `currency_name`, `expiry_policy`

#### `point_valuations`
Redemption-specific valuations:
- `id`, `program_id`, `redemption_type`, `cents_per_point`
- Examples: travel, statement, merchandise, transfer

#### `duplicate_detection_log`
Duplicate detection history:
- `id`, `card1_fingerprint`, `card2_fingerprint`, `similarity_score`
- `action_taken`, `manual_review_required`, `reviewed_by`

---

## Common Workflows

### Setup New Environment

```bash
# Install dependencies
pip install -r requirements.txt
pip install jellyfish  # NEW: Required for fuzzy matching

# Configure credentials
cp .env.example .env
# Edit .env with your Supabase credentials

# Run migrations (in order)
psql -U your_user -d your_db -f migrations/003_add_duplicate_prevention.sql
psql -U your_user -d your_db -f migrations/004_add_reward_taxonomy.sql
psql -U your_user -d your_db -f migrations/005_add_card_master_list.sql  # NEW

# Seed reward programs
python seed_reward_programs.py --clear

# Load master card list (one-time setup)
python card_master_manager.py --load docs/canadian_credit_cards.json --clear

# Verify setup
python -m pytest tests/ -v
```

### Scraping Workflow (v2.0)

```bash
# 1. Load master cards (if not already loaded)
python card_master_manager.py --load docs/canadian_credit_cards.json --clear
python card_master_manager.py --stats  # Verify 106 cards loaded

# 2. Run targeted scraper workflow
python scrape_workflow.py --limit 5    # Test with 5 cards first
python scrape_workflow.py              # Full scrape (all 106 cards)

# Output per card:
# - Searches 5 sources
# - Stores raw data in scraped_card_data
# - Merges data using priority rules
# - Deduplicates using fingerprinting
# - Uploads to cards table
# - Updates master_card_id link

# 3. Check results
python card_master_manager.py --stats
# Expected: found > 90, not_found < 10

# 4. Review duplicates (optional)
python monitor_duplicates.py --days 1
python review_duplicates.py
```

### Old Scraping Workflow (v1.0 - DEPRECATED)

```bash
# NOTE: This workflow is deprecated. Use v2.0 workflow above.
# Old scraper archived in: archive/enhanced_scraper.py.bak

# 1. Run old scraper (discovery-based)
python enhanced_scraper.py

# Problems with v1.0:
# - Discovers random cards from websites
# - No guarantee of finding all 106 cards
# - Results vary between runs
# - Harder to track missing cards
```

### Adding New Reward Program

```python
# 1. Edit reward_programs.py
REWARD_PROGRAMS['new_program'] = {
    'program_family': 'New Program',
    'program_name': 'New Program Name',
    'currency_type': 'flexible_points',
    'base_valuation': 1.5,
    'valuations': {
        'travel': 1.5,
        'statement': 1.0
    },
    'issuer_banks': ['Bank Name'],
    # ... other fields
}

# 2. Add patterns to program_matcher.py
PROGRAM_PATTERNS['new_program'] = {
    'patterns': [r'new program', r'bank.*new'],
    'exclude_patterns': [],
    'issuer_hints': ['Bank Name']
}

# 3. Reseed database
python seed_reward_programs.py --clear

# 4. Add tests
# Edit tests/test_reward_taxonomy.py

# 5. Run tests
python -m pytest tests/test_reward_taxonomy.py -v
```

### Database Migrations

```bash
# Apply migration
psql -U user -d db -f migrations/00X_migration_name.sql

# Rollback if needed
psql -U user -d db -f migrations/00X_rollback_migration_name.sql
```

### Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Specific test file
python -m pytest tests/test_reward_taxonomy.py -v

# With coverage
python -m pytest tests/ -v --cov=. --cov-report=html

# Specific test class
python -m pytest tests/test_reward_taxonomy.py::TestProgramMatcher -v
```

---

## Environment Variables

Required in `.env`:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
```

**IMPORTANT**: Never commit `.env` file! It's in `.gitignore`.

---

## Key Design Decisions

### 1. Master-List Based vs Discovery-Based (v2.0 Change)
- **Why Changed**: Discovery-based scraping had inconsistent results (50-100 cards per run)
- **Old Approach**: Scrape all cards found on websites, deduplicate after
- **New Approach**: Start with canonical 106 cards in DB, search for each specifically
- **Benefits**: Guaranteed coverage, track missing cards, consistent results

### 2. Multi-Source Scraping with Priority Merging
- **Why**: Single sources are unreliable; multiple sources provide verification
- **How**: 5 sources with priority-based merging (CreditCardGenius > Ratehub > GreedyRates > NerdWallet > MoneySense)
- **Merge Strategy**: Best data from each source per field (annual_fee uses priority 1, category_rewards uses union)

### 3. Fuzzy Card Matching Algorithm
- **Why**: Card names vary across sources ("TD Aeroplan" vs "TD® Aeroplan® Visa Infinite*")
- **How**: Multi-factor similarity (40% exact + 30% Jaro-Winkler + 20% token overlap + 10% issuer)
- **Thresholds**: ≥85% auto-match, 70-84% manual review, <70% no match

### 4. Fingerprinting for Duplicates
- **Why**: Card names vary across sources
- **How**: Normalized fingerprint = hash(name + issuer + fee + program)

### 5. Reward Program Taxonomy
- **Why**: Generic "Points" is meaningless; need accurate valuations
- **How**: 15+ programs with multi-pattern matching and exclusion rules

### 6. Backward Compatibility
- **Why**: Existing code depends on legacy fields
- **How**: Keep `reward_program` and `reward_currency` alongside new taxonomy fields

### 7. Deduplication as Last Step (Not First)
- **Why**: Want to collect all data from all sources before deciding what's duplicate
- **How**: Store raw data first, merge by master_card_id, deduplicate at end of workflow

### 8. Test Coverage
- **Why**: Complex pattern matching and merging needs verification
- **How**: 44 taxonomy tests + new matcher/merger tests

---

## Testing Strategy

### Test Coverage Requirements

- **Reward Taxonomy**: 90%+ matching accuracy (44 tests)
- **Duplicate Prevention**: Edge cases, fuzzy matching, merging logic
- **Scraper**: Mock responses, data extraction, validation

### Running Tests Locally

```bash
# Quick test (specific file)
python -m pytest tests/test_reward_taxonomy.py -v

# Full test suite
python -m pytest tests/ -v --cov=.

# Test a specific function
python -m pytest tests/test_reward_taxonomy.py::TestProgramMatcher::test_match_aeroplan_td -v
```

---

## Database Queries (Examples)

```sql
-- Get all Aeroplan cards
SELECT name, annual_fee, currency_type
FROM cards
WHERE reward_program_family = 'Aeroplan';

-- Find high-value flexible points cards
SELECT c.name, rp.program_name, rp.base_valuation
FROM cards c
JOIN reward_programs rp ON c.reward_program_id = rp.id
WHERE rp.currency_type = 'flexible_points'
  AND rp.base_valuation >= 1.5
ORDER BY rp.base_valuation DESC;

-- Get duplicate detection activity
SELECT
    DATE(created_at) as date,
    COUNT(*) as detections,
    SUM(CASE WHEN action_taken = 'merged' THEN 1 ELSE 0 END) as merged
FROM duplicate_detection_log
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at);

-- Find cards without taxonomy
SELECT name, issuer, reward_program
FROM cards
WHERE reward_program_id IS NULL
LIMIT 10;
```

---

## Troubleshooting

### Scraper Issues

**Problem**: Scraper returns 0 cards
- Check website structure hasn't changed
- Verify User-Agent is up to date
- Check rate limiting (increase delay)

**Problem**: Many cards marked as "Other" issuer
- Add issuer patterns to `_get_issuer()` in enhanced_scraper.py

### Taxonomy Issues

**Problem**: Cards not matching to programs
- Check confidence threshold (70%+)
- Add more patterns to `program_matcher.py`
- Verify issuer name normalization

**Problem**: False positive matches (e.g., Amex Aeroplan → Membership Rewards)
- Add exclusion patterns in `PROGRAM_PATTERNS`
- Check pattern order (most specific first)

### Database Issues

**Problem**: Foreign key violations
- Ensure `reward_programs` table is seeded first
- Run `python seed_reward_programs.py --clear`

**Problem**: Duplicate fingerprints
- Check fingerprint generation algorithm
- May need to adjust normalization rules

---

## Performance Optimization

### Scraping
- Default delay: 2 seconds between requests
- Batch size: Process 50 cards at a time
- Timeout: 15 seconds per request

### Duplicate Detection
- LRU cache: 1000 fingerprints with 15-minute TTL
- Batch mode: 50 cards in single query (~100ms)

### Database
- Indexes on: `fingerprint`, `reward_program_id`, `currency_type`, `program_family`
- Use batch inserts (50+ cards at once)

---

## Future Enhancements

### Planned Features
- [ ] French language support for card names
- [ ] API endpoint for querying cards
- [ ] Dashboard for monitoring scraper activity
- [ ] Automated scheduling (cron jobs)
- [ ] More reward programs (US cards, hotel programs)
- [ ] Enhanced category bonus detection

### Known Limitations
- Only supports Canadian credit cards
- Relies on website structure (may break if sites change)
- Limited to 5 data sources
- Manual review still needed for edge cases

---

## Git Workflow

```bash
# Check status
git status

# Stage changes
git add -A

# Commit (Claude can auto-generate commit messages)
git commit -m "feat: add new reward program XYZ"

# Push
git push origin main
```

**Commit Message Convention**:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `test:` Tests
- `refactor:` Code refactoring
- `chore:` Maintenance

---

## Important Notes for Claude

### Code Style
- Python 3.12+ features are available
- Use type hints where helpful
- Prefer dataclasses for structured data
- Follow existing logging patterns

### Testing
- Always run tests after changes: `python -m pytest tests/test_reward_taxonomy.py -v`
- Aim for 90%+ test coverage on new features
- Add tests BEFORE implementing new features

### Database Changes
- ALWAYS create rollback migration
- Test migrations on dev database first
- Update schema comments for clarity

### Documentation
- Update relevant docs in `docs/` folder
- Keep Claude.md up to date
- Add inline comments for complex logic

### Security
- NEVER commit `.env` file
- NEVER log Supabase credentials
- Validate all user input

---

## Quick Reference

### Most Used Commands (v2.0)
```bash
# Setup (one-time)
python card_master_manager.py --load docs/canadian_credit_cards.json --clear
python seed_reward_programs.py --clear

# Run scraper workflow
python scrape_workflow.py --limit 10   # Test
python scrape_workflow.py              # Full scrape

# Check status
python card_master_manager.py --stats
python card_master_manager.py --list

# Backfill cards
python backfill_card_programs.py --execute

# Run tests
python -m pytest tests/test_card_matcher.py -v
python -m pytest tests/test_data_merger.py -v
python -m pytest tests/test_reward_taxonomy.py -v

# Monitor duplicates
python monitor_duplicates.py --days 7
python review_duplicates.py
```

### Most Important Files (v2.0)
1. `scrape_workflow.py` - Main workflow orchestrator
2. `card_master_manager.py` - Master list management
3. `targeted_scraper.py` - Source-specific scrapers
4. `card_matcher.py` - Fuzzy card matching
5. `data_merger.py` - Multi-source merging
6. `credit_card_uploader.py` - Database upload
7. `program_matcher.py` - Reward program matching
8. `card_identity_manager.py` - Duplicate prevention
9. `reward_programs.py` - Program registry

### Old Files (Deprecated v1.0)
- `archive/enhanced_scraper.py.bak` - Old discovery-based scraper

---

## Project Status

**Last Major Update**: January 20, 2026 - Architecture v2.0

**Completed Features**:
- ✅ Master-list based scraping (v2.0)
- ✅ Multi-source scraper (5 sources) with priority merging
- ✅ Fuzzy card matching (85%+ threshold)
- ✅ Raw data storage per source
- ✅ Priority-based data merging
- ✅ Duplicate prevention system
- ✅ Reward program taxonomy (15+ programs)
- ✅ Database migrations (003, 004, 005)
- ✅ Comprehensive test suite (44+ tests)
- ✅ Monitoring and review tools

**Current State**: v2.0 implemented, ready for testing

**Test Results**:
- 44/44 reward taxonomy tests passing (100%)
- Card matcher tests created
- Data merger tests created

**Migration Path**:
1. Run migration 005_add_card_master_list.sql
2. Load master cards: `python card_master_manager.py --load docs/canadian_credit_cards.json --clear`
3. Test with: `python scrape_workflow.py --limit 5`
4. Full scrape: `python scrape_workflow.py`

---

**For questions or issues, refer to**:
- `docs/REWARD_TAXONOMY_STATUS.md` - Taxonomy implementation details
- `docs/TASK_DUPLICATE_PREVENTION.md` - Duplicate prevention guide
- `docs/IMPLEMENTATION_SUMMARY.md` - Overall project summary
