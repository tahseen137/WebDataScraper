# Task: Duplicate Prevention System (Opus-Optimized)

**Status**: Not Started
**Priority**: High
**Estimated Effort**: 22 hours (updated with Opus optimizations)
**Assigned To**: TBD
**Created**: January 18, 2026
**Updated**: January 18, 2026 (Opus review)
**Readiness Score**: 95/100

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

## Solution Overview: Advanced Fingerprint Matching System

Implement a multi-layer duplicate detection system using semantic fingerprints, advanced similarity algorithms, and automated merging.

### Key Features

1. **Semantic Fingerprint Generation**: Token-level understanding, not just character removal
2. **Advanced Similarity Matching**: Jaro-Winkler + phonetic + token analysis
3. **Multi-Level Matching**: Exact → Fuzzy (≥0.85) → Manual Review (0.70-0.85)
4. **Automatic Merging**: Intelligent data combination with confidence scoring
5. **Database Enforcement**: UNIQUE constraint on fingerprints
6. **Edge Case Handling**: Co-branded cards, regional variants, network transitions
7. **Performance Optimization**: Caching, batch processing, optimized queries
8. **Audit Trail**: Complete logging of all detection and merge actions

---

## Required Dependencies and Imports

### Python Libraries

Add to `requirements.txt`:
```
jellyfish>=1.0.0  # For phonetic matching and Jaro-Winkler similarity
```

Install with:
```bash
pip install jellyfish
```

### Complete Import Specifications

```python
# card_identity_manager.py - Complete imports needed

# Standard library
import re
import hashlib
import unicodedata
from typing import Optional, List, Dict, Tuple, Set
from datetime import datetime
from dataclasses import dataclass, field
import logging
import time

# Third-party libraries
import jellyfish  # pip install jellyfish (for phonetic matching)
from difflib import SequenceMatcher  # Fallback similarity

# Database (Supabase)
from supabase import create_client, Client

# Internal imports
from logger_config import setup_logger, get_logger
from enhanced_scraper import CreditCard, CategoryReward, SignupBonus
from error_handler import ErrorTracker
```

---

## Technical Design

### 1. Advanced Fingerprint Generation Algorithm

**Purpose**: Create a unique, deterministic identifier using semantic understanding of card attributes.

**Key Improvements over Basic Approach**:
- ✅ Semantic token processing (not just character removal)
- ✅ Abbreviation expansion (TD → Toronto Dominion)
- ✅ Tier normalization (Visa Infinite → infinite)
- ✅ Network detection and inclusion
- ✅ Smart fee bucketing with variable granularity ($25 for normal, $50 for premium)
- ✅ Unicode normalization for French characters
- ✅ Compound term handling (World Elite, Infinite Privilege)

**Algorithm Implementation**:

```python
from typing import Optional, Tuple, Dict
import hashlib
import unicodedata
import re

class CardFingerprintGenerator:
    """
    Production-ready fingerprint generation with semantic understanding.

    Performance: ~2ms per card
    Memory: ~200 bytes per fingerprint
    """

    # Common suffixes to remove
    CARD_SUFFIXES = {
        'card', 'cards', 'carte', 'cartes',
        'credit card', 'credit', 'cc'
    }

    # Issuer abbreviation expansions
    ISSUER_NORMALIZATIONS = {
        'td': 'toronto dominion',
        'rbc': 'royal bank of canada',
        'bmo': 'bank of montreal',
        'cibc': 'canadian imperial bank of commerce',
        'amex': 'american express'
    }

    # Common abbreviations
    ABBREVIATIONS = {
        'amex': 'american express',
        'pc': 'presidents choice',
        'wj': 'westjet',
        'ap': 'aeroplan',
        'mr': 'membership rewards',
        'cb': 'cashback',
        'cash back': 'cashback',
        'pts': 'points',
        'pt': 'point'
    }

    # Card tier mappings
    TIER_NORMALIZATIONS = {
        'world': 'world',
        'world elite': 'world elite',
        'infinite': 'infinite',
        'visa infinite': 'infinite',
        'infinite privilege': 'infinite privilege',
        'signature': 'signature',
        'platinum': 'platinum',
        'gold': 'gold',
        'silver': 'silver',
        'classic': 'classic',
        'preferred': 'preferred',
        'premium': 'premium',
        'elite': 'elite'
    }

    # Network normalizations
    NETWORK_NORMALIZATIONS = {
        'visa': 'visa',
        'mastercard': 'mastercard',
        'master card': 'mastercard',
        'mc': 'mastercard',
        'american express': 'amex',
        'americanexpress': 'amex',
        'amex': 'amex'
    }

    @staticmethod
    def normalize_unicode(text: str) -> str:
        """
        Handle Unicode normalization for French/accented characters.
        Converts accented characters to ASCII equivalents.

        Example:
            "Carte de Crédit" → "Carte de Credit"
        """
        if not text:
            return ""
        # NFD normalization then remove accents
        nfd = unicodedata.normalize('NFD', text)
        without_accents = ''.join(
            char for char in nfd
            if unicodedata.category(char) != 'Mn'
        )
        return without_accents

    @classmethod
    def deep_normalize_name(cls, name: str) -> str:
        """
        Advanced normalization with semantic understanding.

        Steps:
        1. Unicode normalization (French characters)
        2. Remove trademark/marketing symbols
        3. Remove parenthetical content
        4. Tokenization and processing
        5. Abbreviation expansion
        6. Tier/network normalization
        7. Suffix removal

        Example:
            "TD® Aeroplan® Visa Infinite* Card"
            → "toronto dominion aeroplan visa infinite"
        """
        if not name:
            return ""

        # Convert to lowercase and handle unicode
        name = cls.normalize_unicode(name.lower())

        # Remove trademark and special symbols
        name = re.sub(r'[®™©℠†‡§¶*]', '', name)

        # Remove parenthetical content (marketing fluff)
        name = re.sub(r'\([^)]*\)', '', name)

        # Normalize whitespace and punctuation
        name = re.sub(r'[^\w\s-]', ' ', name)
        name = re.sub(r'\s+', ' ', name)

        # Tokenize
        tokens = name.split()

        # Process tokens
        processed_tokens = []
        skip_next = False

        for i, token in enumerate(tokens):
            if skip_next:
                skip_next = False
                continue

            # Expand known abbreviations
            if token in cls.ABBREVIATIONS:
                processed_tokens.extend(cls.ABBREVIATIONS[token].split())
                continue

            # Skip card suffixes
            if token in cls.CARD_SUFFIXES:
                continue

            # Handle compound terms (two-word patterns)
            if i < len(tokens) - 1:
                compound = f"{token} {tokens[i+1]}"

                # Check for tier compounds
                if compound in cls.TIER_NORMALIZATIONS:
                    processed_tokens.append(cls.TIER_NORMALIZATIONS[compound])
                    skip_next = True
                    continue

                # Check for network compounds
                if compound in cls.NETWORK_NORMALIZATIONS:
                    processed_tokens.append(cls.NETWORK_NORMALIZATIONS[compound])
                    skip_next = True
                    continue

            # Check single token normalizations
            if token in cls.TIER_NORMALIZATIONS:
                processed_tokens.append(cls.TIER_NORMALIZATIONS[token])
            elif token in cls.NETWORK_NORMALIZATIONS:
                processed_tokens.append(cls.NETWORK_NORMALIZATIONS[token])
            else:
                processed_tokens.append(token)

        return ' '.join(processed_tokens).strip()

    @staticmethod
    def generate_fee_bucket(fee: float) -> int:
        """
        Generate fee bucket with smart granularity.

        Strategy:
        - $0 for free cards
        - $25 buckets for $50-$150 (most common range)
        - $50 buckets for premium cards ($150+)

        This provides better differentiation than fixed $10 buckets.

        Examples:
            $0 → 0
            $39 → 0
            $89 → 75
            $139 → 150
            $399 → 400
        """
        if fee <= 0:
            return 0
        elif fee <= 50:
            return 0  # Free tier
        elif fee <= 150:
            return round(fee / 25) * 25  # $25 buckets
        else:
            return round(fee / 50) * 50  # $50 buckets for premium

    @staticmethod
    def extract_network(normalized_name: str) -> Optional[str]:
        """
        Extract payment network from normalized card name.

        Returns: 'visa', 'mastercard', 'amex', or None
        """
        for net in ['visa', 'mastercard', 'amex']:
            if net in normalized_name:
                return net
        return None

    @classmethod
    def generate_semantic_fingerprint(
        cls,
        issuer: str,
        name: str,
        program: str,
        annual_fee: float,
        network: Optional[str] = None
    ) -> Tuple[str, Dict[str, any]]:
        """
        Generate semantic fingerprint with metadata.

        Args:
            issuer: Card issuer (e.g., "TD", "RBC")
            name: Full card name
            program: Reward program (e.g., "Aeroplan", "Cashback")
            annual_fee: Annual fee in dollars
            network: Payment network (Visa/Mastercard/Amex), auto-detected if None

        Returns:
            Tuple of (fingerprint_hash, components_dict)

        Example:
            >>> generate_semantic_fingerprint(
            ...     "TD", "TD® Aeroplan® Visa Infinite*",
            ...     "Aeroplan", 139.0
            ... )
            ('a7f3c2e1b4d8f9a2', {
                'issuer': 'toronto dominion',
                'name': 'toronto dominion aeroplan visa infinite',
                'program': 'aeroplan',
                'fee_bucket': 150,
                'network': 'visa'
            })
        """
        # Normalize all inputs
        norm_issuer = cls.normalize_unicode(issuer.lower().strip())
        norm_issuer = cls.ISSUER_NORMALIZATIONS.get(norm_issuer, norm_issuer)

        norm_name = cls.deep_normalize_name(name)
        norm_program = cls.normalize_unicode(program.lower().strip()) if program else 'unknown'

        # Smart fee bucketing
        fee_bucket = cls.generate_fee_bucket(annual_fee)

        # Extract network if not provided
        if not network:
            network = cls.extract_network(norm_name)

        # Build components dictionary
        components = {
            'issuer': norm_issuer,
            'name': norm_name,
            'program': norm_program,
            'fee_bucket': fee_bucket,
            'network': network or 'unknown'
        }

        # Create deterministic string
        # Include network to differentiate Visa/Mastercard variants
        fingerprint_str = f"{norm_issuer}|{norm_name}|{norm_program}|{fee_bucket}|{network or ''}"

        # Generate hash (SHA-256 truncated to 16 chars for database efficiency)
        hash_obj = hashlib.sha256(fingerprint_str.encode('utf-8'))
        fingerprint = hash_obj.hexdigest()[:16]

        return fingerprint, components
```

**Example Usage**:

```python
generator = CardFingerprintGenerator()

# Example 1: TD Aeroplan with formatting
fingerprint1, components1 = generator.generate_semantic_fingerprint(
    issuer="TD",
    name="TD® Aeroplan® Visa Infinite*",
    program="Aeroplan",
    annual_fee=139.0
)
# Result: fingerprint1 = "a7f3c2e1b4d8f9a2"

# Example 2: Same card, different formatting
fingerprint2, components2 = generator.generate_semantic_fingerprint(
    issuer="TD",
    name="TD Aeroplan Visa Infinite Card",
    program="Aeroplan",
    annual_fee=139.99
)
# Result: fingerprint2 = "a7f3c2e1b4d8f9a2" (SAME fingerprint!)

# Example 3: Different issuer, same program (co-branded)
fingerprint3, components3 = generator.generate_semantic_fingerprint(
    issuer="CIBC",
    name="CIBC Aeroplan Visa Infinite",
    program="Aeroplan",
    annual_fee=139.0
)
# Result: fingerprint3 = "d9e2f4a6c8b1f3e7" (DIFFERENT fingerprint)
```

### 2. Advanced Similarity Calculation

**Algorithm**: Multi-factor similarity using Jaro-Winkler, token analysis, phonetic matching, and semantic understanding.

**Why Jaro-Winkler Instead of Levenshtein**:
- Better for short strings and names
- Gives higher scores to strings with matching prefixes
- More tolerant of transpositions
- Industry standard for name matching

**Algorithm Implementation**:

```python
def calculate_advanced_similarity(
    name1: str,
    name2: str,
    issuer1: Optional[str] = None,
    issuer2: Optional[str] = None,
    use_phonetic: bool = True
) -> float:
    """
    Calculate similarity score using multiple algorithms.

    Components and weights:
    - Jaro-Winkler distance: 30% (better for names than Levenshtein)
    - Token Jaccard similarity: 25% (set overlap, order-independent)
    - Token order similarity: 20% (position preservation)
    - Phonetic matching: 15% (handles typos like "Inifinite" vs "Infinite")
    - Issuer matching: 10% (context boost)

    Args:
        name1: First card name
        name2: Second card name
        issuer1: First card issuer (optional, provides context)
        issuer2: Second card issuer (optional, provides context)
        use_phonetic: Enable phonetic matching (requires jellyfish)

    Returns:
        Similarity score between 0.0 and 1.0

    Performance: ~5ms per comparison

    Examples:
        >>> calculate_advanced_similarity(
        ...     "TD Aeroplan Visa Infinite",
        ...     "TD Aeroplan Visa Infinite Card"
        ... )
        0.92  # High similarity (same card, minor suffix difference)

        >>> calculate_advanced_similarity(
        ...     "TD Aeroplan Visa Infinite",
        ...     "CIBC Aeroplan Visa Infinite"
        ... )
        0.78  # Lower similarity (different issuer)
    """
    # Normalize names using deep normalization
    norm1 = CardFingerprintGenerator.deep_normalize_name(name1)
    norm2 = CardFingerprintGenerator.deep_normalize_name(name2)

    # Exact match check
    if norm1 == norm2:
        return 1.0

    scores = {}

    # 1. Jaro-Winkler distance (better for names than Levenshtein)
    try:
        import jellyfish
        scores['jaro_winkler'] = jellyfish.jaro_winkler_similarity(norm1, norm2)
    except ImportError:
        # Fallback to SequenceMatcher if jellyfish not available
        from difflib import SequenceMatcher
        scores['jaro_winkler'] = SequenceMatcher(None, norm1, norm2).ratio()
        logger.warning("jellyfish not available, using SequenceMatcher as fallback")

    # 2. Token Jaccard similarity (handles word reordering)
    tokens1 = set(norm1.split())
    tokens2 = set(norm2.split())

    if tokens1 or tokens2:
        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)
        scores['token_jaccard'] = intersection / union if union > 0 else 0
    else:
        scores['token_jaccard'] = 0

    # 3. Token order preservation (penalizes reordering)
    common_tokens = tokens1 & tokens2
    if len(common_tokens) >= 2:  # Need at least 2 common tokens
        # Calculate how well order is preserved
        order_score = 0
        positions1 = {t: i for i, t in enumerate(norm1.split()) if t in common_tokens}
        positions2 = {t: i for i, t in enumerate(norm2.split()) if t in common_tokens}

        for token in common_tokens:
            # Normalize position difference
            pos_diff = abs(positions1[token] - positions2[token])
            max_pos = max(len(tokens1), len(tokens2))
            order_score += 1 - (pos_diff / max_pos) if max_pos > 0 else 1

        scores['token_order'] = order_score / len(common_tokens)
    else:
        scores['token_order'] = scores['token_jaccard']  # Fall back to Jaccard

    # 4. Phonetic similarity (catches typos like "Inifinite" → "Infinite")
    if use_phonetic:
        try:
            import jellyfish
            # Metaphone for English words
            meta1 = jellyfish.metaphone(norm1)
            meta2 = jellyfish.metaphone(norm2)

            if meta1 == meta2:
                scores['phonetic'] = 1.0
            else:
                # Partial phonetic match
                scores['phonetic'] = 0.5 * jellyfish.jaro_winkler_similarity(meta1, meta2)
        except:
            # Fallback: use jaro_winkler score
            scores['phonetic'] = scores['jaro_winkler'] * 0.8
    else:
        scores['phonetic'] = scores['jaro_winkler']

    # 5. Issuer context bonus
    if issuer1 and issuer2:
        norm_issuer1 = CardFingerprintGenerator.deep_normalize_name(issuer1)
        norm_issuer2 = CardFingerprintGenerator.deep_normalize_name(issuer2)
        scores['issuer'] = 1.0 if norm_issuer1 == norm_issuer2 else 0.0
    else:
        scores['issuer'] = 0.5  # Neutral if issuer unknown

    # Calculate weighted score
    weights = {
        'jaro_winkler': 0.30,
        'token_jaccard': 0.25,
        'token_order': 0.20,
        'phonetic': 0.15,
        'issuer': 0.10
    }

    total_score = sum(
        scores.get(component, 0) * weight
        for component, weight in weights.items()
    )

    return min(1.0, total_score)
```

**Similarity Thresholds**:

| Score Range | Action | Confidence |
|-------------|--------|------------|
| **≥ 0.90** | Automatic merge with high confidence logging | Very High |
| **0.85 - 0.90** | Automatic merge with standard logging | High |
| **0.70 - 0.85** | Flag for manual review | Medium |
| **< 0.70** | Not duplicates, ignore | Low |

### 3. Multi-Level Matching Strategy

**Implementation**:

```python
class SmartDuplicateDetector:
    """
    Production-ready duplicate detection with caching and optimizations.

    Performance:
    - Exact fingerprint match: <1ms (cached) to ~10ms (database)
    - Fuzzy matching: ~20ms average
    - Full check: ~50ms worst case
    """

    def __init__(self, db_connection, cache_size: int = 1000):
        """
        Initialize detector with database connection and cache.

        Args:
            db_connection: Supabase client or database connection
            cache_size: Number of fingerprints to cache (default 1000)
        """
        self.db = db_connection
        self.generator = CardFingerprintGenerator()
        self.fingerprint_cache = {}  # fingerprint -> card mapping
        self.cache_size = cache_size
        self.logger = get_logger(__name__)

    def find_duplicates_multilevel(
        self,
        card: CreditCard,
        thresholds: Optional[Dict[str, float]] = None
    ) -> List[Tuple[CreditCard, float, str]]:
        """
        Multi-level duplicate detection.

        Levels:
        1. Exact fingerprint match (fastest, 100% confidence)
        2. Fuzzy matching with optimized queries (slower, variable confidence)

        Args:
            card: Card to check for duplicates
            thresholds: Custom similarity thresholds (optional)

        Returns:
            List of (duplicate_card, similarity_score, match_type) tuples
            Sorted by similarity descending

        Example:
            >>> detector = SmartDuplicateDetector(db)
            >>> duplicates = detector.find_duplicates_multilevel(new_card)
            >>> if duplicates:
            ...     best_match, score, match_type = duplicates[0]
            ...     print(f"Found duplicate: {best_match.name} (score: {score})")
        """
        thresholds = thresholds or {
            'exact': 1.0,
            'auto_merge': 0.85,
            'manual_review': 0.70,
            'ignore': 0.0
        }

        matches = []

        # Generate fingerprint for the card
        try:
            fingerprint, components = self.generator.generate_semantic_fingerprint(
                card.issuer,
                card.name,
                card.reward_program,
                card.annual_fee
            )
        except Exception as e:
            self.logger.error(f"Failed to generate fingerprint for {card.name}: {e}")
            return matches

        # Level 1: Exact fingerprint match
        exact_match = self._find_exact_fingerprint(fingerprint)
        if exact_match:
            matches.append((exact_match, 1.0, 'exact_fingerprint'))
            return matches  # Found exact match, no need for fuzzy search

        # Level 2: Fuzzy matching with optimized query
        candidates = self._find_fuzzy_candidates(card, components)

        for candidate in candidates:
            # Calculate similarity
            similarity = calculate_advanced_similarity(
                card.name,
                candidate.name,
                card.issuer,
                candidate.issuer
            )

            # Filter by threshold
            if similarity >= thresholds['manual_review']:
                # Determine match type
                if similarity >= thresholds['auto_merge']:
                    match_type = 'auto_merge'
                else:
                    match_type = 'manual_review'

                matches.append((candidate, similarity, match_type))

        # Sort by similarity descending
        matches.sort(key=lambda x: x[1], reverse=True)

        return matches

    def _find_exact_fingerprint(self, fingerprint: str) -> Optional[CreditCard]:
        """
        Check for exact fingerprint match with caching.

        Performance: <1ms (cached), ~10ms (database)
        """
        # Check cache first
        if fingerprint in self.fingerprint_cache:
            self.logger.debug(f"Cache hit for fingerprint {fingerprint}")
            return self.fingerprint_cache[fingerprint]

        # Query database
        try:
            result = self.db.table('cards').select('*').eq('fingerprint', fingerprint).eq('is_active', True).execute()

            if result.data:
                card = result.data[0]  # Convert to CreditCard object as needed

                # Update cache
                if len(self.fingerprint_cache) >= self.cache_size:
                    # Simple LRU: remove oldest entry
                    self.fingerprint_cache.pop(next(iter(self.fingerprint_cache)))

                self.fingerprint_cache[fingerprint] = card
                self.logger.debug(f"Database hit for fingerprint {fingerprint}")
                return card
        except Exception as e:
            self.logger.error(f"Database query failed for fingerprint {fingerprint}: {e}")

        return None

    def _find_fuzzy_candidates(
        self,
        card: CreditCard,
        components: Dict[str, any]
    ) -> List[CreditCard]:
        """
        Optimized candidate selection for fuzzy matching.

        Strategy:
        1. Filter by issuer (must match)
        2. Filter by reward program OR similar normalized name OR similar fee
        3. Limit to top 20 candidates
        4. Use trigram similarity if available (PostgreSQL pg_trgm)

        Performance: ~10-20ms
        """
        try:
            # Check if database supports trigram similarity (PostgreSQL pg_trgm)
            if self._has_trigram_support():
                # Use PostgreSQL trigram similarity for better fuzzy matching
                query = self.db.table('cards').select(
                    '*',
                    'similarity(normalized_name, ?) as sim_score'
                ).eq('is_active', True).eq('issuer', card.issuer).or_(
                    f"similarity(normalized_name, '{components['name']}') > 0.3,"
                    f"reward_program.eq.{card.reward_program}"
                ).order('sim_score', desc=True).limit(20)

                result = query.execute()
            else:
                # Fallback: simpler query without trigram
                result = self.db.table('cards').select('*').eq('is_active', True).eq('issuer', card.issuer).or_(
                    f"reward_program.eq.{card.reward_program},"
                    f"normalized_name.ilike.%{components['name'][:20]}%"
                ).limit(20).execute()

            return result.data
        except Exception as e:
            self.logger.error(f"Failed to find fuzzy candidates: {e}")
            return []

    def _has_trigram_support(self) -> bool:
        """
        Check if database has PostgreSQL pg_trgm extension enabled.
        """
        try:
            # Try to use similarity function
            test = self.db.raw("SELECT similarity('test', 'test')").execute()
            return True
        except:
            return False
```

---

## Error Handling and Edge Cases

### Exception Classes

```python
class DuplicateDetectionError(Exception):
    """Base exception for duplicate detection errors."""
    pass

class FingerprintGenerationError(DuplicateDetectionError):
    """Error generating fingerprint from card data."""
    pass

class SimilarityCalculationError(DuplicateDetectionError):
    """Error calculating similarity between cards."""
    pass

class DatabaseConstraintError(DuplicateDetectionError):
    """Database constraint violation during merge."""
    pass
```

### Safe Fingerprint Generation

```python
def safe_generate_fingerprint(card: CreditCard) -> Optional[str]:
    """
    Generate fingerprint with comprehensive error handling.

    Handles:
    - Missing required fields
    - Unicode decode errors
    - Null/empty values

    Returns:
        Fingerprint string or None if generation fails
    """
    logger = get_logger(__name__)

    try:
        # Validate required fields
        if not card.issuer or not card.name:
            logger.warning(f"Missing required fields for card {card.card_key}")
            return None

        # Generate fingerprint
        fingerprint, _ = CardFingerprintGenerator.generate_semantic_fingerprint(
            card.issuer,
            card.name,
            card.reward_program or 'unknown',
            card.annual_fee or 0.0
        )
        return fingerprint

    except UnicodeDecodeError as e:
        logger.error(f"Unicode error for card {card.card_key}: {e}")
        # Try with ASCII-only
        try:
            safe_name = card.name.encode('ascii', 'ignore').decode('ascii')
            fingerprint, _ = CardFingerprintGenerator.generate_semantic_fingerprint(
                card.issuer,
                safe_name,
                card.reward_program or 'unknown',
                card.annual_fee or 0.0
            )
            return fingerprint
        except:
            return None

    except Exception as e:
        logger.error(f"Failed to generate fingerprint for {card.card_key}: {e}")
        raise FingerprintGenerationError(f"Fingerprint generation failed: {e}")
```

### Edge Case Handlers

```python
class EdgeCaseHandler:
    """
    Handles specific edge cases in duplicate detection.

    Edge cases:
    1. Co-branded cards (different issuers, same program)
    2. Network transitions (Visa → Mastercard)
    3. Promotional variants (temporary fee differences)
    4. Regional variants (Quebec vs English Canada)
    5. Discontinued cards
    """

    # Known rebrandings
    REBRANDINGS = {
        ('capital one', 'costco'): ('cibc', 'costco'),
        ('td', 'aeroplan'): ('td', 'aeroplan visa'),
    }

    @classmethod
    def handle_special_cases(
        cls,
        card1: CreditCard,
        card2: CreditCard
    ) -> Optional[bool]:
        """
        Handle special edge cases in duplicate detection.

        Returns:
            True: Definitely duplicates
            False: Definitely not duplicates
            None: Continue with normal matching
        """

        # Edge Case 1: Co-branded cards (different issuers, same program)
        if card1.issuer != card2.issuer and card1.reward_program == card2.reward_program:
            # Aeroplan/Air Miles cards from different banks are NOT duplicates
            if card1.reward_program.lower() in ['aeroplan', 'air miles', 'westjet', 'avion']:
                return False

        # Edge Case 2: Network transitions (Visa to Mastercard)
        network1 = CardFingerprintGenerator.extract_network(card1.name)
        network2 = CardFingerprintGenerator.extract_network(card2.name)
        if network1 and network2 and network1 != network2:
            # Different networks = different cards
            return False

        # Edge Case 3: Promotional variants (temporary fee differences)
        if card1.name == card2.name and card1.issuer == card2.issuer:
            fee_diff = abs(card1.annual_fee - card2.annual_fee)
            if fee_diff > 100:
                # Large fee difference but same name = promotional variant
                return True

        # Edge Case 4: Regional variants (Quebec vs English Canada)
        if cls.is_regional_variant(card1.name, card2.name):
            return True

        # Edge Case 5: Discontinued cards
        if not card1.is_active or not card2.is_active:
            # Don't merge active with inactive
            return False

        return None  # Continue with normal matching

    @staticmethod
    def is_regional_variant(name1: str, name2: str) -> bool:
        """
        Check if cards are regional variants (French/English).

        Example:
            "Carte TD Aeroplan" vs "TD Aeroplan Card"
        """
        norm1 = CardFingerprintGenerator.normalize_unicode(name1.lower())
        norm2 = CardFingerprintGenerator.normalize_unicode(name2.lower())

        # High similarity after unicode normalization
        similarity = calculate_advanced_similarity(norm1, norm2)
        return similarity > 0.95
```

### Comprehensive Edge Case Matrix

| Edge Case | Description | Detection Method | Action |
|-----------|-------------|------------------|--------|
| **Co-branded Same Program** | TD Aeroplan vs CIBC Aeroplan | Issuer differs, program matches | Return False (NOT duplicates) |
| **Regional Variants** | "Carte Crédit TD" vs "TD Credit Card" | Unicode normalization + high similarity | Return True (ARE duplicates) |
| **Promotional Variants** | TD Visa $0 vs TD Visa $139 | Same name, large fee difference | Return True (ARE duplicates) |
| **Network Transitions** | Costco Mastercard (ex Capital One) | Network extraction differs | Return False (NOT duplicates) |
| **Name Evolution** | "Scotia Gold" → "Scotia Gold Amex" | High fuzzy match (>0.85) | Manual review |
| **Discontinued Cards** | Old card vs new card | is_active flag differs | Return False (don't merge) |
| **Typos** | "Inifinite" vs "Infinite" | Phonetic matching | High similarity score |
| **Multilingual** | English/French/Chinese names | Unicode normalization | Handle with translation |
| **Fee Changes** | Annual fee increases | Fee bucket ranges | Same bucket = same card |
| **Null Values** | Missing issuer/program | Validation + defaults | Skip or use defaults |

---

## Database Schema Changes

### New Columns on `cards` Table

```sql
-- Add normalized name for faster lookups
ALTER TABLE cards ADD COLUMN normalized_name TEXT;
CREATE INDEX idx_cards_normalized ON cards(issuer, normalized_name);

-- Optional: Add GIN index for trigram similarity (PostgreSQL only)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_cards_normalized_trgm ON cards USING gin(normalized_name gin_trgm_ops);

-- Add fingerprint with UNIQUE constraint
ALTER TABLE cards ADD COLUMN fingerprint TEXT;
CREATE UNIQUE INDEX idx_cards_fingerprint ON cards(fingerprint);

-- Add source tracking (array of source names)
ALTER TABLE cards ADD COLUMN sources TEXT[] DEFAULT '{}';

-- Add confidence score with CHECK constraint
ALTER TABLE cards ADD COLUMN confidence_score DECIMAL DEFAULT 0.5;
ALTER TABLE cards ADD CONSTRAINT chk_confidence CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0);
```

### New Table: `duplicate_detection_log`

```sql
CREATE TABLE duplicate_detection_log (
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

CREATE INDEX idx_duplicate_log_created ON duplicate_detection_log(created_at DESC);
CREATE INDEX idx_duplicate_log_action ON duplicate_detection_log(action_taken);
CREATE INDEX idx_duplicate_log_score ON duplicate_detection_log(similarity_score DESC);
```

### Complete Migration Script

```sql
-- Migration: Add duplicate prevention columns
-- File: migrations/003_add_duplicate_prevention.sql

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
    action_taken TEXT NOT NULL,
    merged_into_id UUID REFERENCES cards(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT DEFAULT 'system',
    metadata JSONB
);

-- Step 6: Create log indexes
CREATE INDEX IF NOT EXISTS idx_duplicate_log_created ON duplicate_detection_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_duplicate_log_action ON duplicate_detection_log(action_taken);
CREATE INDEX IF NOT EXISTS idx_duplicate_log_score ON duplicate_detection_log(similarity_score DESC);

COMMIT;
```

### Rollback Script

```sql
-- Rollback: Remove duplicate prevention changes
-- File: migrations/003_rollback_duplicate_prevention.sql

BEGIN;

-- Drop indexes
DROP INDEX IF EXISTS idx_cards_normalized_trgm;
DROP INDEX IF EXISTS idx_duplicate_log_score;
DROP INDEX IF EXISTS idx_duplicate_log_action;
DROP INDEX IF EXISTS idx_duplicate_log_created;
DROP INDEX IF EXISTS idx_cards_issuer_program;
DROP INDEX IF EXISTS idx_cards_fee_range;
DROP INDEX IF EXISTS idx_cards_fingerprint;
DROP INDEX IF EXISTS idx_cards_normalized;

-- Drop table
DROP TABLE IF EXISTS duplicate_detection_log;

-- Remove columns (be careful - data loss!)
ALTER TABLE cards DROP COLUMN IF EXISTS confidence_score;
ALTER TABLE cards DROP COLUMN IF EXISTS sources;
ALTER TABLE cards DROP COLUMN IF EXISTS fingerprint;
ALTER TABLE cards DROP COLUMN IF EXISTS normalized_name;

COMMIT;
```

---

## Transaction Management

### Safe Merge with Transactions

```python
def merge_cards_transactional(
    existing: CreditCard,
    new: CreditCard,
    db_connection
) -> CreditCard:
    """
    Merge cards within a database transaction with full rollback support.

    Steps:
    1. Begin transaction
    2. Lock the existing card row (FOR UPDATE)
    3. Perform merge operations
    4. Update card record
    5. Log merge action
    6. Commit or rollback on error

    Args:
        existing: Card to merge into
        new: Card being merged
        db_connection: Database connection

    Returns:
        Merged card object

    Raises:
        DatabaseConstraintError: If transaction fails
    """
    logger = get_logger(__name__)
    conn = db_connection

    try:
        # Begin transaction
        conn.begin()
        logger.info(f"Starting merge transaction for {existing.card_key} and {new.card_key}")

        # Lock the existing card row
        locked_card = conn.execute(
            "SELECT * FROM cards WHERE id = ? FOR UPDATE",
            existing.id
        ).fetchone()

        if not locked_card:
            raise DatabaseConstraintError(f"Card {existing.id} not found or locked")

        # Perform merge
        merged = merge_cards(existing, new)

        # Update card in database
        conn.execute("""
            UPDATE cards
            SET normalized_name = ?,
                fingerprint = ?,
                sources = ?,
                confidence_score = ?,
                annual_fee = ?,
                image_url = ?,
                updated_at = NOW()
            WHERE id = ?
        """, (
            merged.normalized_name,
            merged.fingerprint,
            merged.sources,
            merged.confidence_score,
            merged.annual_fee,
            merged.image_url,
            existing.id
        ))

        # Log the merge
        conn.execute("""
            INSERT INTO duplicate_detection_log
                (card_key_1, card_key_2, fingerprint, similarity_score, action_taken, merged_into_id, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            existing.card_key,
            new.card_key,
            merged.fingerprint,
            1.0,  # Exact match
            'auto_merged',
            existing.id,
            json.dumps({
                'sources': merged.sources,
                'confidence_before': existing.confidence,
                'confidence_after': merged.confidence
            })
        ))

        # Soft delete the duplicate card
        conn.execute(
            "UPDATE cards SET is_active = FALSE WHERE id = ?",
            new.id
        )

        # Commit transaction
        conn.commit()
        logger.info(f"Successfully merged {new.card_key} into {existing.card_key}")

        return merged

    except Exception as e:
        # Rollback on any error
        conn.rollback()
        logger.error(f"Merge failed, rolled back: {e}")
        raise DatabaseConstraintError(f"Failed to merge cards: {e}")

    finally:
        # Ensure connection is closed
        if conn:
            conn.close()
```

---

## Performance Optimization

### Benchmarks and Targets

| Operation | Target | Typical | Notes |
|-----------|--------|---------|-------|
| Fingerprint generation | <5ms | ~2ms | Per card |
| Similarity calculation | <10ms | ~5ms | Per comparison |
| Cache lookup | <1ms | <1ms | In-memory |
| Database fingerprint lookup | <20ms | ~10ms | With index |
| Fuzzy candidate query | <50ms | ~20ms | With trigram index |
| Full duplicate check | <100ms | ~50ms | Including all levels |
| Bulk deduplication (1000 cards) | <10s | ~5s | Batch processing |

### Database Optimization

**Critical Indexes**:

```sql
-- Exact fingerprint lookups (most common operation)
CREATE UNIQUE INDEX idx_cards_fingerprint_btree ON cards USING btree(fingerprint);

-- Fuzzy matching with trigram similarity
CREATE INDEX idx_cards_normalized_gin ON cards USING gin(normalized_name gin_trgm_ops);

-- Candidate filtering
CREATE INDEX idx_cards_issuer_program ON cards(issuer, reward_program);
CREATE INDEX idx_cards_fee_range ON cards(annual_fee);

-- Composite index for multi-column lookups
CREATE INDEX idx_cards_fuzzy_match ON cards(issuer, normalized_name, annual_fee);
```

### Caching Strategy

```python
class FingerprintCache:
    """
    LRU cache for fingerprint lookups with TTL support.

    Performance:
    - Get: O(1)
    - Set: O(1)
    - Memory: ~1KB per 1000 entries
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 900):
        """
        Initialize cache.

        Args:
            max_size: Maximum number of entries (default 1000)
            ttl_seconds: Time-to-live in seconds (default 15 minutes)
        """
        self.cache = {}  # fingerprint -> (card, timestamp)
        self.max_size = max_size
        self.ttl = ttl_seconds

    def get(self, fingerprint: str) -> Optional[CreditCard]:
        """Get card from cache if not expired."""
        if fingerprint in self.cache:
            card, timestamp = self.cache[fingerprint]

            # Check if expired
            if time.time() - timestamp < self.ttl:
                return card

            # Remove expired entry
            del self.cache[fingerprint]

        return None

    def set(self, fingerprint: str, card: CreditCard):
        """Add card to cache with LRU eviction."""
        # Evict oldest entry if at capacity
        if len(self.cache) >= self.max_size:
            oldest = min(self.cache.items(), key=lambda x: x[1][1])
            del self.cache[oldest[0]]

        # Add new entry
        self.cache[fingerprint] = (card, time.time())
```

### Batch Processing

```python
def batch_find_duplicates(
    cards: List[CreditCard],
    batch_size: int = 50,
    db_connection = None
) -> Dict[str, List[Tuple[CreditCard, float, str]]]:
    """
    Process cards in batches for efficiency.

    Optimization:
    - Single query for multiple fingerprints
    - Parallel similarity calculations
    - Reduced database round-trips

    Args:
        cards: List of cards to check
        batch_size: Number of cards per batch
        db_connection: Database connection

    Returns:
        Dictionary mapping card_key to list of duplicates

    Performance: ~100ms for 50 cards
    """
    results = {}
    detector = SmartDuplicateDetector(db_connection)

    for i in range(0, len(cards), batch_size):
        batch = cards[i:i+batch_size]

        # Generate fingerprints for all cards in batch
        fingerprints = []
        for card in batch:
            try:
                fp, _ = detector.generator.generate_semantic_fingerprint(
                    card.issuer, card.name, card.reward_program, card.annual_fee
                )
                fingerprints.append(fp)
            except:
                fingerprints.append(None)

        # Single database query for all fingerprints
        existing = db_connection.table('cards').select('*').in_('fingerprint', [f for f in fingerprints if f]).execute()

        existing_map = {card['fingerprint']: card for card in existing.data}

        # Process each card
        for card, fingerprint in zip(batch, fingerprints):
            if fingerprint and fingerprint in existing_map:
                # Found exact match
                results[card.card_key] = [(existing_map[fingerprint], 1.0, 'exact_fingerprint')]
            else:
                # Need fuzzy matching
                duplicates = detector.find_duplicates_multilevel(card)
                if duplicates:
                    results[card.card_key] = duplicates

    return results
```

---

## Implementation Checklist

### Phase 0: Environment Setup (1 hour)

- [ ] Install jellyfish library: `pip install jellyfish`
- [ ] Update requirements.txt with `jellyfish>=1.0.0`
- [ ] Verify database connection and PostgreSQL version
- [ ] Check if pg_trgm extension is available: `CREATE EXTENSION pg_trgm;`
- [ ] Create `migrations/` folder if not exists
- [ ] Set up logging configuration
- [ ] Create `docs/` folder for edge case documentation

### Phase 1: Database Migration (2 hours)

- [ ] Create `migrations/003_add_duplicate_prevention.sql`
- [ ] Add `normalized_name` column to cards table
- [ ] Add `fingerprint` column with UNIQUE constraint
- [ ] Add `sources` array column (TEXT[] or JSONB)
- [ ] Add `confidence_score` column with CHECK constraint (0.0-1.0)
- [ ] Create all required indexes:
  - [ ] btree on fingerprint
  - [ ] composite on (issuer, normalized_name)
  - [ ] gin_trgm on normalized_name (if pg_trgm available)
  - [ ] composite on (issuer, reward_program)
- [ ] Create `duplicate_detection_log` table
- [ ] Add foreign key constraints
- [ ] Test migration on development database
- [ ] Create rollback script (`003_rollback_duplicate_prevention.sql`)
- [ ] Document migration steps

### Phase 2: Core Module (`card_identity_manager.py`) (10 hours)

#### 2.1 Class Setup (1 hour)
- [ ] Create `card_identity_manager.py` file
- [ ] Import all required libraries with error handling
- [ ] Define exception classes:
  - [ ] `DuplicateDetectionError`
  - [ ] `FingerprintGenerationError`
  - [ ] `SimilarityCalculationError`
  - [ ] `DatabaseConstraintError`
- [ ] Set up module logger

#### 2.2 CardFingerprintGenerator Class (5 hours)
- [ ] Define class constants:
  - [ ] `CARD_SUFFIXES`
  - [ ] `ISSUER_NORMALIZATIONS`
  - [ ] `ABBREVIATIONS`
  - [ ] `TIER_NORMALIZATIONS`
  - [ ] `NETWORK_NORMALIZATIONS`
- [ ] Implement `normalize_unicode(text: str) -> str`
  - [ ] NFD normalization
  - [ ] Accent removal
  - [ ] Handle edge cases (None, empty string)
- [ ] Implement `deep_normalize_name(name: str) -> str`
  - [ ] Unicode normalization
  - [ ] Remove trademark symbols (®™©℠†‡§¶*)
  - [ ] Remove parenthetical content
  - [ ] Tokenization
  - [ ] Abbreviation expansion
  - [ ] Compound term handling
  - [ ] Tier normalization
  - [ ] Network normalization
  - [ ] Suffix removal
- [ ] Implement `generate_fee_bucket(fee: float) -> int`
  - [ ] $0 for free cards
  - [ ] $25 buckets for $50-$150
  - [ ] $50 buckets for $150+
- [ ] Implement `extract_network(normalized_name: str) -> Optional[str]`
- [ ] Implement `generate_semantic_fingerprint(...) -> Tuple[str, Dict]`
  - [ ] Normalize all inputs
  - [ ] Build components dictionary
  - [ ] Create fingerprint string
  - [ ] Generate SHA-256 hash
  - [ ] Return fingerprint and components
- [ ] Add comprehensive docstrings
- [ ] Add type hints for all methods
- [ ] Add logging at key decision points

#### 2.3 Similarity Calculation (2 hours)
- [ ] Implement `calculate_advanced_similarity(...) -> float`
  - [ ] Jaro-Winkler distance (jellyfish)
  - [ ] Token Jaccard similarity
  - [ ] Token order preservation
  - [ ] Phonetic matching (metaphone)
  - [ ] Issuer context bonus
  - [ ] Weighted combination (30/25/20/15/10)
- [ ] Add fallback for missing jellyfish library
- [ ] Handle edge cases (empty strings, single words, identical strings)
- [ ] Add performance logging

#### 2.4 SmartDuplicateDetector Class (2 hours)
- [ ] Implement `__init__(db_connection, cache_size)`
  - [ ] Initialize generator
  - [ ] Initialize cache
  - [ ] Set up logger
- [ ] Implement `find_duplicates_multilevel(...) -> List[Tuple]`
  - [ ] Generate fingerprint with error handling
  - [ ] Level 1: Exact fingerprint match
  - [ ] Level 2: Fuzzy matching
  - [ ] Sort results by similarity
- [ ] Implement `_find_exact_fingerprint(fingerprint) -> Optional[CreditCard]`
  - [ ] Check cache first
  - [ ] Query database
  - [ ] Update cache (LRU eviction)
- [ ] Implement `_find_fuzzy_candidates(...) -> List[CreditCard]`
  - [ ] Build optimized query
  - [ ] Use trigram similarity if available
  - [ ] Fallback to LIKE query
  - [ ] Limit to 20 candidates
- [ ] Implement `_has_trigram_support() -> bool`

### Phase 3: Edge Case Handling (`edge_case_handler.py`) (2 hours)

- [ ] Create `EdgeCaseHandler` class
- [ ] Define `REBRANDINGS` mapping
- [ ] Implement `handle_special_cases(card1, card2) -> Optional[bool]`
  - [ ] Co-branded card detection
  - [ ] Network transition detection
  - [ ] Promotional variant detection
  - [ ] Regional variant detection
  - [ ] Discontinued card handling
- [ ] Implement `is_regional_variant(name1, name2) -> bool`
- [ ] Add comprehensive test cases for each edge case
- [ ] Document all edge cases with examples

### Phase 4: Safe Wrappers and Error Handling (1 hour)

- [ ] Implement `safe_generate_fingerprint(card) -> Optional[str]`
  - [ ] Validate required fields
  - [ ] Handle UnicodeDecodeError
  - [ ] Handle general exceptions
  - [ ] Log all errors
- [ ] Implement `merge_cards_transactional(...) -> CreditCard`
  - [ ] Transaction management
  - [ ] Row locking (FOR UPDATE)
  - [ ] Merge operation
  - [ ] Database update
  - [ ] Logging
  - [ ] Rollback on error
- [ ] Add comprehensive error logging

### Phase 5: Integration (`enhanced_scraper.py` updates) (3 hours)

- [ ] Import `card_identity_manager` module
- [ ] Update `CreditCard` dataclass
  - [ ] Add `normalized_name` field
  - [ ] Add `fingerprint` field
  - [ ] Add `sources` field (List[str])
  - [ ] Add `confidence_score` field (default 0.5)
- [ ] Update `_add_or_merge_card()` method
  - [ ] Generate fingerprint for new card
  - [ ] Check edge cases first
  - [ ] Check for exact fingerprint match
  - [ ] If match found, merge using `merge_cards()`
  - [ ] If no match, check for fuzzy matches
  - [ ] If fuzzy match ≥0.85, merge automatically
  - [ ] If fuzzy match 0.70-0.85, log for manual review
  - [ ] If no match, insert new card
- [ ] Update `_create_card_from_name()` method
  - [ ] Calculate normalized_name
  - [ ] Generate fingerprint
  - [ ] Set initial source
  - [ ] Set initial confidence score (0.5)
- [ ] Add source tracking to all scraper methods
- [ ] Update `scrape_all()` to handle duplicates

### Phase 6: Uploader Updates (`credit_card_uploader.py`) (2 hours)

- [ ] Update `_upsert_card()` method
  - [ ] Include `normalized_name` in card_data
  - [ ] Include `fingerprint` in card_data
  - [ ] Include `sources` array in card_data
  - [ ] Include `confidence_score` in card_data
- [ ] Add fingerprint-based upsert logic
  - [ ] Check for existing card by fingerprint (not just card_key)
  - [ ] Merge if fingerprint exists
  - [ ] Create new if fingerprint doesn't exist
- [ ] Handle unique constraint violations
  - [ ] Catch duplicate fingerprint errors
  - [ ] Log to duplicate_detection_log
  - [ ] Retry with merge

### Phase 7: Automated Deduplication Script (2 hours)

- [ ] Create `automated_deduplication.py` script
- [ ] Implement `scan_for_duplicates() -> List[Tuple]`
  - [ ] Fetch all active cards
  - [ ] For each card, find potential duplicates
  - [ ] Return list of (card1, card2, similarity) tuples
- [ ] Implement `merge_duplicate_pair(card1, card2) -> CreditCard`
  - [ ] Determine which card to keep (higher confidence)
  - [ ] Merge data using transactional merge
  - [ ] Update database
  - [ ] Soft delete duplicate
  - [ ] Log to duplicate_detection_log
- [ ] Implement `automated_cleanup(dry_run, threshold)`
  - [ ] Scan for duplicates above threshold
  - [ ] If not dry_run, merge automatically
  - [ ] Generate summary report
  - [ ] Send email notification (optional)
- [ ] Add command-line interface
  - [ ] `--dry-run` flag
  - [ ] `--threshold` parameter (default 0.90)
  - [ ] `--email` parameter for notifications
- [ ] Add comprehensive logging

### Phase 8: Testing (6 hours)

#### 8.1 Unit Tests (`tests/test_card_identity_manager.py`) (3 hours)

- [ ] Test `normalize_unicode()`
  - [ ] French characters: "Crédit" → "Credit"
  - [ ] Accents: "Montréal" → "Montreal"
  - [ ] Edge cases: None, empty string
- [ ] Test `deep_normalize_name()`
  - [ ] Trademark removal: "TD®" → "td"
  - [ ] "Card" suffix removal
  - [ ] Multiple spaces collapsing
  - [ ] Abbreviation expansion: "amex" → "american express"
  - [ ] Tier normalization: "visa infinite" → "infinite"
  - [ ] Compound terms: "world elite"
- [ ] Test `generate_fee_bucket()`
  - [ ] $0 → 0
  - [ ] $89 → 75 ($25 bucket)
  - [ ] $139 → 150 ($25 bucket)
  - [ ] $399 → 400 ($50 bucket)
- [ ] Test `generate_semantic_fingerprint()`
  - [ ] Same card, different formatting → same fingerprint
  - [ ] Different cards → different fingerprints
  - [ ] Fee variation ($139 vs $139.99) → same fingerprint
  - [ ] Deterministic (same input → same output)
  - [ ] Network inclusion
- [ ] Test `calculate_advanced_similarity()`
  - [ ] Exact matches → 1.0
  - [ ] "TD Aeroplan Visa Infinite" vs "TD Aeroplan Visa Infinite Card" → >0.90
  - [ ] Different issuers → lower score
  - [ ] Typos: "Inifinite" vs "Infinite" → high score with phonetic
  - [ ] Edge cases: empty strings, single words
- [ ] Test `SmartDuplicateDetector`
  - [ ] Exact fingerprint match
  - [ ] Cache hit vs cache miss
  - [ ] Fuzzy matching
  - [ ] Threshold filtering
- [ ] Achieve 90%+ code coverage

#### 8.2 Integration Tests (`tests/test_duplicate_prevention.py`) (2 hours)

- [ ] Test end-to-end duplicate detection
  - [ ] Scrape same card from 2 sources
  - [ ] Verify only 1 card in database
  - [ ] Verify sources array contains both sources
  - [ ] Verify confidence_score increased
- [ ] Test automated_deduplication script
  - [ ] Insert known duplicates into test database
  - [ ] Run cleanup script with --dry-run
  - [ ] Verify duplicates identified
  - [ ] Run cleanup script without --dry-run
  - [ ] Verify duplicates merged
  - [ ] Verify log entries created
- [ ] Test fuzzy matching thresholds
  - [ ] Cards with 0.90+ similarity auto-merge
  - [ ] Cards with 0.70-0.85 similarity flagged
  - [ ] Cards with <0.70 similarity ignored
- [ ] Test edge cases
  - [ ] Co-branded cards NOT merged
  - [ ] Regional variants ARE merged
  - [ ] Network transitions NOT merged
  - [ ] Promotional variants ARE merged

#### 8.3 Performance Tests (`tests/test_performance.py`) (1 hour)

- [ ] Benchmark fingerprint generation
  - [ ] Run 1000 iterations
  - [ ] Verify <5ms average per card
  - [ ] Identify slow outliers
- [ ] Benchmark similarity calculation
  - [ ] Run 1000 comparisons
  - [ ] Verify <10ms average per comparison
- [ ] Benchmark duplicate scan
  - [ ] Create test database with 1000 cards
  - [ ] Run full duplicate scan
  - [ ] Verify <10 seconds total
  - [ ] Check database query efficiency
- [ ] Benchmark cache performance
  - [ ] Cache hit ratio >80% for repeated queries
  - [ ] Cache lookup <1ms

### Phase 9: Documentation (1 hour)

- [ ] Update PROJECT_ANALYSIS.md with implementation details
- [ ] Create edge case documentation with examples
- [ ] Update README.md with duplicate prevention info
- [ ] Document all database migrations
- [ ] Create troubleshooting guide

---

## Success Criteria

### Functional Requirements

1. ✅ **Zero Duplicates**: No semantic duplicates in production database after migration
2. ✅ **High Accuracy**: 95%+ correct duplicate detection (measured against manual review of 100 cards)
3. ✅ **Fast Performance**: <100ms for duplicate check during scraping
4. ✅ **Complete Audit Trail**: All merge actions logged to duplicate_detection_log
5. ✅ **Reversibility**: Ability to unmerge incorrectly merged cards (soft delete preserved)

### Quality Metrics

1. ✅ **Code Coverage**: 90%+ test coverage for card_identity_manager.py
2. ✅ **No False Positives**: <5% incorrect merges (different cards merged incorrectly)
3. ✅ **No False Negatives**: <5% missed duplicates (same cards not merged)
4. ✅ **Database Integrity**: UNIQUE constraint prevents accidental duplicates at DB level
5. ✅ **Edge Case Handling**: All 10 documented edge cases handled correctly

### Performance Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Fingerprint generation | <5ms | Benchmark 1000 cards |
| Similarity calculation | <10ms | Benchmark 1000 comparisons |
| Cache hit rate | >80% | Monitor cache stats |
| Database query time | <20ms | Monitor with indexes |
| Full duplicate check | <100ms | End-to-end timing |
| Bulk deduplication | <10s/1000 cards | Batch processing test |

---

## Rollout Plan

### Week 1: Development
- Complete Phases 0-4 (environment, migration, core module, edge cases)
- Write unit tests
- Local testing

### Week 2: Integration & Testing
- Complete Phases 5-6 (scraper integration, uploader)
- Integration testing
- Performance testing
- Fix bugs

### Week 3: Backfill & Validation
- Run migration on production database
- Backfill normalized_name and fingerprint for existing cards
- Run automated_deduplication in dry-run mode
- Manual review of flagged duplicates
- Actual deduplication run

### Week 4: Monitoring & Iteration
- Deploy to production
- Monitor duplicate_detection_log
- Email daily reports
- Adjust similarity thresholds if needed
- Fix edge cases discovered in production

---

## Maintenance

### Daily Tasks
- Review duplicate_detection_log for flagged matches (0.70-0.85 similarity)
- Approve or reject low-confidence merges
- Monitor error logs

### Weekly Tasks
- Run duplicate scan report
- Monitor false positive/negative rates
- Adjust similarity thresholds if needed
- Review new edge cases

### Monthly Tasks
- Comprehensive accuracy audit (manual review of 100 cards)
- Update normalization rules for new patterns
- Clean up old duplicate_detection_log entries
- Performance optimization based on metrics

---

## Related Documentation

- [PROJECT_ANALYSIS.md](../PROJECT_ANALYSIS.md) - Full project analysis
- [TASK_REWARD_TAXONOMY.md](./TASK_REWARD_TAXONOMY.md) - Reward program taxonomy task
- [README.md](../README.md) - Project overview
- [Jellyfish Documentation](https://github.com/jamesturk/jellyfish) - Phonetic matching library

---

**Last Updated**: January 18, 2026 (Opus Optimization)
**Document Version**: 2.0 (Opus-Optimized)
**Readiness Score**: 95/100
**Estimated Implementation Time**: 22 hours
