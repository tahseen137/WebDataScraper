"""Tests for DataMerger."""

import pytest
from datetime import datetime, timedelta
from data_merger import DataMerger, MergedCardData
from targeted_scraper import ScrapedCardData


@pytest.fixture
def merger():
    """Create DataMerger instance."""
    return DataMerger()


@pytest.fixture
def sample_scraped_data():
    """Sample scraped data from multiple sources."""
    now = datetime.now()
    return [
        ScrapedCardData(
            master_card_id='test-id',
            source_name='creditcardgenius',
            source_url='https://creditcardgenius.ca/test',
            match_confidence=0.95,
            scraped_at=now,
            annual_fee=139.0,
            base_reward_rate=1.5,
            base_reward_unit='multiplier',
            category_rewards=[
                {'category': 'groceries', 'multiplier': 5.0, 'reward_unit': 'multiplier'},
                {'category': 'dining', 'multiplier': 3.0, 'reward_unit': 'multiplier'}
            ],
            signup_bonus={'bonus_amount': 20000, 'spend_requirement': 1000}
        ),
        ScrapedCardData(
            master_card_id='test-id',
            source_name='ratehub',
            source_url='https://ratehub.ca/test',
            match_confidence=0.90,
            scraped_at=now - timedelta(hours=1),
            annual_fee=139.0,
            base_reward_rate=1.0,  # Different value
            base_reward_unit='multiplier',
            category_rewards=[
                {'category': 'groceries', 'multiplier': 4.0, 'reward_unit': 'multiplier'},  # Different
                {'category': 'gas', 'multiplier': 2.0, 'reward_unit': 'multiplier'}  # New category
            ],
            signup_bonus={'bonus_amount': 25000, 'spend_requirement': 1500}  # Different
        ),
        ScrapedCardData(
            master_card_id='test-id',
            source_name='moneysense',
            source_url='https://moneysense.ca/test',
            match_confidence=0.75,
            scraped_at=now - timedelta(days=7),
            annual_fee=120.0,  # Different (outdated)
            base_reward_rate=1.5,
            base_reward_unit='multiplier',
            category_rewards=[],
            signup_bonus=None
        )
    ]


class TestDataMerger:
    """Test DataMerger functionality."""

    def test_priority_merge_annual_fee(self, merger, sample_scraped_data):
        """Test annual_fee uses highest priority source."""
        result = merger.merge_card_data('test-id', sample_scraped_data, 'Test Card', 'TD')

        # CreditCardGenius has priority 1, should use its value (139)
        assert result.annual_fee == 139.0

    def test_priority_merge_reward_rate(self, merger, sample_scraped_data):
        """Test base_reward_rate uses highest priority source."""
        result = merger.merge_card_data('test-id', sample_scraped_data, 'Test Card', 'TD')

        # CreditCardGenius value should win
        assert result.base_reward_rate == 1.5

    def test_union_merge_category_rewards(self, merger, sample_scraped_data):
        """Test category_rewards uses union with priority for conflicts."""
        result = merger.merge_card_data('test-id', sample_scraped_data, 'Test Card', 'TD')

        categories = {r['category'] for r in result.category_rewards}

        # Should have union of all categories
        assert 'groceries' in categories
        assert 'dining' in categories
        assert 'gas' in categories

        # For groceries conflict, should use CCG value (5.0, not 4.0)
        groceries = next(r for r in result.category_rewards if r['category'] == 'groceries')
        assert groceries['multiplier'] == 5.0

    def test_most_recent_signup_bonus(self, merger, sample_scraped_data):
        """Test signup_bonus uses most recent source."""
        result = merger.merge_card_data('test-id', sample_scraped_data, 'Test Card', 'TD')

        # Most recent is CreditCardGenius (now)
        assert result.signup_bonus is not None
        assert result.signup_bonus['bonus_amount'] == 20000

    def test_sources_tracking(self, merger, sample_scraped_data):
        """Test all sources are tracked."""
        result = merger.merge_card_data('test-id', sample_scraped_data, 'Test Card', 'TD')

        assert 'creditcardgenius' in result.sources
        assert 'ratehub' in result.sources
        assert 'moneysense' in result.sources

    def test_confidence_calculation(self, merger, sample_scraped_data):
        """Test confidence score is reasonable."""
        result = merger.merge_card_data('test-id', sample_scraped_data, 'Test Card', 'TD')

        # With 3 sources and high match confidences, should be decent
        assert 0.5 <= result.confidence_score <= 1.0

    def test_empty_records(self, merger):
        """Test handling of empty records list."""
        result = merger.merge_card_data('test-id', [], 'Test Card', 'TD')

        assert result.master_card_id == 'test-id'
        assert result.name == 'Test Card'
        assert result.annual_fee is None
        assert result.category_rewards == []

    def test_single_source(self, merger, sample_scraped_data):
        """Test with single source."""
        result = merger.merge_card_data('test-id', [sample_scraped_data[0]], 'Test Card', 'TD')

        assert result.annual_fee == 139.0
        assert len(result.sources) == 1
        assert result.sources[0] == 'creditcardgenius'

    def test_card_key_generation(self, merger, sample_scraped_data):
        """Test card_key is properly generated."""
        result = merger.merge_card_data('test-id', sample_scraped_data, 'TD Aeroplan Visa Infinite', 'TD')

        assert result.card_key == 'td-td-aeroplan-visa-infinite'
        assert '-' in result.card_key
        assert result.card_key.islower() or result.card_key.replace('-', '').islower()


class TestMergedCardData:
    """Test MergedCardData dataclass."""

    def test_merged_card_data_defaults(self):
        """Test MergedCardData default values."""
        data = MergedCardData(master_card_id='test')

        assert data.master_card_id == 'test'
        assert data.category_rewards == []
        assert data.sources == []
        assert data.confidence_score == 0.0
