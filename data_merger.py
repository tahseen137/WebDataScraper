"""
Data Merger
Merges scraped card data from multiple sources using priority-based rules.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from collections import defaultdict

from targeted_scraper import ScrapedCardData
from logger_config import get_logger

logger = get_logger(__name__)


@dataclass
class MergedCardData:
    """Final merged card data ready for database."""
    master_card_id: str
    card_key: str = ""
    name: str = ""
    issuer: str = ""

    # Merged fields
    annual_fee: Optional[float] = None
    base_reward_rate: Optional[float] = None
    base_reward_unit: str = ""
    reward_program: str = ""
    reward_currency: str = ""
    point_valuation: Optional[float] = None

    # Merged complex fields
    category_rewards: List[Dict] = field(default_factory=list)
    signup_bonus: Optional[Dict] = None
    image_url: Optional[str] = None
    apply_url: Optional[str] = None

    # Metadata
    sources: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    merged_at: datetime = field(default_factory=datetime.now)


class DataMerger:
    """Merges scraped data from multiple sources."""

    # Source priority (1 = highest)
    SOURCE_PRIORITY = {
        'creditcardgenius': 1,
        'ratehub': 2,
        'greedyrates': 3,
        'nerdwallet': 4,
        'moneysense': 5
    }

    # Field-specific merge strategies
    MERGE_STRATEGIES = {
        'annual_fee': 'priority',
        'base_reward_rate': 'priority',
        'base_reward_unit': 'priority',
        'reward_program': 'priority',
        'reward_currency': 'priority',
        'point_valuation': 'priority',
        'category_rewards': 'union',
        'signup_bonus': 'most_recent',
        'image_url': 'first_non_null',
        'apply_url': 'priority'
    }

    def merge_card_data(self, master_card_id: str,
                        scraped_records: List[ScrapedCardData],
                        card_name: str = "",
                        card_issuer: str = "") -> MergedCardData:
        """
        Merge multiple scraped records into single card.

        Args:
            master_card_id: ID of the master card
            scraped_records: List of scraped data from different sources
            card_name: Canonical card name
            card_issuer: Canonical issuer name

        Returns:
            MergedCardData with best values from all sources
        """
        if not scraped_records:
            return MergedCardData(master_card_id=master_card_id, name=card_name, issuer=card_issuer)

        # Sort by priority
        sorted_records = sorted(
            scraped_records,
            key=lambda r: self.SOURCE_PRIORITY.get(r.source_name, 99)
        )

        merged = MergedCardData(
            master_card_id=master_card_id,
            name=card_name,
            issuer=card_issuer,
            card_key=self._generate_card_key(card_name, card_issuer)
        )

        # Track which sources contributed
        merged.sources = [r.source_name for r in sorted_records]

        # Merge each field according to its strategy
        for field_name, strategy in self.MERGE_STRATEGIES.items():
            values = self._collect_field_values(sorted_records, field_name)

            if strategy == 'priority':
                merged_value = self._merge_priority(values)
            elif strategy == 'union':
                merged_value = self._merge_union(values)
            elif strategy == 'most_recent':
                merged_value = self._merge_most_recent(values, sorted_records)
            elif strategy == 'first_non_null':
                merged_value = self._merge_first_non_null(values)
            else:
                merged_value = self._merge_priority(values)

            if merged_value is not None:
                setattr(merged, field_name, merged_value)

        # Calculate confidence based on source agreement and count
        merged.confidence_score = self._calculate_confidence(sorted_records)

        logger.info(f"Merged {len(scraped_records)} sources for {card_name}: "
                    f"confidence={merged.confidence_score:.2%}")

        return merged

    def _collect_field_values(self, records: List[ScrapedCardData],
                              field_name: str) -> List[tuple]:
        """Collect (source, value) pairs for a field."""
        values = []
        for record in records:
            value = getattr(record, field_name, None)
            if value is not None and value != "" and value != []:
                values.append((record.source_name, value, record.scraped_at))
        return values

    def _merge_priority(self, values: List[tuple]) -> Any:
        """Use value from highest priority source."""
        if not values:
            return None

        # Already sorted by priority, take first
        return values[0][1]

    def _merge_union(self, values: List[tuple]) -> List[Dict]:
        """Union merge for category rewards - combine all categories."""
        if not values:
            return []

        # Collect all rewards, keyed by category
        rewards_by_category = {}

        for source, rewards_list, _ in values:
            priority = self.SOURCE_PRIORITY.get(source, 99)

            for reward in rewards_list:
                category = reward.get('category', 'unknown')

                if category not in rewards_by_category:
                    rewards_by_category[category] = (priority, reward)
                elif priority < rewards_by_category[category][0]:
                    # Higher priority source, replace
                    rewards_by_category[category] = (priority, reward)

        return [r[1] for r in rewards_by_category.values()]

    def _merge_most_recent(self, values: List[tuple],
                           records: List[ScrapedCardData]) -> Any:
        """Use most recently scraped value."""
        if not values:
            return None

        # Sort by scraped_at descending
        sorted_values = sorted(values, key=lambda v: v[2] if v[2] else datetime.min, reverse=True)
        return sorted_values[0][1]

    def _merge_first_non_null(self, values: List[tuple]) -> Any:
        """Use first non-null value (priority order)."""
        if not values:
            return None
        return values[0][1]

    def _calculate_confidence(self, records: List[ScrapedCardData]) -> float:
        """
        Calculate confidence score based on:
        - Number of sources (more = higher)
        - Match confidence from each source
        - Source priority
        """
        if not records:
            return 0.0

        # Base confidence from number of sources
        source_count_score = min(0.5, len(records) * 0.1)  # Max 0.5 from 5 sources

        # Average match confidence from sources
        avg_match_confidence = sum(r.match_confidence for r in records) / len(records)
        match_score = avg_match_confidence * 0.4  # Max 0.4

        # Priority bonus (higher priority sources weighted more)
        priority_sum = sum(1 / self.SOURCE_PRIORITY.get(r.source_name, 5) for r in records)
        priority_score = min(0.1, priority_sum * 0.02)  # Max 0.1

        return min(1.0, source_count_score + match_score + priority_score)

    def _generate_card_key(self, name: str, issuer: str) -> str:
        """Generate card_key from name and issuer."""
        import re
        # Normalize
        key = f"{issuer}-{name}".lower()
        key = re.sub(r'[^\w\s-]', '', key)
        key = re.sub(r'\s+', '-', key)
        key = re.sub(r'-+', '-', key)
        return key[:100]


# CLI
if __name__ == '__main__':
    # Test merge
    from datetime import datetime

    records = [
        ScrapedCardData(
            master_card_id='test-id',
            source_name='creditcardgenius',
            source_url='test.com',
            match_confidence=0.95,
            annual_fee=139.0,
            base_reward_rate=1.5,
            category_rewards=[{'category': 'groceries', 'multiplier': 5.0}]
        ),
        ScrapedCardData(
            master_card_id='test-id',
            source_name='ratehub',
            source_url='test2.com',
            match_confidence=0.90,
            annual_fee=139.0,
            base_reward_rate=1.0,
            category_rewards=[{'category': 'dining', 'multiplier': 3.0}]
        )
    ]

    merger = DataMerger()
    result = merger.merge_card_data('test-id', records, 'Test Card', 'TD')

    print(f"Merged: {result.name}")
    print(f"  Fee: ${result.annual_fee}")
    print(f"  Rate: {result.base_reward_rate}")
    print(f"  Categories: {result.category_rewards}")
    print(f"  Confidence: {result.confidence_score:.2%}")
