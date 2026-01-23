"""Tests for CardMatcher."""

import pytest
from card_matcher import CardMatcher, MatchResult
from card_master_manager import MasterCard


@pytest.fixture
def sample_master_cards():
    """Sample master cards for testing."""
    return [
        MasterCard(
            id='1',
            canonical_name='TD Aeroplan Visa Infinite',
            canonical_issuer='TD',
            card_category='Airline Miles',
            name_aliases=['TD Aeroplan Visa Infinite Card']
        ),
        MasterCard(
            id='2',
            canonical_name='American Express Cobalt Card',
            canonical_issuer='American Express',
            card_category='Travel Rewards',
            name_aliases=['Amex Cobalt', 'Amex Cobalt Card']
        ),
        MasterCard(
            id='3',
            canonical_name='CIBC Dividend Visa Infinite',
            canonical_issuer='CIBC',
            card_category='Cash Back',
            name_aliases=[]
        ),
        MasterCard(
            id='4',
            canonical_name='Scotiabank Passport Visa Infinite',
            canonical_issuer='Scotiabank',
            card_category='Travel Rewards',
            name_aliases=['Scotia Passport Visa Infinite']
        ),
    ]


@pytest.fixture
def matcher(sample_master_cards):
    """Create matcher with sample cards."""
    return CardMatcher(sample_master_cards)


class TestCardMatcher:
    """Test CardMatcher functionality."""

    def test_exact_match(self, matcher):
        """Test exact name match returns 1.0 confidence."""
        result = matcher.find_best_match('TD Aeroplan Visa Infinite', 'TD')
        assert result.master_card is not None
        assert result.master_card.id == '1'
        assert result.confidence == 1.0
        assert result.match_type == 'exact'

    def test_alias_match(self, matcher):
        """Test alias match returns high confidence."""
        result = matcher.find_best_match('Amex Cobalt', 'American Express')
        assert result.master_card is not None
        assert result.master_card.id == '2'
        assert result.confidence >= 0.95
        assert result.match_type == 'alias'

    def test_fuzzy_match_with_suffix(self, matcher):
        """Test fuzzy match handles 'Card' suffix."""
        result = matcher.find_best_match('TD Aeroplan Visa Infinite Card', 'TD Bank')
        assert result.master_card is not None
        assert result.master_card.id == '1'
        assert result.confidence >= 0.85

    def test_fuzzy_match_with_symbols(self, matcher):
        """Test fuzzy match handles trademark symbols."""
        result = matcher.find_best_match('TD® Aeroplan® Visa Infinite*', 'TD')
        assert result.master_card is not None
        assert result.master_card.id == '1'
        assert result.confidence >= 0.85

    def test_issuer_normalization(self, matcher):
        """Test different issuer name formats."""
        # Amex variations
        result1 = matcher.find_best_match('American Express Cobalt Card', 'Amex')
        result2 = matcher.find_best_match('American Express Cobalt Card', 'American Express')

        assert result1.master_card is not None
        assert result2.master_card is not None
        assert result1.master_card.id == result2.master_card.id

    def test_low_confidence_no_match(self, matcher):
        """Test low confidence returns no match."""
        result = matcher.find_best_match('Random Card Name XYZ', 'Unknown Bank')
        assert result.match_type == 'none'
        assert result.master_card is None
        assert result.confidence < 0.70

    def test_find_all_matches_returns_multiple(self, matcher):
        """Test find_all_matches returns sorted list."""
        results = matcher.find_all_matches('Visa Infinite', '', threshold=0.5)
        assert len(results) > 0
        # Should be sorted by confidence descending
        confidences = [r.confidence for r in results]
        assert confidences == sorted(confidences, reverse=True)

    def test_normalize_issuer_aliases(self, matcher):
        """Test issuer alias normalization."""
        assert matcher._normalize_issuer('American Express') == 'american express'
        assert matcher._normalize_issuer('Amex') == 'american express'
        assert matcher._normalize_issuer('TD Bank') == 'td'
        assert matcher._normalize_issuer('Toronto Dominion') == 'td'
        assert matcher._normalize_issuer('Royal Bank') == 'rbc'

    def test_normalize_card_name(self, matcher):
        """Test card name normalization."""
        # Should remove trademark symbols
        assert '®' not in matcher._normalize_name('TD® Aeroplan®')
        # Should remove 'card' suffix
        assert 'card' not in matcher._normalize_name('Amex Cobalt Card')
        # Should lowercase
        assert matcher._normalize_name('TD AEROPLAN') == matcher._normalize_name('td aeroplan')


class TestMatchResult:
    """Test MatchResult dataclass."""

    def test_match_result_creation(self):
        """Test MatchResult can be created."""
        result = MatchResult(
            master_card=None,
            confidence=0.85,
            match_type='fuzzy',
            normalized_scraped='test',
            normalized_master='test'
        )
        assert result.confidence == 0.85
        assert result.match_type == 'fuzzy'
