# Task: Duplicate Prevention System

**Status**: Not Started
**Priority**: High
**Estimated Effort**: 20 hours
**Assigned To**: TBD
**Created**: January 18, 2026

---

## Problem Statement

The current WebDataScraper system creates duplicate credit card entries in the database when different data sources format card names differently. The current `card_key` generation method in `enhanced_scraper.py` is too strict and doesn't account for common formatting variations.

### Current Duplication Issues

**Root Causes**:
1. **Weak Key Generation**: Keys based on exact name matching miss semantic duplicates
2. **Formatting Variations**: Different sources use ®, ™, asterisks, "Card" suffix inconsistently
3. **No Fuzzy Matching**: Slight differences create entirely new card entries
4. **Missing Database Constraints**: No fingerprinting or similarity checking

### Real-World Examples

| Source | Card Name | Generated Key | Problem |
|--------|-----------|---------------|---------|
| CreditCardGenius | "TD® Aeroplan® Visa Infinite*" | `td-td-aeroplan-visa-infinite` | Creates Card #1 |
| Ratehub | "TD Aeroplan Visa Infinite Card" | `td-td-aeroplan-visa-infinite-card` | Creates Card #2 (duplicate!) |
| NerdWallet | "TD Aeroplan Visa Infinite" | `td-td-aeroplan-visa-infinite` | Matches Card #1 |
| MoneySense | "TD® Aeroplan Visa® Infinite Card" | `td-td-aeroplan-visa-infinite-card` | Matches Card #2 |

**Result**: 2 database entries for the same card with keys differing only by "-card" suffix.

### Impact

- **Data Quality**: Users see duplicate cards in listings
- **Comparison Issues**: Same card appears multiple times in comparisons
- **Maintenance Burden**: Manual cleanup required
- **Storage Waste**: Redundant data in category_rewards and signup_bonuses tables
- **User Confusion**: Inconsistent annual fees or rewards across duplicates

---

## Solution Overview: Fingerprint Matching System

Implement a multi-layer duplicate detection system using normalized fingerprints, fuzzy matching, and automated merging.

### Key Features

1. **Fingerprint Generation**: Deterministic hash combining issuer + normalized name + program + fee bucket
2. **Name Normalization**: Strip formatting noise (®™, asterisks, "Card" suffix, etc.)
3. **Multi-Level Matching**: Exact → Fuzzy → Manual review
4. **Automatic Merging**: Combine duplicates with confidence scoring
5. **Database Enforcement**: UNIQUE constraint on fingerprints
6. **Audit Trail**: Log all duplicate detection and merge actions

---

## Technical Design

### 1. Fingerprint Generation Algorithm

**Purpose**: Create a unique, deterministic identifier that ignores formatting differences.

**Algorithm**:
```python
def generate_fingerprint(card: CreditCard) -> str:
    """
    Creates a fingerprint from normalized card attributes.

    Components:
    - Issuer (lowercased, trimmed)
    - Normalized name (special chars removed, "Card" suffix stripped)
    - Reward program (normalized)
    - Fee bucket (rounded to nearest $10)

    Returns: 16-character hex hash
    """
    # 1. Normalize name
    normalized_name = normalize_name(card.name)
    # "TD® Aeroplan® Visa Infinite*" → "td aeroplan visa infinite"

    # 2. Standardize issuer
    issuer = card.issuer.lower().strip()
    # "TD" → "td"

    # 3. Round fee to bucket
    fee_bucket = round(card.annual_fee / 10) * 10
    # $139.99 → 140

    # 4. Normalize program
    program = normalize_program(card.reward_program)
    # "Aeroplan®" → "aeroplan"

    # 5. Combine into string
    fingerprint_str = f"{issuer}|{normalized_name}|{program}|{fee_bucket}"
    # "td|td aeroplan visa infinite|aeroplan|140"

    # 6. Hash for consistency
    import hashlib
    return hashlib.sha256(fingerprint_str.encode()).hexdigest()[:16]
    # "a7f3c2e1b4d8f9a2"
```

### 2. Name Normalization Process

**Purpose**: Remove all formatting variations that don't affect card identity.

**Steps**:
```python
def normalize_name(name: str) -> str:
    """
    Removes formatting noise from card names.

    Transformations:
    1. Lowercase
    2. Remove trademark symbols (®™©℠)
    3. Remove marketing characters (*†‡§)
    4. Remove "Card" suffix
    5. Collapse multiple spaces
    6. Remove punctuation except spaces
    7. Strip and return
    """
    name = name.lower()
    name = re.sub(r'[®™©℠]', '', name)           # Trademarks
    name = re.sub(r'[*†‡§]', '', name)             # Asterisks
    name = re.sub(r'\s+card\s*$', '', name)        # "Card" suffix
    name = re.sub(r'\s+', ' ', name)               # Multiple spaces
    name = re.sub(r'[^\w\s]', '', name)            # Punctuation
    return name.strip()
```

**Examples**:
```python
normalize_name("TD® Aeroplan® Visa Infinite*")
# → "td aeroplan visa infinite"

normalize_name("American Express® Cobalt™ Card")
# → "american express cobalt"

normalize_name("BMO CashBack Mastercard®")
# → "bmo cashback mastercard"
```

### 3. Multi-Level Matching Strategy

**Tier 1: Exact Fingerprint Match (100% confidence)**
```python
# Check database for existing fingerprint
existing = db.query(
    "SELECT * FROM cards WHERE fingerprint = ?",
    fingerprint
)
if existing:
    # Definitely a duplicate
    return merge_cards(existing, new_card)
```

**Tier 2: Fuzzy Name Match (85-99% confidence)**
```python
# If no exact match, find similar cards
candidates = db.query("""
    SELECT * FROM cards
    WHERE issuer = ?
    AND reward_program = ?
    AND ABS(annual_fee - ?) < 20
""", issuer, program, fee)

for candidate in candidates:
    similarity = calculate_similarity(new_card.name, candidate.normalized_name)
    if similarity > 0.85:
        # Likely duplicate - auto-merge or flag
        return handle_fuzzy_match(candidate, new_card, similarity)
```

**Tier 3: Manual Review (70-85% confidence)**
```python
# Edge cases flagged for admin review
if 0.70 < similarity < 0.85:
    log_potential_duplicate(new_card, candidate, similarity)
    # Admin dashboard will show for manual decision
```

### 4. Similarity Calculation

**Algorithm**: Levenshtein distance + token set matching

```python
def calculate_similarity(name1: str, name2: str) -> float:
    """
    Multi-factor similarity score (0.0 to 1.0).

    Combines:
    - Edit distance similarity (60% weight)
    - Token set overlap (40% weight)
    """
    norm1 = normalize_name(name1)
    norm2 = normalize_name(name2)

    # Exact match
    if norm1 == norm2:
        return 1.0

    # Edit distance (Levenshtein ratio)
    from difflib import SequenceMatcher
    edit_similarity = SequenceMatcher(None, norm1, norm2).ratio()

    # Token set matching (order-independent)
    tokens1 = set(norm1.split())
    tokens2 = set(norm2.split())

    intersection = tokens1 & tokens2
    union = tokens1 | tokens2

    if len(union) == 0:
        return 0.0

    token_similarity = len(intersection) / len(union)

    # Weighted combination
    return (edit_similarity * 0.6) + (token_similarity * 0.4)
```

**Examples**:
```python
calculate_similarity(
    "TD Aeroplan Visa Infinite",
    "TD Aeroplan Visa Infinite Privilege"
)
# Edit: 0.86, Tokens: 4/5=0.80 → Score: 0.836

calculate_similarity(
    "American Express Cobalt",
    "Amex Cobalt Card"
)
# Edit: 0.65, Tokens: 2/4=0.50 → Score: 0.590 (below threshold)
```

### 5. Automatic Merge Logic

**Purpose**: Combine duplicate card data, keeping best information from each.

```python
def merge_cards(existing: CreditCard, new: CreditCard) -> CreditCard:
    """
    Intelligently merge two duplicate cards.

    Strategy:
    - Track all sources
    - Increase confidence score
    - Prefer non-null/non-zero values
    - Union category rewards
    - Keep most recent signup bonus
    """
    merged = existing.copy()

    # 1. Track sources
    existing_sources = existing.sources or []
    merged.sources = list(set(existing_sources + [new.source]))

    # 2. Increase confidence (max 1.0)
    merged.confidence = min(1.0, existing.confidence + 0.2)

    # 3. Prefer non-null image
    if new.image_url and not existing.image_url:
        merged.image_url = new.image_url

    # 4. Prefer non-zero annual fee
    if new.annual_fee > 0 and existing.annual_fee == 0:
        merged.annual_fee = new.annual_fee
    elif existing.annual_fee > 0 and new.annual_fee > 0:
        # Average if both present
        merged.annual_fee = (existing.annual_fee + new.annual_fee) / 2

    # 5. Merge category rewards (union by category)
    existing_cats = {cr.category: cr for cr in existing.category_rewards}
    for cr in new.category_rewards:
        if cr.category not in existing_cats:
            merged.category_rewards.append(cr)
        elif cr.multiplier > existing_cats[cr.category].multiplier:
            # Keep higher multiplier
            existing_cats[cr.category].multiplier = cr.multiplier

    # 6. Keep most recent signup bonus
    if new.signup_bonus and not existing.signup_bonus:
        merged.signup_bonus = new.signup_bonus

    # 7. Update last_verified timestamp
    merged.last_verified = datetime.now().isoformat()

    return merged
```

---

## Database Schema Changes

### New Columns on `cards` Table

```sql
-- Add normalized name for faster lookups
ALTER TABLE cards ADD COLUMN normalized_name TEXT;
CREATE INDEX idx_cards_normalized ON cards(issuer, normalized_name);

-- Add fingerprint with UNIQUE constraint
ALTER TABLE cards ADD COLUMN fingerprint TEXT;
CREATE UNIQUE INDEX idx_cards_fingerprint ON cards(fingerprint);

-- Add source tracking
ALTER TABLE cards ADD COLUMN sources TEXT[] DEFAULT '{}';

-- Add confidence score
ALTER TABLE cards ADD COLUMN confidence_score DECIMAL DEFAULT 0.5;
```

### New Table: `duplicate_detection_log`

```sql
CREATE TABLE duplicate_detection_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    card_key_1 TEXT NOT NULL,
    card_key_2 TEXT NOT NULL,
    fingerprint TEXT,
    similarity_score DECIMAL NOT NULL,
    action_taken TEXT NOT NULL, -- 'auto_merged', 'flagged', 'ignored'
    merged_into_id UUID REFERENCES cards(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB -- Additional context
);

CREATE INDEX idx_duplicate_log_created ON duplicate_detection_log(created_at DESC);
CREATE INDEX idx_duplicate_log_action ON duplicate_detection_log(action_taken);
```

### Migration Script

```sql
-- Migration: Add duplicate prevention columns
-- File: migrations/003_add_duplicate_prevention.sql

BEGIN;

-- Add new columns
ALTER TABLE cards ADD COLUMN IF NOT EXISTS normalized_name TEXT;
ALTER TABLE cards ADD COLUMN IF NOT EXISTS fingerprint TEXT;
ALTER TABLE cards ADD COLUMN IF NOT EXISTS sources TEXT[] DEFAULT '{}';
ALTER TABLE cards ADD COLUMN IF NOT EXISTS confidence_score DECIMAL DEFAULT 0.5;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_cards_normalized ON cards(issuer, normalized_name);
CREATE UNIQUE INDEX IF NOT EXISTS idx_cards_fingerprint ON cards(fingerprint);

-- Create log table
CREATE TABLE IF NOT EXISTS duplicate_detection_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    card_key_1 TEXT NOT NULL,
    card_key_2 TEXT NOT NULL,
    fingerprint TEXT,
    similarity_score DECIMAL NOT NULL,
    action_taken TEXT NOT NULL,
    merged_into_id UUID REFERENCES cards(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_duplicate_log_created ON duplicate_detection_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_duplicate_log_action ON duplicate_detection_log(action_taken);

COMMIT;
```

---

## Implementation Checklist

### Part 1: Core Module (`card_identity_manager.py`) - 8 hours

- [ ] Create `card_identity_manager.py` file
- [ ] Implement `CardIdentityManager` class
- [ ] Implement `normalize_name(name: str) -> str` method
  - [ ] Remove trademark symbols (®™©℠)
  - [ ] Remove marketing characters (*†‡§)
  - [ ] Remove "Card" suffix with regex
  - [ ] Collapse multiple spaces
  - [ ] Remove all punctuation except spaces
  - [ ] Handle edge cases (empty strings, Unicode)
- [ ] Implement `normalize_program(program: str) -> str` method
- [ ] Implement `generate_fingerprint(card: CreditCard) -> str` method
  - [ ] Normalize all components
  - [ ] Round fee to nearest $10
  - [ ] Combine into pipe-delimited string
  - [ ] Hash with SHA-256
  - [ ] Return first 16 characters
- [ ] Implement `calculate_similarity(name1: str, name2: str) -> float` method
  - [ ] Import difflib.SequenceMatcher
  - [ ] Calculate edit distance similarity
  - [ ] Calculate token set overlap
  - [ ] Return weighted combination
- [ ] Implement `find_potential_duplicates(card: CreditCard, threshold: float = 0.85) -> List[CreditCard]` method
  - [ ] Query database for candidates
  - [ ] Calculate similarity for each
  - [ ] Filter by threshold
  - [ ] Sort by similarity (descending)
- [ ] Add comprehensive docstrings
- [ ] Add type hints

### Part 2: Deduplication Script (`automated_deduplication.py`) - 4 hours

- [ ] Create `automated_deduplication.py` file
- [ ] Import CardIdentityManager
- [ ] Implement `scan_for_duplicates() -> List[Tuple[CreditCard, CreditCard, float]]` function
  - [ ] Fetch all active cards from database
  - [ ] For each card, check for duplicates
  - [ ] Return list of (card1, card2, similarity) tuples
- [ ] Implement `merge_duplicate_pair(card1: CreditCard, card2: CreditCard) -> CreditCard` function
  - [ ] Determine which card to keep (higher confidence)
  - [ ] Merge data using merge_cards() logic
  - [ ] Update database
  - [ ] Delete duplicate card (soft delete)
  - [ ] Log to duplicate_detection_log
- [ ] Implement `automated_cleanup(dry_run: bool = True, threshold: float = 0.90)` function
  - [ ] Scan for duplicates above threshold
  - [ ] Auto-merge if not dry_run
  - [ ] Generate summary report
  - [ ] Send email notification
- [ ] Add command-line interface
  - [ ] `--dry-run` flag
  - [ ] `--threshold` parameter
  - [ ] `--email` parameter for notifications
- [ ] Add logging with logger_config

### Part 3: Update Scraper (`enhanced_scraper.py`) - 3 hours

- [ ] Import CardIdentityManager
- [ ] Update `_add_or_merge_card()` method
  - [ ] Generate fingerprint for new card
  - [ ] Check database for exact fingerprint match
  - [ ] If match found, merge using merge_cards()
  - [ ] If no match, check for fuzzy matches
  - [ ] If fuzzy match >0.85, merge
  - [ ] If fuzzy match 0.70-0.85, log for manual review
  - [ ] If no match, insert new card
- [ ] Update CreditCard dataclass
  - [ ] Add normalized_name field
  - [ ] Add fingerprint field
  - [ ] Add sources field (List[str])
  - [ ] Add confidence_score field (default 0.5)
- [ ] Update `_create_card_from_name()` method
  - [ ] Calculate normalized_name
  - [ ] Generate fingerprint
  - [ ] Set initial source
  - [ ] Set initial confidence score
- [ ] Add source tracking to all scraper methods

### Part 4: Update Uploader (`credit_card_uploader.py`) - 2 hours

- [ ] Update `_upsert_card()` method
  - [ ] Include normalized_name in card_data
  - [ ] Include fingerprint in card_data
  - [ ] Include sources array in card_data
  - [ ] Include confidence_score in card_data
- [ ] Add fingerprint-based upsert logic
  - [ ] Check for existing card by fingerprint (not just card_key)
  - [ ] Merge if fingerprint exists
  - [ ] Create new if fingerprint doesn't exist
- [ ] Handle unique constraint violations
  - [ ] Catch duplicate fingerprint errors
  - [ ] Merge automatically
  - [ ] Log to duplicate_detection_log

### Part 5: Database Migration - 1 hour

- [ ] Create `migrations/003_add_duplicate_prevention.sql`
- [ ] Run migration on dev database
- [ ] Backfill existing cards
  - [ ] Calculate normalized_name for all cards
  - [ ] Generate fingerprints for all cards
  - [ ] Set sources from 'source' field
  - [ ] Set initial confidence_score
- [ ] Verify no duplicate fingerprints after migration
- [ ] Handle any conflicts manually

### Part 6: Testing - 6 hours

#### Unit Tests (`tests/test_card_identity_manager.py`)

- [ ] Test normalize_name()
  - [ ] Basic normalization
  - [ ] Trademark symbols removal
  - [ ] "Card" suffix removal
  - [ ] Multiple spaces collapsing
  - [ ] Punctuation removal
  - [ ] Edge cases (empty, Unicode, all caps)
- [ ] Test generate_fingerprint()
  - [ ] Same card, different formatting → same fingerprint
  - [ ] Different cards → different fingerprints
  - [ ] Fee variation ($139 vs $139.99) → same fingerprint
  - [ ] Deterministic (same input → same output)
- [ ] Test calculate_similarity()
  - [ ] Exact matches → 1.0
  - [ ] Minor variations → >0.85
  - [ ] Different cards → <0.70
  - [ ] Edge cases (empty strings, single words)

#### Integration Tests (`tests/test_duplicate_prevention.py`)

- [ ] Test end-to-end duplicate detection
  - [ ] Scrape same card from 2 sources
  - [ ] Verify only 1 card in database
  - [ ] Verify sources array contains both sources
  - [ ] Verify confidence_score increased
- [ ] Test automated_deduplication script
  - [ ] Insert known duplicates
  - [ ] Run cleanup script
  - [ ] Verify duplicates merged
  - [ ] Verify log entries created
- [ ] Test fuzzy matching threshold
  - [ ] Cards with 0.90+ similarity auto-merge
  - [ ] Cards with 0.70-0.85 similarity flagged
  - [ ] Cards with <0.70 similarity ignored

#### Performance Tests

- [ ] Test fingerprint generation speed
  - [ ] Target: <5ms per card
  - [ ] Benchmark with 1000 cards
- [ ] Test similarity calculation speed
  - [ ] Target: <10ms per comparison
  - [ ] Benchmark with 1000 comparisons
- [ ] Test duplicate scan on large dataset
  - [ ] Create 1000 card test database
  - [ ] Run full scan
  - [ ] Target: <10 seconds total

---

## Success Criteria

### Functional Requirements

1. **Zero Duplicates**: No semantic duplicates in production database
2. **High Accuracy**: 95%+ correct duplicate detection (measured against manual review)
3. **Fast Performance**: <100ms for duplicate check during scraping
4. **Audit Trail**: All merge actions logged to duplicate_detection_log
5. **Reversibility**: Ability to unmerge incorrectly merged cards

### Quality Metrics

1. **Code Coverage**: 90%+ test coverage for card_identity_manager.py
2. **No False Positives**: <5% incorrect merges (different cards merged)
3. **No False Negatives**: <5% missed duplicates (same cards not merged)
4. **Database Integrity**: UNIQUE constraint prevents accidental duplicates

### User Experience

1. **Transparency**: Admin dashboard shows merge history
2. **Manual Override**: Ability to flag cards as "not duplicates"
3. **Notifications**: Email alerts for low-confidence matches requiring review

---

## Testing Strategy

### Phase 1: Unit Testing (2 hours)
- Test all normalization functions
- Test fingerprint generation
- Test similarity calculation
- Achieve 90%+ code coverage

### Phase 2: Integration Testing (2 hours)
- Test with real scraped data
- Test with known duplicate scenarios
- Test with edge cases

### Phase 3: Performance Testing (1 hour)
- Benchmark fingerprint generation
- Benchmark similarity calculation
- Benchmark full duplicate scan

### Phase 4: User Acceptance Testing (1 hour)
- Manual review of merge results
- Verify admin dashboard displays correctly
- Test unmerge functionality

---

## Rollout Plan

### Phase 1: Development (Week 1)
- Implement core modules
- Write unit tests
- Database migration

### Phase 2: Testing (Week 2)
- Integration testing
- Performance testing
- Fix bugs

### Phase 3: Backfill (Week 3)
- Run on production data (dry-run)
- Review results
- Fix edge cases
- Run actual backfill

### Phase 4: Monitoring (Week 4)
- Deploy to production
- Monitor duplicate logs
- Email daily reports
- Iterate on threshold tuning

---

## Maintenance

### Daily Tasks
- Review duplicate_detection_log for flagged matches
- Approve or reject low-confidence merges

### Weekly Tasks
- Run duplicate scan report
- Monitor false positive/negative rates
- Adjust similarity thresholds if needed

### Monthly Tasks
- Audit merge accuracy
- Update normalization rules for new patterns
- Review and clean up duplicate_detection_log

---

## Related Documentation

- [PROJECT_ANALYSIS.md](../PROJECT_ANALYSIS.md) - Full project analysis
- [TASK_REWARD_TAXONOMY.md](./TASK_REWARD_TAXONOMY.md) - Reward program taxonomy task
- [README.md](../README.md) - Project overview

---

**Last Updated**: January 18, 2026
**Document Version**: 1.0
