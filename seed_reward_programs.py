"""
Seed Reward Programs Script

Populates the reward_programs and point_valuations tables with
comprehensive Canadian credit card reward program data.

Usage:
    python seed_reward_programs.py              # Seed all programs
    python seed_reward_programs.py --clear      # Clear and reseed

Author: WebDataScraper Team
Created: January 18, 2026
"""

import argparse
import sys
from datetime import datetime

from supabase import create_client
from logger_config import setup_logger, get_logger
from config import load_config
from reward_programs import REWARD_PROGRAMS


class RewardProgramSeeder:
    """Seed reward programs into database."""

    def __init__(self, db_client):
        """
        Initialize seeder.

        Args:
            db_client: Supabase client
        """
        self.db = db_client
        self.logger = get_logger(__name__)
        self.stats = {
            'programs_inserted': 0,
            'valuations_inserted': 0,
            'errors': 0
        }

    def clear_existing_data(self) -> None:
        """Clear all existing reward program data."""
        try:
            # Delete all valuations first (foreign key constraint)
            self.db.table('point_valuations').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()

            # Delete all programs
            self.db.table('reward_programs').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()

            self.logger.info("Cleared existing reward program data")

        except Exception as e:
            self.logger.error(f"Failed to clear existing data: {e}")
            raise

    def seed_programs(self) -> None:
        """Seed all reward programs from registry."""
        self.logger.info(f"Seeding {len(REWARD_PROGRAMS)} reward programs...")

        for program_key, program_data in REWARD_PROGRAMS.items():
            try:
                # Insert program
                program_record = {
                    'program_family': program_data['program_family'],
                    'program_name': program_data['program_name'],
                    'currency_type': program_data['currency_type'],
                    'base_valuation': program_data['base_valuation'],
                    'transfer_partners': program_data.get('transfer_partners', []),
                    'redemption_options': program_data.get('redemption_options', []),
                    'issuer_banks': program_data.get('issuer_banks', []),
                    'currency_name': program_data.get('currency_name', 'points'),
                    'minimum_redemption': program_data.get('minimum_redemption'),
                    'expiry_policy': program_data.get('expiry_policy'),
                    'notes': program_data.get('notes'),
                    'is_active': True,
                    'created_at': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat()
                }

                response = self.db.table('reward_programs').insert(program_record).execute()

                if response.data and len(response.data) > 0:
                    program_id = response.data[0]['id']
                    self.stats['programs_inserted'] += 1
                    self.logger.info(f"✅ Inserted: {program_data['program_name']}")

                    # Insert valuations for this program
                    self._seed_valuations(program_id, program_data)
                else:
                    self.logger.error(f"❌ Failed to insert: {program_data['program_name']}")
                    self.stats['errors'] += 1

            except Exception as e:
                self.logger.error(f"❌ Error inserting {program_data['program_name']}: {e}")
                self.stats['errors'] += 1

    def _seed_valuations(self, program_id: str, program_data: dict) -> None:
        """
        Seed point valuations for a program.

        Args:
            program_id: Program UUID
            program_data: Program data dictionary
        """
        valuations = program_data.get('valuations', {})

        for redemption_type, cents_per_point in valuations.items():
            try:
                valuation_record = {
                    'program_id': program_id,
                    'redemption_type': redemption_type,
                    'cents_per_point': cents_per_point,
                    'minimum_redemption': program_data.get('minimum_redemption'),
                    'notes': f"{redemption_type} redemption for {program_data['program_name']}",
                    'created_at': datetime.utcnow().isoformat()
                }

                self.db.table('point_valuations').insert(valuation_record).execute()
                self.stats['valuations_inserted'] += 1

            except Exception as e:
                self.logger.error(f"   ❌ Error inserting valuation {redemption_type}: {e}")
                self.stats['errors'] += 1

    def print_summary(self) -> None:
        """Print seeding summary."""
        print("\n" + "=" * 70)
        print("REWARD PROGRAM SEEDING SUMMARY")
        print("=" * 70)
        print(f"Programs inserted: {self.stats['programs_inserted']}")
        print(f"Valuations inserted: {self.stats['valuations_inserted']}")
        print(f"Errors: {self.stats['errors']}")
        print("=" * 70)

    def verify_seeding(self) -> bool:
        """
        Verify that seeding was successful.

        Returns:
            True if verification passed
        """
        try:
            # Check program count
            response = self.db.table('reward_programs').select('id').execute()
            program_count = len(response.data) if response.data else 0

            # Check valuation count
            response = self.db.table('point_valuations').select('id').execute()
            valuation_count = len(response.data) if response.data else 0

            print(f"\n✅ Verification:")
            print(f"   Programs in database: {program_count}")
            print(f"   Valuations in database: {valuation_count}")

            expected_programs = len(REWARD_PROGRAMS)
            if program_count >= expected_programs:
                print(f"   ✅ All {expected_programs} programs seeded successfully!")
                return True
            else:
                print(f"   ⚠️  Expected {expected_programs} programs, found {program_count}")
                return False

        except Exception as e:
            self.logger.error(f"Verification failed: {e}")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Seed reward programs into database')
    parser.add_argument(
        '--clear',
        action='store_true',
        help='Clear existing data before seeding'
    )
    args = parser.parse_args()

    # Setup logging
    logger = setup_logger()
    logger.info("Starting reward program seeding")

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

    # Create seeder
    seeder = RewardProgramSeeder(db)

    # Clear if requested
    if args.clear:
        print("\n⚠️  Clearing existing reward program data...")
        seeder.clear_existing_data()

    # Seed programs
    print(f"\n🌱 Seeding {len(REWARD_PROGRAMS)} reward programs...")
    seeder.seed_programs()

    # Print summary
    seeder.print_summary()

    # Verify
    success = seeder.verify_seeding()

    # Exit with appropriate code
    if success and seeder.stats['errors'] == 0:
        print("\n✅ Seeding completed successfully!")
        sys.exit(0)
    else:
        print("\n⚠️  Seeding completed with errors")
        sys.exit(1)


if __name__ == '__main__':
    main()
