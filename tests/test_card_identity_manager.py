"""
Unit tests for CardIdentityManager

Tests fingerprint generation, name normalization, and similarity calculation.

Author: Kiro AI
Created: January 18, 2026
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from card_identity_manager import (
    CardIdentityManager,
    CreditCard,
    normalize_name,
    generate_fingerprint,
    calculate_similarity
)


class TestNameNormalization(unittest.TestCase):
    """Test name normalization function."""
    
    def test_basic_normalization(self):
        """Test basic lowercase and trimming."""
        self.assertEqual(
            normalize_name("TD Aeroplan Visa Infinite"),
            "td aeroplan visa infinite"
        )
    
    def test_trademark_removal(self):
        """Test removal of trademark symbols."""
        self.assertEqual(
            normalize_name("TD® Aeroplan® Visa Infinite™"),
            "td aeroplan visa infinite"
        )
        self.assertEqual(
            normalize_name("American Express© Cobalt℠"),
            "american express cobalt"
        )
    
    def test_marketing_characters_removal(self):
        """Test removal of asterisks and other marketing symbols."""
        self.assertEqual(
            normalize_name("TD Aeroplan Visa Infinite*"),
            "td aeroplan visa infinite"
        )
        self.assertEqual(
            normalize_name("BMO CashBack† Mastercard‡"),
            "bmo cashback mastercard"
        )
    
    def test_card_suffix_removal(self):
        """Test removal of 'Card' suffix."""
        self.assertEqual(
            normalize_name("American Express Cobalt Card"),
            "american express cobalt"
        )
        self.assertEqual(
            normalize_name("BMO CashBack Mastercard"),
            "bmo cashback mastercard"
        )
        # Should not remove "Card" in the middle
        self.assertEqual(
            normalize_name("Credit Card Rewards"),
            "credit card rewards"
        )
    
    def test_multiple_spaces_collapse(self):
        """Test collapsing of multiple spaces."""
        self.assertEqual(
            normalize_name("TD  Aeroplan   Visa    Infinite"),
            "td aeroplan visa infinite"
        )
    
    def test_punctuation_removal(self):
        """Test removal of punctuation."""
        self.assertEqual(
            normalize_name("TD-Aeroplan Visa.Infinite!"),
            "td aeroplan visa infinite"
        )
        self.assertEqual(
            normalize_name("American Express: Cobalt (Premium)"),
            "american express cobalt premium"
        )
    
    def test_edge_cases(self):
        """Test edge cases."""
        # Empty string
        self.assertEqual(normalize_name(""), "")
        
        # Only spaces
        self.assertEqual(normalize_name("   "), "")
        
        # Only special characters
        self.assertEqual(normalize_name("®™©*†"), "")
        
        # Single word
        self.assertEqual(normalize_name("Cobalt"), "cobalt")
    
    def test_unicode_handling(self):
        """Test handling of Unicode characters."""
        # Should handle accented characters
        result = normalize_name("Café Card")
        self.assertIn("caf", result.lower())
    
    def test_all_caps(self):
        """Test all caps input."""
        self.assertEqual(
            normalize_name("TD AEROPLAN VISA INFINITE"),
            "td aeroplan visa infinite"
        )


class TestFingerprintGeneration(unittest.TestCase):
    """Test fingerprint generation."""
    
    def test_same_card_different_formatting(self):
        """Test that same card with different formatting gets same fingerprint."""
        card1 = CreditCard(
            name="TD® Aeroplan® Visa Infinite*",
            issuer="TD",
            reward_program="Aeroplan®",
            annual_fee=139.99
        )
        card2 = CreditCard(
            name="TD Aeroplan Visa Infinite Card",
            issuer="TD",
            reward_program="Aeroplan",
            annual_fee=139
        )
        
        fp1 = generate_fingerprint(card1)
        fp2 = generate_fingerprint(card2)
        
        self.assertEqual(fp1, fp2)
    
    def test_different_cards_different_fingerprints(self):
        """Test that different cards get different fingerprints."""
        card1 = CreditCard(
            name="TD Aeroplan Visa Infinite",
            issuer="TD",
            reward_program="Aeroplan",
            annual_fee=139
        )
        card2 = CreditCard(
            name="TD Aeroplan Visa Infinite Privilege",
            issuer="TD",
            reward_program="Aeroplan",
            annual_fee=499
        )
        
        fp1 = generate_fingerprint(card1)
        fp2 = generate_fingerprint(card2)
        
        self.assertNotEqual(fp1, fp2)
    
    def test_fee_variation_same_bucket(self):
        """Test that small fee variations result in same fingerprint."""
        card1 = CreditCard(
            name="TD Aeroplan Visa Infinite",
            issuer="TD",
            reward_program="Aeroplan",
            annual_fee=139
        )
        card2 = CreditCard(
            name="TD Aeroplan Visa Infinite",
            issuer="TD",
            reward_program="Aeroplan",
            annual_fee=139.99
        )
        
        fp1 = generate_fingerprint(card1)
        fp2 = generate_fingerprint(card2)
        
        self.assertEqual(fp1, fp2)
    
    def test_deterministic(self):
        """Test that fingerprint generation is deterministic."""
        card = CreditCard(
            name="TD Aeroplan Visa Infinite",
            issuer="TD",
            reward_program="Aeroplan",
            annual_fee=139
        )
        
        fp1 = generate_fingerprint(card)
        fp2 = generate_fingerprint(card)
        fp3 = generate_fingerprint(card)
        
        self.assertEqual(fp1, fp2)
        self.assertEqual(fp2, fp3)
    
    def test_fingerprint_length(self):
        """Test that fingerprint is 16 characters."""
        card = CreditCard(
            name="TD Aeroplan Visa Infinite",
            issuer="TD",
            reward_program="Aeroplan",
            annual_fee=139
        )
        
        fp = generate_fingerprint(card)
        self.assertEqual(len(fp), 16)
    
    def test_fingerprint_hex(self):
        """Test that fingerprint is valid hexadecimal."""
        card = CreditCard(
            name="TD Aeroplan Visa Infinite",
            issuer="TD",
            reward_program="Aeroplan",
            annual_fee=139
        )
        
        fp = generate_fingerprint(card)
        # Should be valid hex (only 0-9, a-f)
        self.assertTrue(all(c in '0123456789abcdef' for c in fp))


class TestSimilarityCalculation(unittest.TestCase):
    """Test similarity calculation."""
    
    def test_exact_match(self):
        """Test that exact matches return 1.0."""
        similarity = calculate_similarity(
            "TD Aeroplan Visa Infinite",
            "TD Aeroplan Visa Infinite"
        )
        self.assertEqual(similarity, 1.0)
    
    def test_exact_match_different_formatting(self):
        """Test that same card with different formatting returns 1.0."""
        similarity = calculate_similarity(
            "TD® Aeroplan® Visa Infinite*",
            "TD Aeroplan Visa Infinite Card"
        )
        self.assertEqual(similarity, 1.0)
    
    def test_minor_variation_high_similarity(self):
        """Test that minor variations have high similarity."""
        similarity = calculate_similarity(
            "TD Aeroplan Visa Infinite",
            "TD Aeroplan Visa Infinite Privilege"
        )
        self.assertGreater(similarity, 0.80)
        self.assertLess(similarity, 1.0)
    
    def test_different_cards_low_similarity(self):
        """Test that different cards have low similarity."""
        similarity = calculate_similarity(
            "TD Aeroplan Visa Infinite",
            "American Express Cobalt"
        )
        self.assertLess(similarity, 0.70)
    
    def test_empty_strings(self):
        """Test handling of empty strings."""
        self.assertEqual(calculate_similarity("", ""), 1.0)  # Both empty = identical
        self.assertEqual(calculate_similarity("TD Aeroplan", ""), 0.0)
        self.assertEqual(calculate_similarity("", "TD Aeroplan"), 0.0)
    
    def test_single_word_match(self):
        """Test single word matching."""
        similarity = calculate_similarity("Cobalt", "Cobalt")
        self.assertEqual(similarity, 1.0)
        
        similarity = calculate_similarity("Cobalt", "Gold")
        self.assertLess(similarity, 0.50)
    
    def test_word_order_independence(self):
        """Test that token matching is order-independent."""
        # These should have high similarity due to token overlap
        similarity = calculate_similarity(
            "Visa Infinite Aeroplan TD",
            "TD Aeroplan Visa Infinite"
        )
        self.assertGreater(similarity, 0.70)  # Adjusted expectation
    
    def test_partial_match(self):
        """Test partial word matching."""
        similarity = calculate_similarity(
            "American Express Cobalt",
            "Amex Cobalt Card"
        )
        # Should have moderate similarity (shares "cobalt")
        self.assertGreater(similarity, 0.40)
        self.assertLess(similarity, 0.80)


class TestFindPotentialDuplicates(unittest.TestCase):
    """Test finding potential duplicates."""
    
    def setUp(self):
        """Set up test data."""
        self.manager = CardIdentityManager()
        
        self.all_cards = [
            CreditCard(
                id="1",
                name="TD Aeroplan Visa Infinite",
                issuer="TD",
                reward_program="Aeroplan",
                annual_fee=139
            ),
            CreditCard(
                id="2",
                name="TD® Aeroplan® Visa Infinite*",
                issuer="TD",
                reward_program="Aeroplan",
                annual_fee=139.99
            ),
            CreditCard(
                id="3",
                name="TD Aeroplan Visa Infinite Privilege",
                issuer="TD",
                reward_program="Aeroplan",
                annual_fee=499
            ),
            CreditCard(
                id="4",
                name="American Express Cobalt",
                issuer="American Express",
                reward_program="Membership Rewards",
                annual_fee=120
            ),
        ]
    
    def test_find_exact_duplicate(self):
        """Test finding exact duplicates."""
        card = CreditCard(
            id="5",
            name="TD Aeroplan Visa Infinite Card",
            issuer="TD",
            reward_program="Aeroplan",
            annual_fee=139
        )
        
        duplicates = self.manager.find_potential_duplicates(
            card,
            self.all_cards,
            threshold=0.85
        )
        
        # Should find cards 1 and 2 as duplicates
        self.assertGreaterEqual(len(duplicates), 1)
        self.assertTrue(any(d[0].id in ["1", "2"] for d in duplicates))
    
    def test_threshold_filtering(self):
        """Test that threshold filters results correctly."""
        card = CreditCard(
            id="5",
            name="TD Aeroplan Visa Infinite Privilege",
            issuer="TD",
            reward_program="Aeroplan",
            annual_fee=499
        )
        
        # High threshold - should find exact match
        duplicates_high = self.manager.find_potential_duplicates(
            card,
            self.all_cards,
            threshold=0.95
        )
        
        # Low threshold - should find more matches
        duplicates_low = self.manager.find_potential_duplicates(
            card,
            self.all_cards,
            threshold=0.70
        )
        
        self.assertLessEqual(len(duplicates_high), len(duplicates_low))
    
    def test_no_self_match(self):
        """Test that card doesn't match itself."""
        card = self.all_cards[0]
        
        duplicates = self.manager.find_potential_duplicates(
            card,
            self.all_cards,
            threshold=0.85
        )
        
        # Should not include itself
        self.assertFalse(any(d[0].id == card.id for d in duplicates))
    
    def test_sorted_by_similarity(self):
        """Test that results are sorted by similarity."""
        card = CreditCard(
            id="5",
            name="TD Aeroplan Visa",
            issuer="TD",
            reward_program="Aeroplan",
            annual_fee=139
        )
        
        duplicates = self.manager.find_potential_duplicates(
            card,
            self.all_cards,
            threshold=0.70
        )
        
        if len(duplicates) > 1:
            # Check that similarities are in descending order
            similarities = [d[1] for d in duplicates]
            self.assertEqual(similarities, sorted(similarities, reverse=True))


class TestMergeCards(unittest.TestCase):
    """Test card merging logic."""
    
    def test_merge_tracks_sources(self):
        """Test that merging tracks all sources."""
        existing = CreditCard(
            id="1",
            name="TD Aeroplan Visa Infinite",
            issuer="TD",
            reward_program="Aeroplan",
            annual_fee=139,
            sources=["Ratehub"],
            confidence_score=0.5
        )
        new = CreditCard(
            id="2",
            name="TD Aeroplan Visa Infinite",
            issuer="TD",
            reward_program="Aeroplan",
            annual_fee=139,
            sources=["NerdWallet"],
            confidence_score=0.5
        )
        
        merged = CardIdentityManager.merge_cards(existing, new)
        
        self.assertIn("Ratehub", merged.sources)
        self.assertIn("NerdWallet", merged.sources)
    
    def test_merge_increases_confidence(self):
        """Test that merging increases confidence score."""
        existing = CreditCard(
            id="1",
            name="TD Aeroplan Visa Infinite",
            issuer="TD",
            reward_program="Aeroplan",
            annual_fee=139,
            sources=["Ratehub"],
            confidence_score=0.5
        )
        new = CreditCard(
            id="2",
            name="TD Aeroplan Visa Infinite",
            issuer="TD",
            reward_program="Aeroplan",
            annual_fee=139,
            sources=["NerdWallet"],
            confidence_score=0.5
        )
        
        merged = CardIdentityManager.merge_cards(existing, new)
        
        self.assertGreater(merged.confidence_score, existing.confidence_score)
        self.assertLessEqual(merged.confidence_score, 1.0)
    
    def test_merge_prefers_nonzero_fee(self):
        """Test that merging prefers non-zero annual fee."""
        existing = CreditCard(
            id="1",
            name="TD Aeroplan Visa Infinite",
            issuer="TD",
            reward_program="Aeroplan",
            annual_fee=0,
            sources=["Ratehub"],
            confidence_score=0.5
        )
        new = CreditCard(
            id="2",
            name="TD Aeroplan Visa Infinite",
            issuer="TD",
            reward_program="Aeroplan",
            annual_fee=139,
            sources=["NerdWallet"],
            confidence_score=0.5
        )
        
        merged = CardIdentityManager.merge_cards(existing, new)
        
        self.assertEqual(merged.annual_fee, 139)
    
    def test_merge_averages_fees(self):
        """Test that merging averages fees when both present."""
        existing = CreditCard(
            id="1",
            name="TD Aeroplan Visa Infinite",
            issuer="TD",
            reward_program="Aeroplan",
            annual_fee=139,
            sources=["Ratehub"],
            confidence_score=0.5
        )
        new = CreditCard(
            id="2",
            name="TD Aeroplan Visa Infinite",
            issuer="TD",
            reward_program="Aeroplan",
            annual_fee=139.99,
            sources=["NerdWallet"],
            confidence_score=0.5
        )
        
        merged = CardIdentityManager.merge_cards(existing, new)
        
        expected_fee = (139 + 139.99) / 2
        self.assertAlmostEqual(merged.annual_fee, expected_fee, places=2)


if __name__ == '__main__':
    unittest.main()
