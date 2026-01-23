"""
Show Duplicates Report

Non-interactive script to display all pending duplicate reviews.
Useful for reviewing duplicates without making changes.

Usage:
    python show_duplicates_report.py
"""

import sys
from supabase import create_client
from logger_config import setup_logger, get_logger
from config import DatabaseConfig


def main():
    """Generate duplicate report."""
    logger = setup_logger()

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

    # Get pending reviews
    try:
        response = db.table('duplicate_detection_log').select('*').eq(
            'action_taken', 'flagged_manual_review'
        ).order('similarity_score', desc=True).execute()

        pending = response.data if response.data else []

    except Exception as e:
        logger.error(f"Failed to fetch pending reviews: {e}")
        sys.exit(1)

    # Display report
    print("\n" + "=" * 100)
    print("DUPLICATE REVIEW REPORT")
    print("=" * 100)
    print(f"\nTotal pending reviews: {len(pending)}\n")

    if not pending:
        print("No pending reviews found!")
        return

    for i, log in enumerate(pending, 1):
        card1_key = log.get('card_key_1')
        card2_key = log.get('card_key_2')
        similarity = float(log.get('similarity_score', 0))
        log_id = log.get('id')

        # Fetch card details
        try:
            card1_resp = db.table('cards').select('name,issuer,annual_fee,reward_program').eq(
                'card_key', card1_key
            ).execute()
            card2_resp = db.table('cards').select('name,issuer,annual_fee,reward_program').eq(
                'card_key', card2_key
            ).execute()

            card1 = card1_resp.data[0] if card1_resp.data else None
            card2 = card2_resp.data[0] if card2_resp.data else None

            if not card1 or not card2:
                print(f"\n[{i}] ⚠️  Could not fetch card data (Log ID: {log_id})")
                continue

        except Exception as e:
            print(f"\n[{i}] ⚠️  Error fetching cards: {e}")
            continue

        # Display comparison
        print(f"\n[{i}] Similarity: {similarity:.1%} (Log ID: {log_id})")
        print("-" * 100)
        print(f"Card 1: {card1.get('name')}")
        print(f"  Issuer: {card1.get('issuer')}, Fee: ${card1.get('annual_fee', 0)}, Program: {card1.get('reward_program')}")
        print(f"\nCard 2: {card2.get('name')}")
        print(f"  Issuer: {card2.get('issuer')}, Fee: ${card2.get('annual_fee', 0)}, Program: {card2.get('reward_program')}")
        print("-" * 100)

    print("\n" + "=" * 100)
    print("END OF REPORT")
    print("=" * 100)
    print(f"\nTo review interactively, run: python review_duplicates.py")
    print(f"Note: Interactive mode requires manual input for each duplicate pair.\n")


if __name__ == '__main__':
    main()
