"""
Comprehensive tests for Reward Program Taxonomy

Tests program matching, taxonomy accuracy, and database integration.

Author: WebDataScraper Team
Created: January 18, 2026
"""

import pytest
from program_matcher import RewardProgramMatcher, match_reward_program, get_program_info
from reward_programs import REWARD_PROGRAMS, get_program_by_name, get_programs_by_currency_type


class TestProgramRegistry:
    """Test reward program registry data structure."""

    def test_all_programs_have_required_fields(self):
        """Verify all programs have required fields."""
        required_fields = [
            'program_family',
            'program_name',
            'currency_type',
            'base_valuation'
        ]

        for program_key, program_data in REWARD_PROGRAMS.items():
            for field in required_fields:
                assert field in program_data, f"Program {program_key} missing {field}"

    def test_program_count(self):
        """Verify we have expected number of programs."""
        assert len(REWARD_PROGRAMS) >= 14, "Should have at least 14 Canadian reward programs"

    def test_currency_types_valid(self):
        """Verify all currency types are valid."""
        valid_types = {
            'cashback',
            'airline_miles',
            'flexible_points',
            'retail_points',
            'entertainment_points',
            'travel_points',
            'hotel_points'
        }

        for program_key, program_data in REWARD_PROGRAMS.items():
            currency_type = program_data['currency_type']
            assert currency_type in valid_types, f"Invalid currency type: {currency_type} in {program_key}"

    def test_base_valuations_reasonable(self):
        """Verify base valuations are within reasonable ranges."""
        for program_key, program_data in REWARD_PROGRAMS.items():
            valuation = program_data['base_valuation']
            assert 0.0 < valuation <= 3.0, f"Unusual valuation {valuation} for {program_key}"

    def test_get_program_by_name(self):
        """Test fetching programs by name."""
        aeroplan = get_program_by_name('aeroplan')
        assert aeroplan is not None
        assert aeroplan['program_name'] == 'Aeroplan'

        # Test non-existent program
        unknown = get_program_by_name('nonexistent')
        assert unknown is None

    def test_get_programs_by_currency_type(self):
        """Test fetching programs by currency type."""
        flexible = get_programs_by_currency_type('flexible_points')
        assert len(flexible) >= 2  # At least Membership Rewards and Avion

        airline = get_programs_by_currency_type('airline_miles')
        assert len(airline) >= 2  # At least Aeroplan and WestJet


class TestProgramMatcher:
    """Test reward program matcher accuracy."""

    def setup_method(self):
        """Set up test fixtures."""
        self.matcher = RewardProgramMatcher()

    # =========================================================================
    # Airline Miles Programs
    # =========================================================================

    def test_match_aeroplan_td(self):
        """Test matching TD Aeroplan cards."""
        program, confidence = self.matcher.match_program("TD Aeroplan Visa Infinite", "TD")
        assert program == 'aeroplan'
        assert confidence >= 0.85

    def test_match_aeroplan_cibc(self):
        """Test matching CIBC Aeroplan cards."""
        program, confidence = self.matcher.match_program("CIBC Aeroplan Visa Infinite Privilege", "CIBC")
        assert program == 'aeroplan'
        assert confidence >= 0.85

    def test_match_aeroplan_amex(self):
        """Test matching Amex Aeroplan cards."""
        program, confidence = self.matcher.match_program("American Express Aeroplan Reserve Card", "American Express")
        assert program == 'aeroplan'
        assert confidence >= 0.85

    def test_match_air_miles(self):
        """Test matching AIR MILES cards."""
        program, confidence = self.matcher.match_program("BMO AIR MILES World Elite Mastercard", "BMO")
        assert program == 'air_miles'
        assert confidence >= 0.70

    def test_match_westjet(self):
        """Test matching WestJet Rewards cards."""
        program, confidence = self.matcher.match_program("RBC WestJet World Elite Mastercard", "RBC")
        assert program == 'westjet_rewards'
        assert confidence >= 0.85

    # =========================================================================
    # Flexible Points Programs
    # =========================================================================

    def test_match_membership_rewards_cobalt(self):
        """Test matching Amex Cobalt (Membership Rewards)."""
        program, confidence = self.matcher.match_program("American Express Cobalt Card", "American Express")
        assert program == 'membership_rewards'
        assert confidence >= 0.85

    def test_match_membership_rewards_gold(self):
        """Test matching Amex Gold (Membership Rewards)."""
        program, confidence = self.matcher.match_program("American Express Gold Rewards Card", "American Express")
        assert program == 'membership_rewards'
        assert confidence >= 0.80

    def test_match_membership_rewards_platinum(self):
        """Test matching Amex Platinum (Membership Rewards)."""
        program, confidence = self.matcher.match_program("American Express Platinum Card", "American Express")
        assert program == 'membership_rewards'
        assert confidence >= 0.85

    def test_match_avion(self):
        """Test matching RBC Avion cards."""
        program, confidence = self.matcher.match_program("RBC Avion Visa Infinite", "RBC")
        assert program == 'avion'
        assert confidence >= 0.85

    def test_match_aventura(self):
        """Test matching CIBC Aventura cards."""
        program, confidence = self.matcher.match_program("CIBC Aventura Visa Infinite", "CIBC")
        assert program == 'aventura'
        assert confidence >= 0.85

    # =========================================================================
    # Retail Points Programs
    # =========================================================================

    def test_match_td_rewards(self):
        """Test matching TD Rewards cards."""
        program, confidence = self.matcher.match_program("TD First Class Travel Visa Infinite", "TD")
        assert program == 'td_rewards'
        assert confidence >= 0.80

    def test_match_bmo_rewards(self):
        """Test matching BMO Rewards cards."""
        program, confidence = self.matcher.match_program("BMO Eclipse Visa Infinite", "BMO")
        assert program == 'bmo_rewards'
        assert confidence >= 0.85

    def test_match_pc_optimum(self):
        """Test matching PC Optimum cards."""
        program, confidence = self.matcher.match_program("PC Financial Mastercard", "PC Financial")
        assert program == 'pc_optimum'
        assert confidence >= 0.85

    def test_match_triangle_rewards(self):
        """Test matching Triangle Rewards cards."""
        program, confidence = self.matcher.match_program("Canadian Tire Triangle World Elite Mastercard", "Canadian Tire")
        assert program == 'triangle_rewards'
        assert confidence >= 0.85

    def test_match_mbna_rewards(self):
        """Test matching MBNA Rewards cards."""
        program, confidence = self.matcher.match_program("MBNA Rewards Platinum Plus Mastercard", "MBNA")
        assert program == 'mbna_rewards'
        assert confidence >= 0.70

    # =========================================================================
    # Entertainment Points Programs
    # =========================================================================

    def test_match_scene_plus(self):
        """Test matching Scene+ cards."""
        program, confidence = self.matcher.match_program("Scotiabank Scene+ Visa Card", "Scotiabank")
        assert program == 'scene_plus'
        assert confidence >= 0.85

    def test_match_scene_plus_gold_amex(self):
        """Test matching Scotiabank Gold Amex (Scene+)."""
        program, confidence = self.matcher.match_program("Scotiabank Gold American Express Card", "Scotiabank")
        assert program == 'scene_plus'
        assert confidence >= 0.70

    # =========================================================================
    # Travel Points Programs
    # =========================================================================

    def test_match_odyssey(self):
        """Test matching Odyssey Rewards cards."""
        program, confidence = self.matcher.match_program("Desjardins Odyssey Visa Infinite", "Desjardins")
        assert program == 'odyssey_rewards'
        assert confidence >= 0.85

    # =========================================================================
    # Cashback Programs
    # =========================================================================

    def test_match_cashback_tangerine(self):
        """Test matching Tangerine cashback card."""
        program, confidence = self.matcher.match_program("Tangerine Money-Back Credit Card", "Tangerine")
        assert program == 'cashback'
        assert confidence >= 0.75

    def test_match_cashback_simplii(self):
        """Test matching Simplii cashback card."""
        program, confidence = self.matcher.match_program("Simplii Financial Cash Back Visa", "Simplii")
        assert program == 'cashback'
        assert confidence >= 0.70

    def test_match_cashback_amex(self):
        """Test matching Amex cashback card."""
        program, confidence = self.matcher.match_program("American Express SimplyCash Card", "American Express")
        assert program == 'cashback'
        assert confidence >= 0.75

    # =========================================================================
    # Exclusion Pattern Tests (Important!)
    # =========================================================================

    def test_amex_aeroplan_not_membership_rewards(self):
        """Test that Amex Aeroplan cards are NOT matched to Membership Rewards."""
        program, confidence = self.matcher.match_program("American Express Aeroplan Card", "American Express")
        assert program == 'aeroplan', "Amex Aeroplan should match to Aeroplan, not Membership Rewards"
        assert program != 'membership_rewards'

    def test_rbc_westjet_not_avion(self):
        """Test that RBC WestJet cards are NOT matched to Avion."""
        program, confidence = self.matcher.match_program("RBC WestJet World Elite Mastercard", "RBC")
        assert program == 'westjet_rewards', "RBC WestJet should match to WestJet, not Avion"
        assert program != 'avion'

    def test_cibc_aeroplan_not_aventura(self):
        """Test that CIBC Aeroplan cards are NOT matched to Aventura."""
        program, confidence = self.matcher.match_program("CIBC Aeroplan Visa", "CIBC")
        assert program == 'aeroplan', "CIBC Aeroplan should match to Aeroplan, not Aventura"
        assert program != 'aventura'

    def test_td_aeroplan_not_td_rewards(self):
        """Test that TD Aeroplan cards are NOT matched to TD Rewards."""
        program, confidence = self.matcher.match_program("TD Aeroplan Visa Infinite", "TD")
        assert program == 'aeroplan', "TD Aeroplan should match to Aeroplan, not TD Rewards"
        assert program != 'td_rewards'

    def test_bmo_air_miles_not_bmo_rewards(self):
        """Test that BMO AIR MILES cards are NOT matched to BMO Rewards."""
        program, confidence = self.matcher.match_program("BMO AIR MILES World Elite", "BMO")
        assert program == 'air_miles', "BMO AIR MILES should match to AIR MILES, not BMO Rewards"
        assert program != 'bmo_rewards'

    # =========================================================================
    # Edge Cases and Unknown Cards
    # =========================================================================

    def test_unknown_card_returns_none(self):
        """Test that unknown cards return None."""
        program, confidence = self.matcher.match_program("Unknown Fake Card", "Unknown Bank")
        assert program is None
        assert confidence == 0.0

    def test_confidence_threshold(self):
        """Test that low confidence matches return None."""
        # A very ambiguous card name
        program, confidence = self.matcher.match_program("Visa Card", "Other")
        assert program is None or confidence >= 0.70


class TestProgramMatcherDetails:
    """Test getting full program details."""

    def setup_method(self):
        """Set up test fixtures."""
        self.matcher = RewardProgramMatcher()

    def test_get_program_details_aeroplan(self):
        """Test fetching Aeroplan program details."""
        details = self.matcher.get_program_details('aeroplan')
        assert details is not None
        assert details['program_name'] == 'Aeroplan'
        assert details['currency_type'] == 'airline_miles'
        assert details['base_valuation'] == 1.8

    def test_get_program_details_membership_rewards(self):
        """Test fetching Membership Rewards program details."""
        details = self.matcher.get_program_details('membership_rewards')
        assert details is not None
        assert details['program_name'] == 'Membership Rewards'
        assert details['currency_type'] == 'flexible_points'
        assert details['base_valuation'] == 2.0

    def test_match_and_get_details_combined(self):
        """Test matching and getting details in one call."""
        program_key, details, confidence = self.matcher.match_and_get_details(
            "TD Aeroplan Visa Infinite", "TD"
        )

        assert program_key == 'aeroplan'
        assert details is not None
        assert details['program_name'] == 'Aeroplan'
        assert confidence >= 0.85


class TestConvenienceFunctions:
    """Test convenience wrapper functions."""

    def test_match_reward_program_function(self):
        """Test match_reward_program() convenience function."""
        program, confidence = match_reward_program("Amex Cobalt Card", "American Express")
        assert program == 'membership_rewards'
        assert confidence >= 0.85

    def test_get_program_info_function(self):
        """Test get_program_info() convenience function."""
        info = get_program_info("RBC Avion Visa Infinite", "RBC")
        assert info is not None
        assert info['program_name'] == 'Avion Rewards'
        assert info['currency_type'] == 'flexible_points'


class TestIssuerNormalization:
    """Test issuer name normalization."""

    def setup_method(self):
        """Set up test fixtures."""
        self.matcher = RewardProgramMatcher()

    def test_normalize_td(self):
        """Test TD issuer normalization."""
        assert self.matcher.normalize_issuer("td") == "TD"
        assert self.matcher.normalize_issuer("Toronto Dominion") == "TD"

    def test_normalize_amex(self):
        """Test Amex issuer normalization."""
        assert self.matcher.normalize_issuer("amex") == "American Express"
        assert self.matcher.normalize_issuer("American Express") == "American Express"

    def test_normalize_rbc(self):
        """Test RBC issuer normalization."""
        assert self.matcher.normalize_issuer("rbc") == "RBC"
        assert self.matcher.normalize_issuer("Royal Bank") == "RBC"

    def test_normalize_scotiabank(self):
        """Test Scotiabank issuer normalization."""
        assert self.matcher.normalize_issuer("scotiabank") == "Scotiabank"
        assert self.matcher.normalize_issuer("scotia") == "Scotiabank"


class TestMatchingAccuracy:
    """Test overall matching accuracy on real card names."""

    def setup_method(self):
        """Set up test fixtures."""
        self.matcher = RewardProgramMatcher()

    def test_batch_matching_accuracy(self):
        """Test accuracy on a batch of real card names."""
        test_cases = [
            # (card_name, issuer, expected_program)
            ("TD Aeroplan Visa Infinite", "TD", "aeroplan"),
            ("CIBC Aventura Visa Infinite", "CIBC", "aventura"),
            ("Amex Cobalt Card", "American Express", "membership_rewards"),
            ("RBC Avion Visa Infinite", "RBC", "avion"),
            ("Scotiabank Scene+ Visa", "Scotiabank", "scene_plus"),
            ("BMO Eclipse Visa Infinite", "BMO", "bmo_rewards"),
            ("PC Financial Mastercard", "PC Financial", "pc_optimum"),
            ("Tangerine Money-Back Credit Card", "Tangerine", "cashback"),
            ("RBC WestJet World Elite", "RBC", "westjet_rewards"),
            ("CIBC Aeroplan Visa", "CIBC", "aeroplan"),
        ]

        correct = 0
        total = len(test_cases)

        for card_name, issuer, expected in test_cases:
            program, confidence = self.matcher.match_program(card_name, issuer)
            if program == expected and confidence >= 0.70:
                correct += 1

        accuracy = (correct / total) * 100
        assert accuracy >= 90.0, f"Expected 90%+ accuracy, got {accuracy:.1f}%"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
