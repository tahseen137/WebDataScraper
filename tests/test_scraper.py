"""
Unit tests for credit card scraper parsing logic.
"""

import pytest
from credit_card_scraper import CreditCardScraper, CreditCard, CategoryReward, SignupBonus


class TestCreditCardScraper:
    """Tests for CreditCardScraper class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.scraper = CreditCardScraper(delay=0.1)

    def test_generate_card_key(self):
        """Test card key generation."""
        # Test basic key generation
        key = self.scraper._generate_card_key("TD Aeroplan Visa Infinite", "TD")
        assert key == "td-td-aeroplan-visa-infinite"

        # Test with special characters
        key = self.scraper._generate_card_key("SimplyCash™ Card", "American Express")
        assert key == "american-express-simplycash-card"

        # Test with multiple spaces
        key = self.scraper._generate_card_key("BMO  CashBack   Mastercard", "BMO")
        assert key == "bmo-bmo-cashback-mastercard"

    def test_parse_fee(self):
        """Test annual fee parsing."""
        scraper = CreditCardScraper()

        # Test no fee variations
        assert scraper._parse_fee("No annual fee") == 0.0
        assert scraper._parse_fee("$0") == 0.0
        assert scraper._parse_fee("Free") == 0.0
        assert scraper._parse_fee("no fee") == 0.0

        # Test numeric fees
        assert scraper._parse_fee("$120") == 120.0
        assert scraper._parse_fee("$139.99") == 139.99
        assert scraper._parse_fee("Annual fee: $150") == 150.0
        assert scraper._parse_fee("1,200") == 1200.0

    def test_parse_rate(self):
        """Test reward rate parsing."""
        scraper = CreditCardScraper()

        # Test multiplier format
        rate, unit = scraper._parse_rate("5x points")
        assert rate == 5.0
        assert unit == "multiplier"

        rate, unit = scraper._parse_rate("2X")
        assert rate == 2.0
        assert unit == "multiplier"

        # Test percentage format
        rate, unit = scraper._parse_rate("3% cash back")
        assert rate == 3.0
        assert unit == "percent"

        rate, unit = scraper._parse_rate("1.5 percent")
        assert rate == 1.5
        assert unit == "percent"

        # Test numeric only
        rate, unit = scraper._parse_rate("2.0")
        assert rate == 2.0
        assert unit == "percent"

    def test_get_issuer(self):
        """Test issuer detection from card name."""
        scraper = CreditCardScraper()

        assert scraper._get_issuer("TD Aeroplan Visa") == "TD"
        assert scraper._get_issuer("RBC Avion Visa Infinite") == "RBC"
        assert scraper._get_issuer("BMO CashBack Mastercard") == "BMO"
        assert scraper._get_issuer("CIBC Dividend Visa") == "CIBC"
        assert scraper._get_issuer("Scotiabank Gold Amex") == "Scotiabank"
        assert scraper._get_issuer("American Express Cobalt") == "American Express"
        assert scraper._get_issuer("Amex Platinum") == "American Express"
        assert scraper._get_issuer("Tangerine Money-Back") == "Tangerine"
        assert scraper._get_issuer("PC Financial Mastercard") == "PC Financial"
        assert scraper._get_issuer("Unknown Bank Card") == "Other"

    def test_get_program(self):
        """Test reward program detection."""
        scraper = CreditCardScraper()

        assert scraper._get_program("TD Aeroplan Visa") == "Aeroplan"
        assert scraper._get_program("Scotia Scene+ Card") == "Scene+"
        assert scraper._get_program("RBC Avion Visa") == "Avion"
        assert scraper._get_program("BMO Eclipse Visa") == "BMO Rewards"
        assert scraper._get_program("CIBC Aventura") == "Aventura"
        assert scraper._get_program("Amex Cobalt") == "Membership Rewards"
        assert scraper._get_program("TD Cash Back Visa") == "Cashback"
        assert scraper._get_program("WestJet Mastercard") == "WestJet Rewards"

    def test_get_currency(self):
        """Test reward currency detection."""
        scraper = CreditCardScraper()

        assert scraper._get_currency("Aeroplan", "TD Aeroplan") == "airline_miles"
        assert scraper._get_currency("Avion", "RBC Avion") == "airline_miles"
        assert scraper._get_currency("Cashback", "Cash Back Card") == "cashback"
        assert scraper._get_currency("Points", "Rewards Card") == "points"
        assert scraper._get_currency("Marriott", "Marriott Bonvoy") == "hotel_points"

    def test_get_point_value(self):
        """Test point valuation."""
        scraper = CreditCardScraper()

        assert scraper._get_point_value("cashback", "Cashback") == 1.0
        assert scraper._get_point_value("airline_miles", "Aeroplan") == 1.8
        assert scraper._get_point_value("points", "Membership Rewards") == 2.0
        assert scraper._get_point_value("points", "Scene") == 1.0
        assert scraper._get_point_value("points", "Avion") == 1.5
        assert scraper._get_point_value("points", "TD Rewards") == 0.5

    def test_extract_category_rewards(self):
        """Test category reward extraction from text."""
        scraper = CreditCardScraper()

        # Test single category
        text = "Earn 5x points on groceries"
        rewards = scraper._extract_category_rewards(text)
        assert len(rewards) == 1
        assert rewards[0].category == "groceries"
        assert rewards[0].multiplier == 5.0
        assert rewards[0].reward_unit == "multiplier"

        # Test percentage format
        text = "Get 3% cash back on dining and 2% on gas"
        rewards = scraper._extract_category_rewards(text)
        assert len(rewards) == 2
        assert rewards[0].category == "dining"
        assert rewards[0].multiplier == 3.0
        assert rewards[0].reward_unit == "percent"
        assert rewards[1].category == "gas"
        assert rewards[1].multiplier == 2.0

        # Test multiple categories
        text = "5x on groceries and dining, 3x on entertainment, 2x on travel"
        rewards = scraper._extract_category_rewards(text)
        assert len(rewards) >= 2  # At least groceries and dining

    def test_create_card_from_name(self):
        """Test creating a card object from just the name."""
        scraper = CreditCardScraper()

        card = scraper._create_card_from_name("TD Aeroplan Visa Infinite", "test_source")

        assert card is not None
        assert card.name == "TD Aeroplan Visa Infinite"
        assert card.issuer == "TD"
        assert card.reward_program == "Aeroplan"
        assert card.reward_currency == "airline_miles"
        assert card.point_valuation == 1.8
        assert card.source == "test_source"
        assert card.card_key.startswith("td-")

    def test_create_card_from_name_unknown_issuer(self):
        """Test that unknown issuers return None."""
        scraper = CreditCardScraper()

        card = scraper._create_card_from_name("Unknown Bank Rewards Card", "test_source")

        assert card is None


class TestCreditCardModels:
    """Tests for data model classes."""

    def test_category_reward_creation(self):
        """Test CategoryReward model."""
        reward = CategoryReward(
            category="groceries",
            multiplier=5.0,
            reward_unit="multiplier",
            description="5x on groceries"
        )

        assert reward.category == "groceries"
        assert reward.multiplier == 5.0
        assert reward.reward_unit == "multiplier"
        assert reward.description == "5x on groceries"
        assert reward.has_spend_limit is False
        assert reward.spend_limit is None

    def test_signup_bonus_creation(self):
        """Test SignupBonus model."""
        bonus = SignupBonus(
            bonus_amount=50000,
            bonus_currency="points",
            spend_requirement=3000.0,
            timeframe_days=90
        )

        assert bonus.bonus_amount == 50000
        assert bonus.bonus_currency == "points"
        assert bonus.spend_requirement == 3000.0
        assert bonus.timeframe_days == 90

    def test_credit_card_creation(self):
        """Test CreditCard model."""
        card = CreditCard(
            card_key="td-aeroplan-visa-infinite",
            name="TD Aeroplan Visa Infinite",
            issuer="TD",
            reward_program="Aeroplan",
            reward_currency="airline_miles",
            point_valuation=1.8,
            annual_fee=139.0,
            base_reward_rate=1.0
        )

        assert card.card_key == "td-aeroplan-visa-infinite"
        assert card.name == "TD Aeroplan Visa Infinite"
        assert card.issuer == "TD"
        assert card.annual_fee == 139.0
        assert card.category_rewards == []

    def test_credit_card_with_rewards(self):
        """Test CreditCard with category rewards."""
        rewards = [
            CategoryReward(
                category="groceries",
                multiplier=1.5,
                reward_unit="multiplier",
                description="1.5x on groceries"
            ),
            CategoryReward(
                category="gas",
                multiplier=1.5,
                reward_unit="multiplier",
                description="1.5x on gas"
            )
        ]

        card = CreditCard(
            card_key="td-aeroplan-visa-infinite",
            name="TD Aeroplan Visa Infinite",
            issuer="TD",
            reward_program="Aeroplan",
            reward_currency="airline_miles",
            point_valuation=1.8,
            annual_fee=139.0,
            base_reward_rate=1.0,
            category_rewards=rewards
        )

        assert len(card.category_rewards) == 2
        assert card.category_rewards[0].category == "groceries"
        assert card.category_rewards[1].category == "gas"
