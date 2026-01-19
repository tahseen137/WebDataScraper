# WebDataScraper - Claude Context

**Project**: Canadian Credit Card Data Scraper and Database Manager
**Language**: Python 3.12
**Database**: Supabase (PostgreSQL)
**Last Updated**: January 18, 2026

---

## Project Overview

WebDataScraper is a comprehensive system for scraping, managing, and analyzing Canadian credit card data. The system includes:

- **Web Scraping**: Multi-source scraping from 5+ Canadian credit card websites
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
│   └── 004_rollback_reward_taxonomy.sql
├── tests/                         # Test suite
│   ├── test_reward_taxonomy.py    # 44 tests for reward taxonomy
│   ├── test_duplicate_prevention.py
│   └── test_scraper.py
├── Core Scripts
│   ├── enhanced_scraper.py        # Main scraper (5 sources)
│   ├── credit_card_uploader.py    # Database upload
│   ├── card_identity_manager.py   # Duplicate prevention
│   ├── program_matcher.py         # Reward program matching
│   └── reward_programs.py         # 15+ program registry
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

### 1. Enhanced Scraper (`enhanced_scraper.py`)

Multi-source Canadian credit card scraper with:
- 5 data sources: CreditCardGenius, Ratehub, MoneySense, NerdWallet, GreedyRates
- Smart reward program matching (70%+ confidence)
- Category reward extraction
- Data verification and validation
- Automatic deduplication

**Usage**:
```bash
python enhanced_scraper.py
```

**Key Features**:
- Scrapes ~50-100+ unique cards
- Extracts annual fees, reward rates, category bonuses
- Uses reward taxonomy for accurate program classification
- Confidence scoring (0.0-1.0)

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

#### `cards`
Primary card data with taxonomy fields:
- Core: `id`, `card_key`, `name`, `issuer`, `annual_fee`
- Legacy: `reward_program`, `reward_currency`, `point_valuation`
- Taxonomy: `reward_program_id`, `reward_program_family`, `currency_type`
- Duplicate Prevention: `fingerprint`, `sources`, `data_quality_score`

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

# Configure credentials
cp .env.example .env
# Edit .env with your Supabase credentials

# Run migrations
psql -U your_user -d your_db -f migrations/003_add_duplicate_prevention.sql
psql -U your_user -d your_db -f migrations/004_add_reward_taxonomy.sql

# Seed reward programs
python seed_reward_programs.py --clear

# Verify setup
python -m pytest tests/ -v
```

### Scraping Workflow

```bash
# 1. Run scraper
python enhanced_scraper.py

# Output:
# - Scrapes from 5 sources
# - Deduplicates automatically
# - Matches to reward programs
# - Uploads to Supabase
# - Saves to scraped_cards.json

# 2. Review results
python monitor_duplicates.py --days 1

# 3. Manual review if needed
python review_duplicates.py
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

### 1. Multi-Source Scraping
- **Why**: Single sources are unreliable; multiple sources provide verification
- **How**: 5 sources with confidence scoring and merging

### 2. Fingerprinting for Duplicates
- **Why**: Card names vary across sources ("TD Aeroplan Visa" vs "TD Aeroplan Visa Infinite")
- **How**: Normalized fingerprint = hash(name + issuer + fee + program)

### 3. Reward Program Taxonomy
- **Why**: Generic "Points" is meaningless; need accurate valuations
- **How**: 15+ programs with multi-pattern matching and exclusion rules

### 4. Backward Compatibility
- **Why**: Existing code depends on legacy fields
- **How**: Keep `reward_program` and `reward_currency` alongside new taxonomy fields

### 5. Test Coverage
- **Why**: Complex pattern matching needs verification
- **How**: 44 tests for taxonomy, comprehensive duplicate prevention tests

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

### Most Used Commands
```bash
# Run scraper
python enhanced_scraper.py

# Seed programs
python seed_reward_programs.py --clear

# Backfill cards
python backfill_card_programs.py --execute

# Run tests
python -m pytest tests/test_reward_taxonomy.py -v

# Monitor duplicates
python monitor_duplicates.py --days 7

# Review duplicates
python review_duplicates.py
```

### Most Important Files
1. `enhanced_scraper.py` - Main scraper
2. `program_matcher.py` - Reward program matching
3. `card_identity_manager.py` - Duplicate prevention
4. `reward_programs.py` - Program registry
5. `credit_card_uploader.py` - Database upload

---

## Project Status

**Last Major Update**: January 18, 2026

**Completed Features**:
- ✅ Multi-source scraper (5 sources)
- ✅ Duplicate prevention system
- ✅ Reward program taxonomy (15+ programs)
- ✅ Database migrations and seeding
- ✅ Comprehensive test suite (44 tests)
- ✅ Monitoring and review tools

**Current State**: Production-ready, fully tested, all tests passing

**Test Results**: 44/44 reward taxonomy tests passing (100%)

---

**For questions or issues, refer to**:
- `docs/REWARD_TAXONOMY_STATUS.md` - Taxonomy implementation details
- `docs/TASK_DUPLICATE_PREVENTION.md` - Duplicate prevention guide
- `docs/IMPLEMENTATION_SUMMARY.md` - Overall project summary
