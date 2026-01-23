"""
Card Master List Manager
Manages the canonical list of 106 Canadian credit cards.
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from supabase import create_client, Client

from config import load_config
from logger_config import get_logger

logger = get_logger(__name__)


@dataclass
class MasterCard:
    """Represents a card in the master list."""
    id: Optional[str] = None
    canonical_name: str = ""
    canonical_issuer: str = ""
    card_category: str = ""
    name_aliases: List[str] = field(default_factory=list)
    search_terms: List[str] = field(default_factory=list)
    is_active: bool = True
    scrape_status: str = "pending"
    not_found_count: int = 0
    last_scraped_at: Optional[datetime] = None
    last_found_at: Optional[datetime] = None


class CardMasterManager:
    """Manages the canonical card master list in database."""

    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        """Initialize with Supabase credentials."""
        config = load_config()
        self.url = url or os.getenv('SUPABASE_URL') or config.get('supabase_url')
        self.key = key or os.getenv('SUPABASE_KEY') or config.get('supabase_key')

        if not self.url or not self.key:
            raise ValueError("Supabase URL and KEY required")

        self.client: Client = create_client(self.url, self.key)
        logger.info("CardMasterManager initialized")

    def load_from_json(self, json_path: str, clear_existing: bool = False) -> int:
        """
        Load cards from JSON file into database.

        Args:
            json_path: Path to canadian_credit_cards.json
            clear_existing: If True, delete all existing cards first

        Returns:
            Number of cards inserted
        """
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        cards = data.get('credit_cards', [])
        logger.info(f"Loading {len(cards)} cards from {json_path}")

        if clear_existing:
            self.client.table('card_master_list').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
            logger.info("Cleared existing master cards")

        inserted = 0
        for card in cards:
            try:
                card_data = {
                    'canonical_name': card['name'],
                    'canonical_issuer': card['issuer'],
                    'card_category': card.get('category', ''),
                    'search_terms': [card['name'], card['issuer'], card['name'].lower()],
                    'name_aliases': [],
                    'is_active': True,
                    'scrape_status': 'pending'
                }

                # Upsert based on canonical_name
                self.client.table('card_master_list').upsert(
                    card_data,
                    on_conflict='canonical_name'
                ).execute()
                inserted += 1

            except Exception as e:
                logger.error(f"Failed to insert {card['name']}: {e}")

        logger.info(f"Inserted/updated {inserted} master cards")
        return inserted

    def get_all_active_cards(self) -> List[MasterCard]:
        """Get all active cards to scrape."""
        response = self.client.table('card_master_list').select('*').eq('is_active', True).execute()
        return [self._dict_to_master_card(row) for row in response.data]

    def get_cards_by_status(self, status: str) -> List[MasterCard]:
        """Get cards by scrape status (pending, found, not_found, error)."""
        response = self.client.table('card_master_list').select('*').eq('scrape_status', status).eq('is_active', True).execute()
        return [self._dict_to_master_card(row) for row in response.data]

    def get_cards_by_issuer(self, issuer: str) -> List[MasterCard]:
        """Get cards by issuer."""
        response = self.client.table('card_master_list').select('*').eq('canonical_issuer', issuer).eq('is_active', True).execute()
        return [self._dict_to_master_card(row) for row in response.data]

    def get_card_by_id(self, card_id: str) -> Optional[MasterCard]:
        """Get single card by ID."""
        response = self.client.table('card_master_list').select('*').eq('id', card_id).single().execute()
        return self._dict_to_master_card(response.data) if response.data else None

    def get_card_by_name(self, name: str) -> Optional[MasterCard]:
        """Get card by canonical name."""
        response = self.client.table('card_master_list').select('*').eq('canonical_name', name).single().execute()
        return self._dict_to_master_card(response.data) if response.data else None

    def update_scrape_status(self, card_id: str, status: str, found: bool = False):
        """Update card scrape status after scraping attempt."""
        update_data = {
            'scrape_status': status,
            'last_scraped_at': datetime.now().isoformat()
        }

        if found:
            update_data['last_found_at'] = datetime.now().isoformat()
            update_data['not_found_count'] = 0
        elif status == 'not_found':
            # Increment not_found_count
            card = self.get_card_by_id(card_id)
            if card:
                update_data['not_found_count'] = card.not_found_count + 1

        self.client.table('card_master_list').update(update_data).eq('id', card_id).execute()

    def add_name_alias(self, card_id: str, alias: str):
        """Add alternative name found during scraping."""
        card = self.get_card_by_id(card_id)
        if card and alias not in card.name_aliases:
            new_aliases = card.name_aliases + [alias]
            self.client.table('card_master_list').update({'name_aliases': new_aliases}).eq('id', card_id).execute()
            logger.info(f"Added alias '{alias}' to card {card_id}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get master list statistics."""
        all_cards = self.client.table('card_master_list').select('scrape_status, is_active').execute()

        stats = {
            'total': len(all_cards.data),
            'active': sum(1 for c in all_cards.data if c['is_active']),
            'pending': sum(1 for c in all_cards.data if c['scrape_status'] == 'pending'),
            'found': sum(1 for c in all_cards.data if c['scrape_status'] == 'found'),
            'not_found': sum(1 for c in all_cards.data if c['scrape_status'] == 'not_found'),
            'error': sum(1 for c in all_cards.data if c['scrape_status'] == 'error')
        }
        return stats

    def _dict_to_master_card(self, data: Dict) -> MasterCard:
        """Convert database row to MasterCard object."""
        return MasterCard(
            id=data.get('id'),
            canonical_name=data.get('canonical_name', ''),
            canonical_issuer=data.get('canonical_issuer', ''),
            card_category=data.get('card_category', ''),
            name_aliases=data.get('name_aliases', []),
            search_terms=data.get('search_terms', []),
            is_active=data.get('is_active', True),
            scrape_status=data.get('scrape_status', 'pending'),
            not_found_count=data.get('not_found_count', 0),
            last_scraped_at=data.get('last_scraped_at'),
            last_found_at=data.get('last_found_at')
        )


# CLI for testing
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Card Master Manager CLI')
    parser.add_argument('--load', type=str, help='Load cards from JSON file')
    parser.add_argument('--clear', action='store_true', help='Clear existing cards before load')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    parser.add_argument('--list', action='store_true', help='List all cards')
    args = parser.parse_args()

    manager = CardMasterManager()

    if args.load:
        count = manager.load_from_json(args.load, clear_existing=args.clear)
        print(f"Loaded {count} cards")

    if args.stats:
        stats = manager.get_statistics()
        print(f"Statistics: {stats}")

    if args.list:
        cards = manager.get_all_active_cards()
        for card in cards:
            print(f"- {card.canonical_name} ({card.canonical_issuer})")
