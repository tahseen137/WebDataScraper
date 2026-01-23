# Task: Reward Program Taxonomy System

**Status**: Not Started
**Priority**: High
**Estimated Effort**: 16 hours
**Assigned To**: TBD
**Created**: January 18, 2026

---

## Problem Statement

The current WebDataScraper system uses ambiguous and inconsistent naming for credit card reward programs. Many cards default to generic "Points" when the specific program isn't recognized, making it difficult for users to understand the true value and nature of rewards.

### Current Issues

**1. Generic "Points" Fallback**
The `_get_program()` method in `enhanced_scraper.py:227-244` defaults to "Points" when it can't identify a specific program:

```python
def _get_program(self, name: str) -> str:
    programs = {
        'Aeroplan': ['aeroplan'],
        'Scene+': ['scene'],
        # ... other programs
    }
    # ...
    return "Points"  # ⚠️ Too generic!
```

**Impact**: Users can't distinguish between:
- TD Rewards Points (0.5¢ value)
- BMO Rewards Points (0.7¢ value)
- Membership Rewards Points (2.0¢ value)
- PC Optimum Points (0.1¢ value)

**2. Mixed Currency Types**
No clear distinction between:
- **Airline miles** (Aeroplan, Air Miles, Avion)
- **Flexible points** (Membership Rewards, Aventura)
- **Retail points** (PC Optimum, Triangle Rewards)
- **Entertainment points** (Scene+)
- **Cashback** (straight cash)

**3. Inconsistent Point Valuations**
The `_get_point_value()` method has hardcoded values but doesn't account for:
- Redemption type variations (travel vs statement vs merchandise)
- Transfer partner bonuses
- Tier differences (regular vs elite status)

**4. No Program Hierarchy**
Missing structure for:
- Program families (e.g., "Membership Rewards")
- Program tiers (e.g., "Select" vs "Premium")
- Regional variants

### Real-World Examples

| Card | Current Program | Should Be | Valuation |
|------|----------------|-----------|-----------|
| TD First Class Travel | "TD Rewards" ✅ | "TD Rewards" | 0.5¢ ✅ |
| CIBC Aventura | "Aventura" ✅ | "Aventura" | 1.0¢ ✅ |
| RBC Avion | "Avion" ✅ | "Avion" | 1.5¢ ✅ |
| BMO Eclipse | "BMO Rewards" ✅ | "BMO Rewards" | 0.7¢ ✅ |
| Unknown Card | "Points" ❌ | [Specific Program] | Varies |

---

## Solution Overview: Clear Reward Program Taxonomy

Implement a comprehensive, hierarchical taxonomy for all Canadian credit card reward programs with accurate valuations and clear categorization.

### Key Features

1. **Program Registry**: Complete database of 15+ Canadian reward programs
2. **Clear Hierarchy**: Program Family → Program Name → Currency Type → Valuation
3. **Multiple Valuations**: By redemption type (travel, statement, merchandise)
4. **Enhanced Detection**: Multi-pattern matching for accurate program identification
5. **Database Schema**: Separate reward_programs reference table
6. **Migration Tools**: Backfill existing cards with correct programs

---

## Proposed Program Hierarchy

### Structure

```
Program Family
  ├── Program Name
  │   ├── Currency Type
  │   ├── Base Valuation (cents per point)
  │   ├── Transfer Partners
  │   └── Redemption Options
```

### Examples

**Example 1: Aeroplan**
```
Program Family: Aeroplan
Program Name: Aeroplan (no tiers)
Currency Type: airline_miles
Base Valuation: 1.8¢ per mile (travel redemption)
Transfer Partners: Air Canada, Star Alliance
Redemption Options: Flights, upgrades, merchandise
```

**Example 2: Membership Rewards**
```
Program Family: Membership Rewards
Program Name: Membership Rewards
Currency Type: flexible_points
Base Valuation: 2.0¢ per point (travel transfer)
Transfer Partners: Marriott, British Airways, Aeroplan
Redemption Options: Travel, statement, merchandise, transfers
```

**Example 3: Scene+**
```
Program Family: Scene+
Program Name: Scene+
Currency Type: entertainment_points
Base Valuation: 1.0¢ per point (entertainment)
Transfer Partners: Cineplex, grocery stores, gas stations
Redemption Options: Movies, dining, groceries, travel
```

---

## Complete Canadian Reward Program Registry

### Airline Miles Programs

| Program Family | Program Name | Currency Type | Base Valuation | Issuers |
|---------------|--------------|---------------|----------------|---------|
| Aeroplan | Aeroplan | airline_miles | 1.8¢ | TD, CIBC, Amex |
| Air Miles | AIR MILES | airline_miles | 0.1¢ | BMO, Amex |
| WestJet Rewards | WestJet Dollars | airline_miles | 1.5¢ | RBC, WestJet |

### Flexible Points Programs

| Program Family | Program Name | Currency Type | Base Valuation | Issuers |
|---------------|--------------|---------------|----------------|---------|
| Membership Rewards | Membership Rewards | flexible_points | 2.0¢ | American Express |
| Avion | Avion Rewards | flexible_points | 1.5¢ | RBC |
| Aventura | Aventura Rewards | flexible_points | 1.0¢ | CIBC |

### Retail Points Programs

| Program Family | Program Name | Currency Type | Base Valuation | Issuers |
|---------------|--------------|---------------|----------------|---------|
| TD Rewards | TD Rewards | retail_points | 0.5¢ | TD |
| BMO Rewards | BMO Rewards | retail_points | 0.7¢ | BMO |
| PC Optimum | PC Optimum | retail_points | 0.1¢ | PC Financial |
| Triangle Rewards | Triangle Rewards | retail_points | 0.1¢ | Canadian Tire |
| MBNA Rewards | MBNA Rewards | retail_points | 1.0¢ | MBNA |

### Entertainment Points Programs

| Program Family | Program Name | Currency Type | Base Valuation | Issuers |
|---------------|--------------|---------------|----------------|---------|
| Scene+ | Scene+ | entertainment_points | 1.0¢ | Scotiabank |

### Travel Points Programs

| Program Family | Program Name | Currency Type | Base Valuation | Issuers |
|---------------|--------------|---------------|----------------|---------|
| Odyssey | Odyssey Rewards | travel_points | 1.0¢ | Desjardins |

### Cashback Programs

| Program Family | Program Name | Currency Type | Base Valuation | Issuers |
|---------------|--------------|---------------|----------------|---------|
| Cash Back | Straight Cash | cashback | 1.0¢ | All banks |

---

## Currency Type Definitions

### 1. `cashback`
- **Description**: Direct cash value, deposited to account or statement credit
- **Valuation**: Always 1.0¢ per dollar
- **Flexibility**: Highest (can use anywhere)
- **Transfer**: Not applicable
- **Examples**: TD Cash Back, Tangerine Money-Back

### 2. `airline_miles`
- **Description**: Miles redeemable for flights, upgrades, or airline-specific rewards
- **Valuation**: 0.1¢ - 2.1¢ per mile (varies by program)
- **Flexibility**: Low (airline-specific)
- **Transfer**: Often to Star Alliance or partner airlines
- **Examples**: Aeroplan, Air Miles, WestJet Rewards

### 3. `flexible_points`
- **Description**: Points transferable to multiple partners or redeemable for various rewards
- **Valuation**: 1.0¢ - 2.0¢ per point
- **Flexibility**: High (multiple redemption options)
- **Transfer**: Yes, to airlines, hotels, or other programs
- **Examples**: Membership Rewards, Avion, Aventura

### 4. `retail_points`
- **Description**: Points redeemable for merchandise, statement credit, or bank-specific rewards
- **Valuation**: 0.1¢ - 1.0¢ per point
- **Flexibility**: Medium (limited to issuer ecosystem)
- **Transfer**: No
- **Examples**: TD Rewards, BMO Rewards, PC Optimum

### 5. `entertainment_points`
- **Description**: Points for movies, dining, groceries, and entertainment
- **Valuation**: 0.8¢ - 1.0¢ per point
- **Flexibility**: Medium (entertainment-focused)
- **Transfer**: Limited
- **Examples**: Scene+

### 6. `hotel_points`
- **Description**: Points for hotel stays and hotel-specific rewards
- **Valuation**: 0.5¢ - 0.8¢ per point
- **Flexibility**: Low (hotel-specific)
- **Transfer**: Sometimes to airlines
- **Examples**: Marriott Bonvoy (if added in future)

---

## Database Schema Changes

### New Table: `reward_programs`

```sql
CREATE TABLE reward_programs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    program_family TEXT NOT NULL,
    program_name TEXT UNIQUE NOT NULL,
    currency_type TEXT NOT NULL, -- cashback, airline_miles, flexible_points, etc.
    base_valuation DECIMAL NOT NULL, -- cents per point/mile
    transfer_partners JSONB, -- ["Aeroplan", "Marriott", "British Airways"]
    redemption_options JSONB, -- ["travel", "statement", "merchandise"]
    issuer_banks TEXT[], -- ["American Express", "TD"]
    notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_reward_programs_currency ON reward_programs(currency_type);
CREATE INDEX idx_reward_programs_family ON reward_programs(program_family);
```

### Update `cards` Table

```sql
-- Add new columns
ALTER TABLE cards ADD COLUMN reward_program_family TEXT;
ALTER TABLE cards ADD COLUMN reward_program_id UUID REFERENCES reward_programs(id);

-- Keep existing reward_program column for backward compatibility
-- It will be deprecated after migration

-- Create index
CREATE INDEX idx_cards_program_family ON cards(reward_program_family);
CREATE INDEX idx_cards_program_id ON cards(reward_program_id);
```

### New Table: `point_valuations`

```sql
-- For redemption-specific valuations
CREATE TABLE point_valuations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    program_id UUID REFERENCES reward_programs(id),
    redemption_type TEXT NOT NULL, -- 'travel', 'statement', 'merchandise', 'transfer'
    cents_per_point DECIMAL NOT NULL,
    minimum_redemption INTEGER, -- Minimum points required
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_valuations_program ON point_valuations(program_id);
CREATE INDEX idx_valuations_type ON point_valuations(redemption_type);
```

### Migration Script

```sql
-- Migration: Create reward program taxonomy
-- File: migrations/004_add_reward_taxonomy.sql

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
    notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_reward_programs_currency ON reward_programs(currency_type);
CREATE INDEX idx_reward_programs_family ON reward_programs(program_family);

-- Add columns to cards table
ALTER TABLE cards ADD COLUMN IF NOT EXISTS reward_program_family TEXT;
ALTER TABLE cards ADD COLUMN IF NOT EXISTS reward_program_id UUID REFERENCES reward_programs(id);

CREATE INDEX IF NOT EXISTS idx_cards_program_family ON cards(reward_program_family);
CREATE INDEX IF NOT EXISTS idx_cards_program_id ON cards(reward_program_id);

-- Create point valuations table
CREATE TABLE IF NOT EXISTS point_valuations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    program_id UUID REFERENCES reward_programs(id),
    redemption_type TEXT NOT NULL,
    cents_per_point DECIMAL NOT NULL,
    minimum_redemption INTEGER,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_valuations_program ON point_valuations(program_id);
CREATE INDEX IF NOT EXISTS idx_valuations_type ON point_valuations(redemption_type);

COMMIT;
```

---

## Implementation Checklist

### Part 1: Create Reward Program Registry (`reward_programs.py`) - 4 hours

- [ ] Create `reward_programs.py` file
- [ ] Define REWARD_PROGRAMS constant dictionary
  - [ ] Aeroplan program details
  - [ ] Membership Rewards program details
  - [ ] Scene+ program details
  - [ ] Avion program details
  - [ ] Aventura program details
  - [ ] TD Rewards program details
  - [ ] BMO Rewards program details
  - [ ] PC Optimum program details
  - [ ] Triangle Rewards program details
  - [ ] MBNA Rewards program details
  - [ ] WestJet Rewards program details
  - [ ] Air Miles program details
  - [ ] Odyssey program details
  - [ ] Cash Back program details
- [ ] Define CURRENCY_TYPES constant
  - [ ] cashback
  - [ ] airline_miles
  - [ ] flexible_points
  - [ ] retail_points
  - [ ] entertainment_points
  - [ ] hotel_points
- [ ] Implement `get_program_by_name(name: str) -> Dict` function
- [ ] Implement `get_program_by_family(family: str) -> List[Dict]` function
- [ ] Implement `get_programs_by_currency(currency_type: str) -> List[Dict]` function
- [ ] Implement `detect_program_from_card_name(card_name: str, issuer: str) -> Dict` function
  - [ ] Enhanced pattern matching
  - [ ] Multi-keyword detection
  - [ ] Issuer-specific logic
  - [ ] Confidence scoring
- [ ] Implement `get_valuation(program_name: str, redemption_type: str = 'travel') -> float` function
- [ ] Add comprehensive docstrings
- [ ] Add type hints

### Part 2: Update Scraper (`enhanced_scraper.py`) - 3 hours

- [ ] Import reward_programs module
- [ ] Replace `_get_program()` method with enhanced version
  - [ ] Call detect_program_from_card_name()
  - [ ] Use issuer context for better detection
  - [ ] Return program family and name
  - [ ] Set confidence score
- [ ] Update `_get_currency()` method
  - [ ] Use currency_type from reward program
  - [ ] Remove hardcoded logic
- [ ] Update `_get_point_value()` method
  - [ ] Look up from reward_programs.REWARD_PROGRAMS
  - [ ] Use get_valuation() function
  - [ ] Support redemption type parameter
- [ ] Update CreditCard dataclass
  - [ ] Add reward_program_family field
  - [ ] Add reward_program_id field (optional UUID)
- [ ] Update `_create_card_from_name()` method
  - [ ] Detect program using new function
  - [ ] Set program_family
  - [ ] Set currency_type from program
  - [ ] Set valuation from program
- [ ] Add fallback logic
  - [ ] If program not detected, log warning
  - [ ] Don't default to "Points"
  - [ ] Flag for manual review

### Part 3: Seed Programs to Database (`seed_reward_programs.py`) - 2 hours

- [ ] Create `seed_reward_programs.py` script
- [ ] Import reward_programs module
- [ ] Implement `seed_programs()` function
  - [ ] Connect to Supabase
  - [ ] Insert all programs from REWARD_PROGRAMS
  - [ ] Handle duplicates (upsert)
  - [ ] Insert point valuations for each program
- [ ] Implement `verify_programs()` function
  - [ ] Check all programs inserted
  - [ ] Verify valuations correct
  - [ ] Print summary
- [ ] Add command-line interface
- [ ] Add logging

### Part 4: Migration Script (`migrate_reward_programs.py`) - 3 hours

- [ ] Create `migrate_reward_programs.py` script
- [ ] Implement `backfill_cards()` function
  - [ ] Fetch all cards from database
  - [ ] For each card, detect reward program
  - [ ] Update reward_program_family
  - [ ] Update reward_program_id (FK to reward_programs)
  - [ ] Log successes and failures
- [ ] Implement `validate_migration()` function
  - [ ] Count cards with program_family set
  - [ ] Count cards still with generic "Points"
  - [ ] Print validation report
- [ ] Implement `manual_review_report()` function
  - [ ] List cards that couldn't be auto-classified
  - [ ] Show card name, issuer, current program
  - [ ] Export to CSV for manual review
- [ ] Add dry-run mode
- [ ] Add rollback functionality
- [ ] Add logging with logger_config

### Part 5: Update Uploader (`credit_card_uploader.py`) - 2 hours

- [ ] Update `_upsert_card()` method
  - [ ] Include reward_program_family in card_data
  - [ ] Include reward_program_id in card_data
  - [ ] Validate program_id exists in reward_programs table
- [ ] Add `get_program_id_by_name(program_name: str) -> UUID` helper
  - [ ] Query reward_programs table
  - [ ] Return UUID
  - [ ] Cache results
- [ ] Update data/curated_cards.json
  - [ ] Map each card's reward_program to program_id
  - [ ] Include reward_program_family
  - [ ] Verify against reward_programs table

### Part 6: Testing - 4 hours

#### Unit Tests (`tests/test_reward_programs.py`)

- [ ] Test get_program_by_name()
  - [ ] Valid program names
  - [ ] Case insensitivity
  - [ ] Invalid names return None
- [ ] Test detect_program_from_card_name()
  - [ ] "TD Aeroplan Visa Infinite" → Aeroplan
  - [ ] "American Express Cobalt" → Membership Rewards
  - [ ] "Scotiabank Gold Amex" → Scene+
  - [ ] "Tangerine Money-Back" → Cash Back
  - [ ] Ambiguous names handled correctly
- [ ] Test get_valuation()
  - [ ] Correct valuations returned
  - [ ] Redemption type variations
  - [ ] Invalid programs handled
- [ ] Test currency type mapping
  - [ ] All programs have valid currency_type
  - [ ] Currency types match constants

#### Integration Tests (`tests/test_migration.py`)

- [ ] Test seed_reward_programs.py
  - [ ] All 15+ programs inserted
  - [ ] No duplicate program names
  - [ ] All have valid currency_type
  - [ ] Valuations within reasonable range
- [ ] Test migrate_reward_programs.py
  - [ ] All 34 seed cards migrated successfully
  - [ ] No generic "Points" after migration
  - [ ] All cards have program_family
  - [ ] All cards have valid program_id FK
- [ ] Test scraper with new logic
  - [ ] Scrape known cards
  - [ ] Verify correct programs detected
  - [ ] Verify correct valuations assigned

#### Validation Tests

- [ ] Cross-reference with data/curated_cards.json
  - [ ] All 34 cards have matching programs
  - [ ] Valuations match manual data
- [ ] Verify against official bank websites
  - [ ] Sample 10 cards
  - [ ] Confirm program names correct
  - [ ] Confirm valuations within 10% of reality

---

## Enhanced Program Detection Logic

### Multi-Pattern Matching

```python
def detect_program_from_card_name(card_name: str, issuer: str) -> Dict:
    """
    Detect reward program using multiple patterns and issuer context.

    Returns program details or None if not detected.
    """
    name_lower = card_name.lower()
    issuer_lower = issuer.lower()

    # Priority 1: Explicit program names in card name
    if 'aeroplan' in name_lower:
        return REWARD_PROGRAMS['aeroplan']
    if 'scene' in name_lower or 'scene+' in name_lower:
        return REWARD_PROGRAMS['scene_plus']
    if 'cobalt' in name_lower or ('gold' in name_lower and issuer_lower == 'american express'):
        return REWARD_PROGRAMS['membership_rewards']
    if 'avion' in name_lower:
        return REWARD_PROGRAMS['avion']
    if 'aventura' in name_lower:
        return REWARD_PROGRAMS['aventura']
    if 'westjet' in name_lower:
        return REWARD_PROGRAMS['westjet_rewards']
    if 'air miles' in name_lower:
        return REWARD_PROGRAMS['air_miles']
    if 'odyssey' in name_lower:
        return REWARD_PROGRAMS['odyssey']

    # Priority 2: Card name + issuer patterns
    if 'first class' in name_lower and issuer_lower == 'td':
        return REWARD_PROGRAMS['td_rewards']
    if 'eclipse' in name_lower and issuer_lower == 'bmo':
        return REWARD_PROGRAMS['bmo_rewards']
    if 'pc' in issuer_lower or 'pc financial' in name_lower:
        return REWARD_PROGRAMS['pc_optimum']
    if 'triangle' in name_lower or 'canadian tire' in issuer_lower:
        return REWARD_PROGRAMS['triangle_rewards']

    # Priority 3: Cashback keywords
    if 'cash back' in name_lower or 'cashback' in name_lower or 'dividend' in name_lower:
        return REWARD_PROGRAMS['cash_back']

    # Priority 4: Issuer defaults (last resort)
    issuer_defaults = {
        'td': 'td_rewards',
        'bmo': 'bmo_rewards',
        'cibc': None,  # CIBC has multiple programs
        'scotiabank': 'scene_plus',
        'rbc': None,  # RBC has multiple programs
        'american express': 'membership_rewards',
        'mbna': 'mbna_rewards',
        'tangerine': 'cash_back',
        'simplii': 'cash_back',
    }

    default_program = issuer_defaults.get(issuer_lower)
    if default_program:
        logger.warning(f"Using issuer default for {card_name}: {default_program}")
        return REWARD_PROGRAMS[default_program]

    # Not detected
    logger.error(f"Could not detect reward program for: {card_name} ({issuer})")
    return None
```

---

## Success Criteria

### Functional Requirements

1. **No Generic "Points"**: 100% of cards have specific program names
2. **Accurate Valuations**: Point valuations within 10% of market rates
3. **Clear Hierarchy**: All programs have family, name, and currency type
4. **Complete Registry**: All 15+ Canadian programs documented
5. **Backward Compatibility**: Old reward_program column still works during transition

### Quality Metrics

1. **Coverage**: 100% of 34 seed cards correctly classified
2. **Accuracy**: 95%+ correct program detection (vs manual review)
3. **Valuation Accuracy**: Within 10% of official bank documentation
4. **Database Integrity**: All FK constraints valid

### User Experience

1. **Clarity**: Users can distinguish between different point programs
2. **Transparency**: Clear documentation of how valuations are calculated
3. **Flexibility**: Easy to add new programs or update valuations

---

## Testing Strategy

### Phase 1: Unit Testing (2 hours)
- Test program detection functions
- Test valuation lookups
- Test currency type mappings

### Phase 2: Integration Testing (1 hour)
- Test database seeding
- Test migration script
- Test updated scraper

### Phase 3: Validation Testing (1 hour)
- Cross-reference all 34 seed cards
- Verify against official bank websites
- Check valuations against industry standards

---

## Rollout Plan

### Phase 1: Development (Week 1)
- Create reward_programs.py registry
- Update scraper logic
- Create migration scripts

### Phase 2: Testing (Week 2)
- Unit tests
- Integration tests
- Validation against real data

### Phase 3: Migration (Week 3)
- Run database migrations
- Seed reward_programs table
- Backfill existing cards
- Manual review of edge cases

### Phase 4: Verification (Week 4)
- Validate all cards have programs
- Check valuations are accurate
- Update documentation

---

## Maintenance

### Monthly Tasks
- Review program valuations against market rates
- Update transfer partners
- Add new programs as needed

### Quarterly Tasks
- Comprehensive valuation audit
- User feedback review
- Documentation updates

---

## Future Enhancements

1. **User-Submitted Valuations**: Allow users to share redemption experiences
2. **Dynamic Valuations**: Update based on real-time redemption data
3. **Transfer Partner API**: Integrate with airline/hotel APIs for live availability
4. **Multi-Currency Support**: Expand beyond Canada (US, UK, Australia)
5. **Program Tier Support**: Elite status bonuses and multipliers

---

## Related Documentation

- [PROJECT_ANALYSIS.md](../PROJECT_ANALYSIS.md) - Full project analysis
- [TASK_DUPLICATE_PREVENTION.md](./TASK_DUPLICATE_PREVENTION.md) - Duplicate prevention task
- [README.md](../README.md) - Project overview

---

**Last Updated**: January 18, 2026
**Document Version**: 1.0
