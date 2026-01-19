"""
Bulk Deduplication Script

One-time script to:
1. Generate fingerprints for all existing cards
2. Find and merge duplicates
3. Update database with normalized names and fingerprints

Usage:
    python bulk_deduplicate.py --dry-run    # Preview changes without committing
    python bulk_deduplicate.py              # Execute deduplication

Author: WebDataScraper Team
Created: January 18, 2026
"""

import argparse
import sys
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from collections import defaultdict

from supabase import create_client
from logger_config import setup_logger, get_logger
from config import load_config
from card_identity_manager import (
    CardFingerprintGenerator,
    SmartDuplicateDetector,
    calculate_advanced_similarity,
    log_duplicate_detection,
    EdgeCaseHandler
)
from enhanced_scraper import CreditCard


class BulkDeduplicator:
    """
    Handles bulk deduplication of existing cards in database.
    """

    def __init__(self, db_client, dry_run: bool = False):
        """
        Initialize bulk deduplicator.

        Args:
            db_client: Supabase client
            dry_run: If True, preview changes without committing
        """
        self.db = db_client
        self.dry_run = dry_run
        self.generator = CardFingerprintGenerator()
        self.detector = SmartDuplicateDetector(db_client)
        self.edge_handler = EdgeCaseHandler()
        self.logger = get_logger(__name__)

        # Statistics
        self.stats = {
            'total_cards': 0,
            'fingerprints_generated': 0,
            'duplicates_found': 0,
            'auto_merged': 0,
            'manual_review': 0,
            'errors': 0
        }

    def run(self) -> Dict[str, int]:
        """
        Execute bulk deduplication process.

        Returns:
            Statistics dictionary
        """
        self.logger.info(f"Starting bulk deduplication (dry_run={self.dry_run})")

        # Step 1: Fetch all cards
        cards = self._fetch_all_cards()
        self.stats['total_cards'] = len(cards)
        self.logger.info(f"Found {len(cards)} cards in database")

        # Step 2: Generate fingerprints for all cards
        fingerprint_map = self._generate_all_fingerprints(cards)

        # Step 3: Find duplicate groups
        duplicate_groups = self._find_duplicate_groups(fingerprint_map)
        self.logger.info(f"Found {len(duplicate_groups)} duplicate groups")

        # Step 4: Merge duplicates
        for fingerprint, card_group in duplicate_groups.items():
            self._merge_duplicate_group(fingerprint, card_group)

        # Step 5: Update normalized names and fingerprints in database
        if not self.dry_run:
            self._update_database_fingerprints(cards, fingerprint_map)

        # Print summary
        self._print_summary()

        return self.stats

    def _fetch_all_cards(self) -> List[Dict]:
        """Fetch all cards from database."""
        try:
            response = self.db.table('cards').select('*').execute()
            return response.data if response.data else []
        except Exception as e:
            self.logger.error(f"Failed to fetch cards: {e}")
            return []

    def _generate_all_fingerprints(
        self,
        cards: List[Dict]
    ) -> Dict[str, Tuple[str, Dict]]:
        """
        Generate fingerprints for all cards.

        Returns:
            Dictionary mapping card_id -> (fingerprint, components)
        """
        fingerprint_map = {}

        for card in cards:
            try:
                fingerprint, components = self.generator.generate_semantic_fingerprint(
                    issuer=card.get('issuer', ''),
                    name=card.get('name', ''),
                    program=card.get('reward_program', ''),
                    annual_fee=card.get('annual_fee', 0.0)
                )

                fingerprint_map[card['id']] = (fingerprint, components)
                self.stats['fingerprints_generated'] += 1

            except Exception as e:
                self.logger.error(f"Failed to generate fingerprint for card {card.get('id')}: {e}")
                self.stats['errors'] += 1

        return fingerprint_map

    def _find_duplicate_groups(
        self,
        fingerprint_map: Dict[str, Tuple[str, Dict]]
    ) -> Dict[str, List[str]]:
        """
        Group cards by fingerprint to find duplicates.

        Returns:
            Dictionary mapping fingerprint -> list of card_ids
        """
        groups = defaultdict(list)

        for card_id, (fingerprint, components) in fingerprint_map.items():
            groups[fingerprint].append(card_id)

        # Filter to only groups with duplicates
        duplicate_groups = {
            fingerprint: card_ids
            for fingerprint, card_ids in groups.items()
            if len(card_ids) > 1
        }

        self.stats['duplicates_found'] = sum(len(group) - 1 for group in duplicate_groups.values())

        return duplicate_groups

    def _merge_duplicate_group(
        self,
        fingerprint: str,
        card_ids: List[str]
    ) -> None:
        """
        Merge a group of duplicate cards.

        Strategy:
        1. Pick the "best" card as the primary (most complete data, most sources)
        2. Merge data from duplicates into primary
        3. Mark duplicates as merged (or delete them)
        4. Log the merge action
        """
        if len(card_ids) < 2:
            return

        self.logger.info(f"Merging {len(card_ids)} cards with fingerprint {fingerprint}")

        # Fetch full card data
        cards = []
        for card_id in card_ids:
            try:
                response = self.db.table('cards').select('*').eq('id', card_id).execute()
                if response.data:
                    cards.append(response.data[0])
            except Exception as e:
                self.logger.error(f"Failed to fetch card {card_id}: {e}")

        if len(cards) < 2:
            return

        # Pick primary card (most complete data)
        primary_card = self._select_primary_card(cards)
        duplicate_cards = [c for c in cards if c['id'] != primary_card['id']]

        # Merge data
        merged_card = self._merge_card_data(primary_card, duplicate_cards)

        # Update database
        if not self.dry_run:
            try:
                # Update primary card with merged data
                self.db.table('cards').update(merged_card).eq('id', primary_card['id']).execute()

                # Delete or mark duplicates as merged
                for dup in duplicate_cards:
                    self.db.table('cards').delete().eq('id', dup['id']).execute()

                    # Log the merge
                    log_duplicate_detection(
                        self.db,
                        card_key_1=primary_card.get('card_key', ''),
                        card_key_2=dup.get('card_key', ''),
                        fingerprint=fingerprint,
                        similarity_score=1.0,  # Exact fingerprint match
                        action_taken='auto_merged',
                        merged_into_id=primary_card['id'],
                        metadata={
                            'bulk_deduplication': True,
                            'duplicate_count': len(duplicate_cards)
                        }
                    )

                self.stats['auto_merged'] += len(duplicate_cards)
                self.logger.info(f"Merged {len(duplicate_cards)} duplicates into card {primary_card['id']}")

            except Exception as e:
                self.logger.error(f"Failed to merge cards: {e}")
                self.stats['errors'] += 1
        else:
            self.logger.info(f"[DRY RUN] Would merge {len(duplicate_cards)} cards into {primary_card['name']}")
            self.stats['auto_merged'] += len(duplicate_cards)

    def _select_primary_card(self, cards: List[Dict]) -> Dict:
        """
        Select the best card from a group to keep as primary.

        Criteria:
        1. Most sources (indicates more data coverage)
        2. Most complete highlights
        3. Most recent update
        """
        def score_card(card: Dict) -> Tuple:
            sources_count = len(card.get('sources', []))
            highlights_count = len(card.get('highlights', []))
            updated_at = card.get('updated_at', '')

            return (sources_count, highlights_count, updated_at)

        return max(cards, key=score_card)

    def _merge_card_data(
        self,
        primary: Dict,
        duplicates: List[Dict]
    ) -> Dict:
        """
        Merge data from duplicate cards into primary card.

        Strategy:
        - Combine sources arrays
        - Merge highlights (deduplicate)
        - Keep primary card's core data (name, issuer, fee, program)
        - Increase confidence score
        """
        merged = primary.copy()

        # Combine sources
        all_sources = set(primary.get('sources', []))
        for dup in duplicates:
            all_sources.update(dup.get('sources', []))
        merged['sources'] = list(all_sources)

        # Merge highlights (deduplicate)
        all_highlights = set(primary.get('highlights', []))
        for dup in duplicates:
            all_highlights.update(dup.get('highlights', []))
        merged['highlights'] = list(all_highlights)

        # Increase confidence score (more sources = higher confidence)
        source_count = len(all_sources)
        merged['confidence_score'] = min(1.0, 0.5 + (source_count * 0.1))

        # Update metadata
        merged['updated_at'] = datetime.utcnow().isoformat()

        return merged

    def _update_database_fingerprints(
        self,
        cards: List[Dict],
        fingerprint_map: Dict[str, Tuple[str, Dict]]
    ) -> None:
        """
        Update all cards in database with normalized names and fingerprints.
        """
        self.logger.info("Updating database with fingerprints and normalized names")

        for card in cards:
            card_id = card['id']
            if card_id not in fingerprint_map:
                continue

            fingerprint, components = fingerprint_map[card_id]

            try:
                update_data = {
                    'fingerprint': fingerprint,
                    'normalized_name': components['name'],
                    'updated_at': datetime.utcnow().isoformat()
                }

                self.db.table('cards').update(update_data).eq('id', card_id).execute()

            except Exception as e:
                self.logger.error(f"Failed to update card {card_id}: {e}")
                self.stats['errors'] += 1

    def _print_summary(self) -> None:
        """Print summary statistics."""
        print("\n" + "=" * 60)
        print("BULK DEDUPLICATION SUMMARY")
        print("=" * 60)
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print(f"Total cards processed: {self.stats['total_cards']}")
        print(f"Fingerprints generated: {self.stats['fingerprints_generated']}")
        print(f"Duplicates found: {self.stats['duplicates_found']}")
        print(f"Auto-merged: {self.stats['auto_merged']}")
        print(f"Manual review needed: {self.stats['manual_review']}")
        print(f"Errors: {self.stats['errors']}")
        print("=" * 60)

        if self.dry_run:
            print("\nThis was a DRY RUN. No changes were made to the database.")
            print("Run without --dry-run to execute deduplication.")
        else:
            print("\nDeduplication complete! Database updated.")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Bulk deduplication of credit card data')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without committing to database'
    )
    args = parser.parse_args()

    # Setup logging
    logger = setup_logger()
    logger.info("Starting bulk deduplication script")

    # Load config
    try:
        config = load_config()
        supabase_url = config.get('supabase_url')
        supabase_key = config.get('supabase_key')

        if not supabase_url or not supabase_key:
            logger.error("Missing Supabase credentials in config")
            sys.exit(1)

        # Create database client
        db = create_client(supabase_url, supabase_key)

    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
        sys.exit(1)

    # Run deduplication
    deduplicator = BulkDeduplicator(db, dry_run=args.dry_run)
    stats = deduplicator.run()

    # Exit with error code if errors occurred
    if stats['errors'] > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
