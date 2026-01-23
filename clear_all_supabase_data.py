"""
Clear ALL data from Supabase database
WARNING: This will delete all data from all tables!
"""
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv(override=True)

client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

print("=" * 60)
print("WARNING: CLEARING ALL DATA FROM SUPABASE")
print("=" * 60)

# Confirm deletion
response = input("\nThis will DELETE ALL DATA. Type 'DELETE ALL' to confirm: ")
if response != "DELETE ALL":
    print("Aborted.")
    exit(0)

print("\nProceeding with deletion...")

# Delete in order respecting foreign key constraints

# 1. Delete category rewards (references cards)
try:
    print("\n1. Deleting category_rewards...")
    result = client.table('category_rewards').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
    print("   [OK] Deleted category_rewards")
except Exception as e:
    print(f"   [ERROR] Error deleting category_rewards: {e}")

# 2. Delete signup bonuses (references cards)
try:
    print("2. Deleting signup_bonuses...")
    result = client.table('signup_bonuses').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
    print("   [OK] Deleted signup_bonuses")
except Exception as e:
    print(f"   [ERROR] Error deleting signup_bonuses: {e}")

# 3. Delete duplicate detection log
try:
    print("3. Deleting duplicate_detection_log...")
    result = client.table('duplicate_detection_log').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
    print("   [OK] Deleted duplicate_detection_log")
except Exception as e:
    print(f"   [ERROR] Error deleting duplicate_detection_log: {e}")

# 4. Delete cards (references reward_programs)
try:
    print("4. Deleting cards...")
    result = client.table('cards').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
    print("   [OK] Deleted cards")
except Exception as e:
    print(f"   [ERROR] Error deleting cards: {e}")

# 5. Delete point valuations (references reward_programs)
try:
    print("5. Deleting point_valuations...")
    result = client.table('point_valuations').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
    print("   [OK] Deleted point_valuations")
except Exception as e:
    print(f"   [ERROR] Error deleting point_valuations: {e}")

# 6. Delete reward programs (no dependencies)
try:
    print("6. Deleting reward_programs...")
    result = client.table('reward_programs').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
    print("   [OK] Deleted reward_programs")
except Exception as e:
    print(f"   [ERROR] Error deleting reward_programs: {e}")

# Verify all tables are empty
print("\n" + "=" * 60)
print("VERIFICATION")
print("=" * 60)

tables = ['cards', 'category_rewards', 'signup_bonuses', 'reward_programs',
          'point_valuations', 'duplicate_detection_log']

for table in tables:
    try:
        count = client.table(table).select('id', count='exact').execute().count
        status = "[EMPTY]" if count == 0 else f"[WARNING] {count} rows remaining"
        print(f"{table:30} {status}")
    except Exception as e:
        print(f"{table:30} [ERROR] Error checking: {e}")

print("\n" + "=" * 60)
print("DATABASE CLEARED")
print("=" * 60)
print("\nNext steps:")
print("1. Run: python seed_reward_programs.py --clear")
print("2. Run: python seed_cards.py (if available)")
print("3. Or run: python enhanced_scraper.py")
