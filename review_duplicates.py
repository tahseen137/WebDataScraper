"""
Manual Duplicate Review Tool

Interactive CLI tool for reviewing and managing flagged duplicate cards.
Allows admins to approve merges, reject duplicates, or update similarity thresholds.

Usage:
    python review_duplicates.py              # Interactive mode
    python review_duplicates.py --auto-approve 0.90  # Auto-approve above threshold

Author: WebDataScraper Team
Created: January 18, 2026
"""

import argparse
import sys
from typing import Dict, List, Optional
from datetime import datetime

from supabase import create_client
from logger_config import setup_logger, get_logger
from config import DatabaseConfig
from card_identity_manager import calculate_advanced_similarity, log_duplicate_detection


class DuplicateReviewer:
    """Interactive tool for reviewing flagged duplicates."""

    def __init__(self, db_client):
        """
        Initialize reviewer.

        Args:
            db_client: Supabase client
        """
        self.db = db_client
        self.logger = get_logger(__name__)

    def get_pending_reviews(self) -> List[Dict]:
        """
        Fetch all pending manual reviews.

        Returns:
            List of duplicate pairs needing review
        """
        try:
            response = self.db.table('duplicate_detection_log').select('*').eq('action_taken', 'flagged_manual_review').order('similarity_score', desc=True).execute()

            return response.data if response.data else []

        except Exception as e:
            self.logger.error(f"Failed to fetch pending reviews: {e}")
            return []

    def get_card_details(self, card_key: str) -> Optional[Dict]:
        """
        Fetch full card details.

        Args:
            card_key: Card key to fetch

        Returns:
            Card dictionary or None
        """
        try:
            response = self.db.table('cards').select('*').eq('card_key', card_key).execute()

            return response.data[0] if response.data else None

        except Exception as e:
            self.logger.error(f"Failed to fetch card {card_key}: {e}")
            return None

    def display_comparison(self, card1: Dict, card2: Dict, similarity: float) -> None:
        """
        Display side-by-side comparison of two cards.

        Args:
            card1: First card
            card2: Second card
            similarity: Similarity score
        """
        print("\n" + "=" * 80)
        print(f"DUPLICATE REVIEW - Similarity: {similarity:.2%}")
        print("=" * 80)

        # Card names
        print(f"\nCard 1: {card1.get('name', 'N/A')}")
        print(f"Card 2: {card2.get('name', 'N/A')}")

        # Details comparison
        print(f"\n{'Field':<20} {'Card 1':<30} {'Card 2':<30}")
        print("-" * 80)

        fields = ['issuer', 'reward_program', 'annual_fee', 'base_reward_rate', 'sources']

        for field in fields:
            val1 = card1.get(field, 'N/A')
            val2 = card2.get(field, 'N/A')

            # Format sources as count
            if field == 'sources':
                val1 = f"{len(val1)} source(s)" if val1 else "0 sources"
                val2 = f"{len(val2)} source(s)" if val2 else "0 sources"

            print(f"{field:<20} {str(val1):<30} {str(val2):<30}")

        print("-" * 80)

    def approve_merge(self, log_id: str, card1_key: str, card2_key: str, keep_card: int) -> bool:
        """
        Approve merge of duplicate cards.

        Args:
            log_id: Log entry ID
            card1_key: First card key
            card2_key: Second card key
            keep_card: Which card to keep (1 or 2)

        Returns:
            True if successful
        """
        try:
            # Determine which card to keep and which to merge
            if keep_card == 1:
                keep_key = card1_key
                merge_key = card2_key
            else:
                keep_key = card2_key
                merge_key = card1_key

            # Fetch full card data
            keep_card_data = self.get_card_details(keep_key)
            merge_card_data = self.get_card_details(merge_key)

            if not keep_card_data or not merge_card_data:
                self.logger.error("Failed to fetch card data for merge")
                return False

            # Merge sources
            keep_sources = set(keep_card_data.get('sources', []) or [])
            merge_sources = set(merge_card_data.get('sources', []) or [])
            merged_sources = list(keep_sources | merge_sources)

            # Update kept card with merged data
            update_data = {
                'sources': merged_sources,
                'confidence_score': min(1.0, 0.5 + (len(merged_sources) * 0.1)),
                'updated_at': datetime.utcnow().isoformat()
            }

            self.db.table('cards').update(update_data).eq('card_key', keep_key).execute()

            # Delete merged card
            self.db.table('cards').delete().eq('card_key', merge_key).execute()

            # Update log entry
            self.db.table('duplicate_detection_log').update({
                'action_taken': 'manually_merged',
                'merged_into_id': keep_card_data['id'],
                'metadata': {
                    'reviewed_by': 'admin',
                    'reviewed_at': datetime.utcnow().isoformat()
                }
            }).eq('id', log_id).execute()

            self.logger.info(f"Merged {merge_key} into {keep_key}")
            print(f"\n✅ Successfully merged {merge_key} into {keep_key}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to merge cards: {e}")
            print(f"\n❌ Error: {e}")
            return False

    def reject_duplicate(self, log_id: str) -> bool:
        """
        Reject duplicate suggestion (cards are NOT duplicates).

        Args:
            log_id: Log entry ID

        Returns:
            True if successful
        """
        try:
            self.db.table('duplicate_detection_log').update({
                'action_taken': 'manually_rejected',
                'metadata': {
                    'reviewed_by': 'admin',
                    'reviewed_at': datetime.utcnow().isoformat()
                }
            }).eq('id', log_id).execute()

            self.logger.info(f"Rejected duplicate suggestion (log ID: {log_id})")
            print(f"\n✅ Marked as NOT duplicates")
            return True

        except Exception as e:
            self.logger.error(f"Failed to reject duplicate: {e}")
            print(f"\n❌ Error: {e}")
            return False

    def interactive_review(self) -> None:
        """Run interactive review session."""
        print("\n" + "=" * 80)
        print("DUPLICATE REVIEW TOOL - Interactive Mode")
        print("=" * 80)

        pending = self.get_pending_reviews()

        if not pending:
            print("\n✅ No pending reviews!")
            return

        print(f"\nFound {len(pending)} items for review\n")

        for i, log in enumerate(pending, 1):
            card1_key = log.get('card_key_1')
            card2_key = log.get('card_key_2')
            similarity = float(log.get('similarity_score', 0))
            log_id = log.get('id')

            # Fetch card details
            card1 = self.get_card_details(card1_key)
            card2 = self.get_card_details(card2_key)

            if not card1 or not card2:
                print(f"\n⚠️  Skipping item {i}: Could not fetch card data")
                continue

            # Display comparison
            self.display_comparison(card1, card2, similarity)

            # Prompt for action
            print(f"\nReview {i}/{len(pending)}")
            print("Options:")
            print("  1. Merge (keep Card 1, merge Card 2)")
            print("  2. Merge (keep Card 2, merge Card 1)")
            print("  3. NOT duplicates (reject)")
            print("  4. Skip (review later)")
            print("  q. Quit")

            choice = input("\nYour choice: ").strip().lower()

            if choice == '1':
                self.approve_merge(log_id, card1_key, card2_key, keep_card=1)
            elif choice == '2':
                self.approve_merge(log_id, card1_key, card2_key, keep_card=2)
            elif choice == '3':
                self.reject_duplicate(log_id)
            elif choice == '4':
                print("\n⏭️  Skipped")
                continue
            elif choice == 'q':
                print("\n👋 Exiting...")
                break
            else:
                print("\n❌ Invalid choice, skipping")

        print("\n" + "=" * 80)
        print("Review session complete")
        print("=" * 80)

    def auto_approve(self, threshold: float) -> None:
        """
        Auto-approve merges above similarity threshold.

        Args:
            threshold: Minimum similarity score for auto-approval
        """
        print(f"\n🤖 Auto-approving merges with similarity ≥ {threshold:.0%}")

        pending = self.get_pending_reviews()
        approved = 0
        skipped = 0

        for log in pending:
            similarity = float(log.get('similarity_score', 0))

            if similarity >= threshold:
                card1_key = log.get('card_key_1')
                card2_key = log.get('card_key_2')
                log_id = log.get('id')

                # Auto-approve (keep first card by default)
                if self.approve_merge(log_id, card1_key, card2_key, keep_card=1):
                    approved += 1
            else:
                skipped += 1

        print(f"\n✅ Auto-approved: {approved}")
        print(f"⏭️  Skipped: {skipped}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Review and manage duplicate cards')
    parser.add_argument(
        '--auto-approve',
        type=float,
        metavar='THRESHOLD',
        help='Auto-approve merges above similarity threshold (0.0-1.0)'
    )
    args = parser.parse_args()

    # Setup logging
    logger = setup_logger()
    logger.info("Starting duplicate review tool")

    # Load config
    try:
        supabase_url = DatabaseConfig.SUPABASE_URL
        supabase_key = DatabaseConfig.SUPABASE_KEY

        if not supabase_url or not supabase_key:
            logger.error("Missing Supabase credentials in config")
            sys.exit(1)

        # Create database client
        db = create_client(supabase_url, supabase_key)

    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
        sys.exit(1)

    # Create reviewer
    reviewer = DuplicateReviewer(db)

    # Run appropriate mode
    if args.auto_approve:
        if not 0.0 <= args.auto_approve <= 1.0:
            print("❌ Error: Threshold must be between 0.0 and 1.0")
            sys.exit(1)
        reviewer.auto_approve(args.auto_approve)
    else:
        reviewer.interactive_review()


if __name__ == '__main__':
    main()
