"""
Reward Program Matcher - Smart Detection from Card Names

Intelligent pattern matching to identify reward programs from credit card names.
Uses multi-pattern matching, issuer context, and fuzzy logic to accurately
determine which reward program a card belongs to.

Author: WebDataScraper Team
Created: January 18, 2026
"""

import re
from typing import Optional, Tuple, Dict
from logger_config import get_logger
from reward_programs import REWARD_PROGRAMS, get_program_by_name


logger = get_logger(__name__)


# ============================================================================
# PATTERN DEFINITIONS
# ============================================================================

# Comprehensive pattern matching for each program
# Patterns are ordered by specificity (most specific first)

PROGRAM_PATTERNS = {
    # Airline Miles Programs
    'aeroplan': {
        'patterns': [
            r'aeroplan',
            r'td.*aeroplan',
            r'cibc.*aeroplan',
            r'amex.*aeroplan'
        ],
        'exclude_patterns': [],
        'issuer_hints': ['TD', 'CIBC', 'American Express']
    },

    'air_miles': {
        'patterns': [
            r'air\s*miles',
            r'airmiles',
            r'bmo.*air\s*miles'
        ],
        'exclude_patterns': [],
        'issuer_hints': ['BMO', 'American Express']
    },

    'westjet_rewards': {
        'patterns': [
            r'westjet',
            r'west\s*jet',
            r'rbc.*westjet'
        ],
        'exclude_patterns': [],
        'issuer_hints': ['RBC', 'WestJet']
    },

    # Flexible Points Programs
    'membership_rewards': {
        'patterns': [
            r'membership\s*rewards',
            r'amex.*cobalt',
            r'amex.*gold(?!en)',  # Gold but not Golden
            r'amex.*platinum',
            r'american\s*express.*cobalt',
            r'american\s*express.*gold',
            r'american\s*express.*platinum'
        ],
        'exclude_patterns': [
            r'aeroplan',  # Amex Aeroplan cards are NOT Membership Rewards
            r'marriott'
        ],
        'issuer_hints': ['American Express', 'Amex']
    },

    'avion': {
        'patterns': [
            r'avion',
            r'rbc.*avion'
        ],
        'exclude_patterns': [
            r'westjet'  # RBC WestJet is not Avion
        ],
        'issuer_hints': ['RBC']
    },

    'aventura': {
        'patterns': [
            r'aventura',
            r'cibc.*aventura'
        ],
        'exclude_patterns': [
            r'aeroplan'  # CIBC Aeroplan is not Aventura
        ],
        'issuer_hints': ['CIBC']
    },

    # Retail Points Programs
    'td_rewards': {
        'patterns': [
            r'td\s*rewards',
            r'td.*first\s*class',
            r'td.*travel',
            r'td.*cash.*back.*visa\s*infinite'  # Some TD cards have rewards
        ],
        'exclude_patterns': [
            r'aeroplan',  # TD Aeroplan is NOT TD Rewards
            r'cash\s*back\s*visa(?!.*infinite)'  # Pure cashback is different
        ],
        'issuer_hints': ['TD']
    },

    'bmo_rewards': {
        'patterns': [
            r'bmo\s*rewards',
            r'bmo.*eclipse',
            r'bmo.*ascend'
        ],
        'exclude_patterns': [
            r'air\s*miles',  # BMO Air Miles is separate
            r'cash\s*back'
        ],
        'issuer_hints': ['BMO']
    },

    'pc_optimum': {
        'patterns': [
            r'pc\s*optimum',
            r'president.*choice',
            r'presidents.*choice',
            r'pc\s*financial',
            r'pc\s*mastercard'
        ],
        'exclude_patterns': [],
        'issuer_hints': ['PC Financial', 'Presidents Choice']
    },

    'triangle_rewards': {
        'patterns': [
            r'triangle',
            r'canadian\s*tire',
            r'ct\s*money'
        ],
        'exclude_patterns': [],
        'issuer_hints': ['Canadian Tire']
    },

    'mbna_rewards': {
        'patterns': [
            r'mbna\s*rewards',
            r'mbna.*platinum'
        ],
        'exclude_patterns': [],
        'issuer_hints': ['MBNA']
    },

    # Entertainment Points Programs
    'scene_plus': {
        'patterns': [
            r'scene\+',
            r'scene\s*plus',
            r'scene',
            r'scotiabank.*scene',
            r'scotia.*scene',
            r'scotiabank.*gold.*(?:amex|american\s*express)',  # Scotiabank Gold Amex is Scene+
            r'scotia.*gold.*(?:amex|american\s*express)'
        ],
        'exclude_patterns': [],
        'issuer_hints': ['Scotiabank', 'Scotia']
    },

    # Travel Points Programs
    'odyssey_rewards': {
        'patterns': [
            r'odyssey',
            r'desjardins.*odyssey'
        ],
        'exclude_patterns': [],
        'issuer_hints': ['Desjardins']
    },

    # Cashback Programs
    'cashback': {
        'patterns': [
            r'cash\s*back',
            r'cashback',
            r'money.*back',
            r'tangerine',
            r'simply\s*cash',  # Amex SimplyCash
            r'dividend'  # CIBC Dividend cashback cards
        ],
        'exclude_patterns': [
            r'visa\s*infinite.*rewards',  # Some cards mix terms
            r'world\s*elite.*rewards'
        ],
        'issuer_hints': ['All']
    }
}


# ============================================================================
# ISSUER NORMALIZATION
# ============================================================================

ISSUER_NORMALIZATIONS = {
    'td': 'TD',
    'toronto dominion': 'TD',
    'rbc': 'RBC',
    'royal bank': 'RBC',
    'bmo': 'BMO',
    'bank of montreal': 'BMO',
    'cibc': 'CIBC',
    'canadian imperial': 'CIBC',
    'amex': 'American Express',
    'american express': 'American Express',
    'scotiabank': 'Scotiabank',
    'scotia': 'Scotiabank',
    'desjardins': 'Desjardins',
    'mbna': 'MBNA',
    'pc financial': 'PC Financial',
    'presidents choice': 'PC Financial',
    'canadian tire': 'Canadian Tire',
    'tangerine': 'Tangerine',
    'westjet': 'WestJet'
}


# ============================================================================
# PROGRAM MATCHER CLASS
# ============================================================================

class RewardProgramMatcher:
    """
    Smart matcher for detecting reward programs from card names.

    Uses multi-pattern matching, issuer context, and exclusion rules
    to accurately identify programs.
    """

    def __init__(self):
        """Initialize matcher."""
        self.logger = get_logger(__name__)

    def normalize_issuer(self, issuer: str) -> str:
        """
        Normalize issuer name.

        Args:
            issuer: Raw issuer name

        Returns:
            Normalized issuer name
        """
        if not issuer:
            return ''

        issuer_lower = issuer.lower().strip()
        return ISSUER_NORMALIZATIONS.get(issuer_lower, issuer)

    def match_program(
        self,
        card_name: str,
        issuer: Optional[str] = None
    ) -> Tuple[Optional[str], float]:
        """
        Match card name to reward program.

        Args:
            card_name: Full card name
            issuer: Card issuer (optional, improves accuracy)

        Returns:
            Tuple of (program_key, confidence_score)
            Returns (None, 0.0) if no match found

        Examples:
            >>> matcher = RewardProgramMatcher()
            >>> matcher.match_program("TD Aeroplan Visa Infinite", "TD")
            ('aeroplan', 0.95)

            >>> matcher.match_program("Amex Cobalt Card", "American Express")
            ('membership_rewards', 0.90)

            >>> matcher.match_program("Unknown Rewards Card", "Unknown")
            (None, 0.0)
        """
        if not card_name:
            return (None, 0.0)

        # Normalize inputs
        name_lower = card_name.lower().strip()
        normalized_issuer = self.normalize_issuer(issuer) if issuer else None

        best_match = None
        best_score = 0.0

        # Try to match each program
        for program_key, pattern_data in PROGRAM_PATTERNS.items():
            score = self._calculate_match_score(
                name_lower,
                normalized_issuer,
                pattern_data
            )

            if score > best_score:
                best_score = score
                best_match = program_key

        # Return match only if confidence is high enough
        if best_score >= 0.70:
            self.logger.info(f"Matched '{card_name}' to '{best_match}' (confidence: {best_score:.2f})")
            return (best_match, best_score)
        else:
            self.logger.warning(f"No confident match for '{card_name}' (best: {best_match}, score: {best_score:.2f})")
            return (None, 0.0)

    def _calculate_match_score(
        self,
        name_lower: str,
        issuer: Optional[str],
        pattern_data: Dict
    ) -> float:
        """
        Calculate match score for a program.

        Args:
            name_lower: Lowercase card name
            issuer: Normalized issuer
            pattern_data: Pattern data for the program

        Returns:
            Match score (0.0 - 1.0)
        """
        score = 0.0

        # Check exclude patterns first (disqualifying)
        for exclude_pattern in pattern_data.get('exclude_patterns', []):
            if re.search(exclude_pattern, name_lower, re.IGNORECASE):
                return 0.0  # Excluded, no match

        # Check inclusion patterns
        pattern_matches = 0
        for pattern in pattern_data['patterns']:
            if re.search(pattern, name_lower, re.IGNORECASE):
                pattern_matches += 1

        if pattern_matches == 0:
            return 0.0  # No pattern matched

        # Base score from pattern match
        score = 0.70  # Minimum score if pattern matches

        # Bonus for multiple pattern matches (more specific)
        if pattern_matches > 1:
            score += 0.10

        # Bonus for issuer match
        if issuer:
            issuer_hints = pattern_data.get('issuer_hints', [])
            if any(hint in issuer for hint in issuer_hints):
                score += 0.15
            elif 'All' in issuer_hints:
                score += 0.05  # Small bonus for generic programs like cashback

        return min(1.0, score)

    def get_program_details(self, program_key: str) -> Optional[Dict]:
        """
        Get full program details by key.

        Args:
            program_key: Program key (e.g., 'aeroplan', 'membership_rewards')

        Returns:
            Program details dictionary or None
        """
        return get_program_by_name(program_key)

    def match_and_get_details(
        self,
        card_name: str,
        issuer: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[Dict], float]:
        """
        Match program and return full details in one call.

        Args:
            card_name: Full card name
            issuer: Card issuer (optional)

        Returns:
            Tuple of (program_key, program_details, confidence_score)
        """
        program_key, confidence = self.match_program(card_name, issuer)

        if program_key:
            details = self.get_program_details(program_key)
            return (program_key, details, confidence)
        else:
            return (None, None, 0.0)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def match_reward_program(
    card_name: str,
    issuer: Optional[str] = None
) -> Tuple[Optional[str], float]:
    """
    Convenience function to match a reward program.

    Args:
        card_name: Full card name
        issuer: Card issuer (optional)

    Returns:
        Tuple of (program_key, confidence_score)

    Example:
        >>> program, confidence = match_reward_program("TD Aeroplan Visa Infinite", "TD")
        >>> print(f"Program: {program}, Confidence: {confidence:.0%}")
        Program: aeroplan, Confidence: 95%
    """
    matcher = RewardProgramMatcher()
    return matcher.match_program(card_name, issuer)


def get_program_info(
    card_name: str,
    issuer: Optional[str] = None
) -> Optional[Dict]:
    """
    Get complete program information for a card.

    Args:
        card_name: Full card name
        issuer: Card issuer (optional)

    Returns:
        Program details dictionary or None

    Example:
        >>> info = get_program_info("Amex Cobalt Card", "American Express")
        >>> print(f"Program: {info['program_name']}")
        >>> print(f"Base Value: {info['base_valuation']}¢")
        Program: Membership Rewards
        Base Value: 2.0¢
    """
    matcher = RewardProgramMatcher()
    _, details, _ = matcher.match_and_get_details(card_name, issuer)
    return details


if __name__ == '__main__':
    # Test cases
    print("=" * 70)
    print("REWARD PROGRAM MATCHER - Test Cases")
    print("=" * 70)

    test_cases = [
        ("TD Aeroplan Visa Infinite", "TD"),
        ("CIBC Aventura Visa Infinite", "CIBC"),
        ("Amex Cobalt Card", "American Express"),
        ("RBC Avion Visa Infinite", "RBC"),
        ("Scotiabank Scene+ Visa", "Scotiabank"),
        ("BMO Eclipse Visa Infinite", "BMO"),
        ("PC Financial Mastercard", "PC Financial"),
        ("Tangerine Money-Back Credit Card", "Tangerine"),
        ("Unknown Rewards Card", "Unknown Bank")
    ]

    matcher = RewardProgramMatcher()

    for card_name, issuer in test_cases:
        program_key, details, confidence = matcher.match_and_get_details(card_name, issuer)

        print(f"\nCard: {card_name}")
        print(f"Issuer: {issuer}")

        if details:
            print(f"✅ Matched: {details['program_name']}")
            print(f"   Type: {details['currency_type']}")
            print(f"   Value: {details['base_valuation']}¢")
            print(f"   Confidence: {confidence:.0%}")
        else:
            print(f"❌ No match found")
