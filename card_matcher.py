"""
Card Matcher
Matches scraped card data to master list entries using fuzzy matching.
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Set
import jellyfish

from card_master_manager import MasterCard
from logger_config import get_logger

logger = get_logger(__name__)


@dataclass
class MatchResult:
    """Result of a card match attempt."""
    master_card: Optional[MasterCard]
    confidence: float
    match_type: str  # exact, alias, fuzzy, none
    normalized_scraped: str
    normalized_master: str


class CardMatcher:
    """Matches scraped cards to master list entries."""

    # Issuer name normalization map
    ISSUER_ALIASES = {
        'american express': ['amex', 'americanexpress', 'american express canada'],
        'td': ['td bank', 'td canada trust', 'toronto dominion', 'toronto-dominion'],
        'rbc': ['royal bank', 'royal bank of canada'],
        'cibc': ['canadian imperial bank of commerce', 'canadian imperial'],
        'scotiabank': ['bank of nova scotia', 'scotia', 'bns'],
        'bmo': ['bank of montreal'],
        'national bank': ['national bank of canada', 'banque nationale'],
        'tangerine': ['tangerine bank', 'ing direct'],
        'simplii': ['simplii financial'],
        'pc financial': ['president\'s choice financial', 'presidents choice'],
        'canadian tire': ['triangle', 'ctfs'],
        'rogers bank': ['rogers'],
        'neo financial': ['neo'],
        'desjardins': ['desjardins group', 'mouvement desjardins'],
        'hsbc': ['hsbc bank canada', 'hsbc canada'],
        'mbna': ['mbna canada'],
        'capital one': ['capital one canada'],
        'brim financial': ['brim'],
        'home trust': ['home trust company']
    }

    # Common card name tokens to remove
    REMOVE_TOKENS = {
        'card', 'cards', 'carte', 'cartes', 'credit', 'crédit',
        'the', 'from', 'de', 'du', 'la', 'le', 'les'
    }

    # Tier normalizations
    TIER_NORMALIZATIONS = {
        'infinite privilege': 'infinite_privilege',
        'world elite': 'world_elite',
        'world': 'world',
        'infinite': 'infinite',
        'platinum': 'platinum',
        'gold': 'gold',
        'classic': 'classic'
    }

    def __init__(self, master_cards: List[MasterCard]):
        """Initialize with master card list."""
        self.master_cards = master_cards
        self._build_indexes()
        logger.info(f"CardMatcher initialized with {len(master_cards)} master cards")

    def _build_indexes(self):
        """Build lookup indexes for fast matching."""
        # Index by issuer
        self.by_issuer: Dict[str, List[MasterCard]] = {}
        # Index by normalized name
        self.by_normalized_name: Dict[str, MasterCard] = {}
        # Index by alias
        self.by_alias: Dict[str, MasterCard] = {}
        # Set of all name tokens
        self.all_tokens: Set[str] = set()

        for card in self.master_cards:
            # Index by issuer (normalized)
            issuer_key = self._normalize_issuer(card.canonical_issuer)
            if issuer_key not in self.by_issuer:
                self.by_issuer[issuer_key] = []
            self.by_issuer[issuer_key].append(card)

            # Index by normalized name
            norm_name = self._normalize_name(card.canonical_name)
            self.by_normalized_name[norm_name] = card

            # Index by aliases
            for alias in card.name_aliases:
                norm_alias = self._normalize_name(alias)
                self.by_alias[norm_alias] = card

            # Collect tokens
            self.all_tokens.update(norm_name.split())

    def _normalize_issuer(self, issuer: str) -> str:
        """Normalize issuer name for matching."""
        issuer_lower = issuer.lower().strip()

        # Check if it's a known alias
        for canonical, aliases in self.ISSUER_ALIASES.items():
            if issuer_lower == canonical or issuer_lower in aliases:
                return canonical

        return issuer_lower

    def _normalize_name(self, name: str) -> str:
        """Normalize card name for matching."""
        # Unicode normalization (handle accents)
        name = unicodedata.normalize('NFD', name)
        name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')

        # Lowercase
        name = name.lower()

        # Remove trademark symbols
        name = re.sub(r'[®™©*†‡℠]', '', name)

        # Remove parenthetical content
        name = re.sub(r'\([^)]*\)', '', name)

        # Normalize whitespace and punctuation
        name = re.sub(r'[^\w\s]', ' ', name)
        name = re.sub(r'\s+', ' ', name).strip()

        # Tokenize
        tokens = name.split()

        # Remove common tokens
        tokens = [t for t in tokens if t not in self.REMOVE_TOKENS]

        # Normalize tiers
        name = ' '.join(tokens)
        for tier, norm in sorted(self.TIER_NORMALIZATIONS.items(), key=lambda x: -len(x[0])):
            name = name.replace(tier, norm)

        return name.strip()

    def find_best_match(self, scraped_name: str, scraped_issuer: str = "") -> MatchResult:
        """
        Find best matching master card.

        Args:
            scraped_name: Card name from web scraping
            scraped_issuer: Issuer name from web scraping (optional)

        Returns:
            MatchResult with best match and confidence score
        """
        norm_scraped = self._normalize_name(scraped_name)
        norm_issuer = self._normalize_issuer(scraped_issuer) if scraped_issuer else ""

        # Step 1: Exact match on normalized name
        if norm_scraped in self.by_normalized_name:
            card = self.by_normalized_name[norm_scraped]
            return MatchResult(
                master_card=card,
                confidence=1.0,
                match_type='exact',
                normalized_scraped=norm_scraped,
                normalized_master=self._normalize_name(card.canonical_name)
            )

        # Step 2: Alias match
        if norm_scraped in self.by_alias:
            card = self.by_alias[norm_scraped]
            return MatchResult(
                master_card=card,
                confidence=0.98,
                match_type='alias',
                normalized_scraped=norm_scraped,
                normalized_master=self._normalize_name(card.canonical_name)
            )

        # Step 3: Fuzzy match with issuer filtering
        candidates = self.master_cards
        if norm_issuer and norm_issuer in self.by_issuer:
            # Filter to same issuer (reduces search space by ~90%)
            candidates = self.by_issuer[norm_issuer]

        best_match = None
        best_score = 0.0
        best_norm_master = ""

        for card in candidates:
            norm_master = self._normalize_name(card.canonical_name)
            score = self._calculate_similarity(norm_scraped, norm_master, norm_issuer, self._normalize_issuer(card.canonical_issuer))

            if score > best_score:
                best_score = score
                best_match = card
                best_norm_master = norm_master

        # Determine match type based on score
        if best_score >= 0.85:
            match_type = 'fuzzy'
        elif best_score >= 0.70:
            match_type = 'fuzzy_low'
        else:
            match_type = 'none'
            best_match = None

        return MatchResult(
            master_card=best_match,
            confidence=best_score,
            match_type=match_type,
            normalized_scraped=norm_scraped,
            normalized_master=best_norm_master
        )

    def _calculate_similarity(self, norm_scraped: str, norm_master: str,
                              scraped_issuer: str, master_issuer: str) -> float:
        """
        Calculate weighted similarity score.

        Weights:
        - Exact match: 40%
        - Jaro-Winkler: 30%
        - Token overlap: 20%
        - Issuer match: 10%
        """
        scores = {}

        # 1. Exact match component (40%)
        scores['exact'] = 1.0 if norm_scraped == norm_master else 0.0

        # 2. Jaro-Winkler similarity (30%)
        scores['jaro_winkler'] = jellyfish.jaro_winkler_similarity(norm_scraped, norm_master)

        # 3. Token overlap / Jaccard similarity (20%)
        tokens_scraped = set(norm_scraped.split())
        tokens_master = set(norm_master.split())
        if tokens_scraped or tokens_master:
            intersection = len(tokens_scraped & tokens_master)
            union = len(tokens_scraped | tokens_master)
            scores['token_overlap'] = intersection / union if union > 0 else 0.0
        else:
            scores['token_overlap'] = 0.0

        # 4. Issuer match bonus (10%)
        scores['issuer'] = 1.0 if scraped_issuer == master_issuer else 0.0

        # Weighted sum
        final_score = (
            0.40 * scores['exact'] +
            0.30 * scores['jaro_winkler'] +
            0.20 * scores['token_overlap'] +
            0.10 * scores['issuer']
        )

        return round(final_score, 4)

    def find_all_matches(self, scraped_name: str, scraped_issuer: str = "",
                         threshold: float = 0.70) -> List[MatchResult]:
        """
        Find all master cards matching above threshold.
        Useful for manual review cases.
        """
        norm_scraped = self._normalize_name(scraped_name)
        norm_issuer = self._normalize_issuer(scraped_issuer) if scraped_issuer else ""

        matches = []
        for card in self.master_cards:
            norm_master = self._normalize_name(card.canonical_name)
            score = self._calculate_similarity(
                norm_scraped, norm_master,
                norm_issuer, self._normalize_issuer(card.canonical_issuer)
            )

            if score >= threshold:
                matches.append(MatchResult(
                    master_card=card,
                    confidence=score,
                    match_type='fuzzy' if score >= 0.85 else 'fuzzy_low',
                    normalized_scraped=norm_scraped,
                    normalized_master=norm_master
                ))

        # Sort by confidence descending
        matches.sort(key=lambda m: m.confidence, reverse=True)
        return matches


# Testing
if __name__ == '__main__':
    from card_master_manager import CardMasterManager

    manager = CardMasterManager()
    master_cards = manager.get_all_active_cards()

    matcher = CardMatcher(master_cards)

    # Test cases
    test_cases = [
        ("TD Aeroplan Visa Infinite Card", "TD"),
        ("TD® Aeroplan® Visa Infinite*", "TD Bank"),
        ("American Express Cobalt", "Amex"),
        ("Amex Cobalt Card", "American Express"),
        ("CIBC Dividend Visa Infinite", "CIBC"),
        ("Scotia Momentum Visa Infinite", "Scotiabank"),
        ("BMO CashBack World Elite Mastercard", "BMO"),
        ("Some Random Card Name", "Unknown Bank"),
    ]

    for name, issuer in test_cases:
        result = matcher.find_best_match(name, issuer)
        print(f"\nInput: {name} ({issuer})")
        print(f"  Match: {result.master_card.canonical_name if result.master_card else 'None'}")
        print(f"  Confidence: {result.confidence:.2%}")
        print(f"  Type: {result.match_type}")
