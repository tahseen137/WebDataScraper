"""
Reset database to use only curated seed data (no duplicates, with category rewards)
"""
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv(override=True)

client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

print("=" * 60)
print("RESETTING DATABASE TO SEED DATA")
print("=" * 60)

# Get current count
current = client.table('cards').select('id', count='exact').execute()
print(f"\nCurrent cards in database: {current.count}")

# Delete all category rewards first (foreign key constraint)
print("\nDeleting all category rewards...")
client.table('category_rewards').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()

# Delete all signup bonuses
print("Deleting all signup bonuses...")
client.table('signup_bonuses').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()

# Delete all cards
print("Deleting all cards...")
client.table('cards').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()

# Verify deletion
remaining = client.table('cards').select('id', count='exact').execute()
print(f"Cards remaining: {remaining.count}")

print("\n" + "=" * 60)
print("DATABASE CLEARED")
print("=" * 60)
print("\nNow run: python seed_known_cards.py")
print("This will add 34 curated Canadian cards with full category rewards")
