"""
Backfill Card Programs Script

Updates existing cards in the database with reward program taxonomy.
Matches each card to its reward program using the smart matcher.

Usage:
    python backfill_card_programs.py              # Dry run (preview only)
    python backfill_card_programs.py --execute    # Execute updates
    python backfill_card_programs.py --execute --limit 100  # Update first 100

Author: WebDataScraper Team
Created: January 18, 2026
"""

import argparse
import sys
from datetime import datetime
from typing import Dict, List, Optional

from supabase import create_client
from logger_config import setup_logger, get_logger
from config import load_config
from program_matcher import RewardProgramMatcher
from reward_programs import REWARD_PROGRAMS


class CardProgramBackfiller:
    """Backfill existing cards with reward program taxonomy."""

    def __init__(self, db_client, dry_run: bool = True):
        """
        Initialize backfiller.

        Args:
            db_client: Supabase client
            dry_run: If True, only preview changes without updating
        """
        self.db = db_client
        self.dry_run = dry_run
        self.logger = get_logger(__name__)
        self.matcher = RewardProgramMatcher()
        self.stats = {
            'total_cards': 0,
            'matched': 0,
            'unmatched': 0,
            'updated': 0,
            'errors': 0,
            'by_program': {}
        }

    def fetch_cards(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Fetch cards from database that need taxonomy updates.

        Args:
            limit: Optional limit on number of cards to fetch

        Returns:
            List of card dictionaries
        """
        try:
            self.logger.info("Fetching cards from database...")

            # Fetch cards without taxonomy (reward_program_id is NULL)
            query = self.db.table('cards').select('*').is_('reward_program_id', 'null')

            if limit:
                query = query.limit(limit)

            response = query.execute()

            cards = response.data or []
            self.logger.info(f"Fetched {len(cards)} cards without taxonomy")
            return cards

        except Exception as e:
            self.logger.error(f"Failed to fetch cards: {e}")
            raise

    def get_program_id(self, program_name: str) -> Optional[str]:
        """
        Get program ID from database by program name.

        Args:
            program_name: Program name to look up

        Returns:
            Program UUID or None
        """
        try:
            response = self.db.table('reward_programs').select('id').eq('program_name', program_name).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]['id']
            else:
                return None

        except Exception as e:
            self.logger.error(f"Failed to fetch program ID for {program_name}: {e}")
            return None

    def match_card_to_program(self, card: Dict) -> Optional[Dict]:
        """
        Match a card to its reward program.

        Args:
            card: Card dictionary

        Returns:
            Program match info or None
        """
        card_name = card.get('name', '')
        issuer = card.get('issuer', '')

        if not card_name:
            return None

        # Use smart matcher
        program_key, details, confidence = self.matcher.match_and_get_details(card_name, issuer)

        if details and confidence >= 0.70:
            # Get program ID from database
            program_id = self.get_program_id(details['program_name'])

            if program_id:
                return {
                    'program_id': program_id,
                    'program_family': details['program_family'],
                    'currency_type': details['currency_type'],
                    'base_valuation': details['base_valuation'],
                    'confidence': confidence
                }

        return None

    def update_card(self, card_id: str, program_info: Dict) -> bool:
        """
        Update a card with program taxonomy.

        Args:
            card_id: Card UUID
            program_info: Program information to update

        Returns:
            True if successful
        """
        if self.dry_run:
            return True  # Don't actually update in dry run mode

        try:
            update_data = {
                'reward_program_id': program_info['program_id'],
                'reward_program_family': program_info['program_family'],
                'currency_type': program_info['currency_type'],
                'updated_at': datetime.utcnow().isoformat()
            }

            self.db.table('cards').update(update_data).eq('id', card_id).execute()
            return True

        except Exception as e:
            self.logger.error(f"Failed to update card {card_id}: {e}")
            return False

    def backfill(self, limit: Optional[int] = None):
        """
        Run backfill process.

        Args:
            limit: Optional limit on number of cards to process
        """
        mode = "DRY RUN" if self.dry_run else "EXECUTION"
        self.logger.info(f"Starting backfill process ({mode})...")

        # Fetch cards
        cards = self.fetch_cards(limit)
        self.stats['total_cards'] = len(cards)

        if not cards:
            self.logger.info("No cards to backfill")
            return

        # Process each card
        for i, card in enumerate(cards, 1):
            card_id = card.get('id')
            card_name = card.get('name', 'Unknown')
            issuer = card.get('issuer', 'Unknown')

            self.logger.info(f"\n[{i}/{len(cards)}] Processing: {card_name} ({issuer})")

            # Match to program
            program_info = self.match_card_to_program(card)

            if program_info:
                self.stats['matched'] += 1
                program_family = program_info['program_family']
                currency_type = program_info['currency_type']
                confidence = program_info['confidence']

                # Track by program
                if program_family not in self.stats['by_program']:
                    self.stats['by_program'][program_family] = 0
                self.stats['by_program'][program_family] += 1

                self.logger.info(f"  ✅ Matched: {program_family}")
                self.logger.info(f"     Currency: {currency_type}")
                self.logger.info(f"     Confidence: {confidence:.0%}")

                # Update card
                if self.update_card(card_id, program_info):
                    self.stats['updated'] += 1
                    action = "Would update" if self.dry_run else "Updated"
                    self.logger.info(f"  {action} card with taxonomy")
                else:
                    self.stats['errors'] += 1

            else:
                self.stats['unmatched'] += 1
                self.logger.warning(f"  ❌ No match found")

    def print_summary(self):
        """Print backfill summary."""
        mode = "DRY RUN PREVIEW" if self.dry_run else "EXECUTION RESULTS"

        print("\n" + "=" * 70)
        print(f"BACKFILL SUMMARY - {mode}")
        print("=" * 70)
        print(f"Total cards processed: {self.stats['total_cards']}")
        print(f"Matched: {self.stats['matched']}")
        print(f"Unmatched: {self.stats['unmatched']}")

        if not self.dry_run:
            print(f"Successfully updated: {self.stats['updated']}")
            print(f"Errors: {self.stats['errors']}")
        else:
            print(f"Would update: {self.stats['matched']}")

        print("\nBy Program:")
        for program, count in sorted(self.stats['by_program'].items(), key=lambda x: -x[1]):
            print(f"  {program}: {count}")

        print("=" * 70)

        # Calculate success rate
        if self.stats['total_cards'] > 0:
            match_rate = (self.stats['matched'] / self.stats['total_cards']) * 100
            print(f"\nMatch Rate: {match_rate:.1f}%")

        if self.dry_run:
            print("\n⚠️  This was a DRY RUN. No changes were made to the database.")
            print("Run with --execute to apply changes.")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Backfill card reward program taxonomy')
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Execute updates (default is dry run)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of cards to process'
    )
    args = parser.parse_args()

    # Setup logging
    logger = setup_logger()
    dry_run = not args.execute

    if dry_run:
        logger.info("Running in DRY RUN mode (preview only)")
    else:
        logger.warning("Running in EXECUTION mode (will update database)")

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

    # Create backfiller
    backfiller = CardProgramBackfiller(db, dry_run=dry_run)

    # Run backfill
    try:
        backfiller.backfill(limit=args.limit)
    except KeyboardInterrupt:
        logger.warning("\nBackfill interrupted by user")
    except Exception as e:
        logger.error(f"Backfill failed: {e}", exc_info=True)
        sys.exit(1)

    # Print summary
    backfiller.print_summary()

    # Exit with appropriate code
    if backfiller.stats['errors'] > 0 and not dry_run:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
