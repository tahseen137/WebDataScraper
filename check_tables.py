"""
Check what tables exist in Supabase database
"""
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv(override=True)

client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

print("=" * 60)
print("CHECKING SUPABASE TABLES")
print("=" * 60)

# List of expected tables based on claude.md
expected_tables = [
    'cards',
    'category_rewards',
    'signup_bonuses',
    'reward_programs',
    'point_valuations',
    'duplicate_detection_log'
]

print("\nTable Status:")
print("-" * 60)

existing_tables = []
missing_tables = []

for table in expected_tables:
    try:
        # Try to query the table
        result = client.table(table).select('id', count='exact').limit(0).execute()
        count = result.count
        existing_tables.append(table)
        print(f"{table:30} [EXISTS] ({count} rows)")
    except Exception as e:
        missing_tables.append(table)
        if 'PGRST205' in str(e):
            print(f"{table:30} [MISSING] Table not found")
        else:
            print(f"{table:30} [ERROR] {str(e)[:50]}")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"Existing tables: {len(existing_tables)}/{len(expected_tables)}")
print(f"Missing tables:  {len(missing_tables)}/{len(expected_tables)}")

if missing_tables:
    print("\n" + "=" * 60)
    print("MISSING TABLES")
    print("=" * 60)
    for table in missing_tables:
        print(f"  - {table}")

    print("\nTo create missing tables, run migrations:")
    if 'reward_programs' in missing_tables or 'point_valuations' in missing_tables:
        print("  python apply_migration.py migrations/004_add_reward_taxonomy.sql")
    if 'duplicate_detection_log' in missing_tables:
        print("  python apply_migration.py migrations/003_add_duplicate_prevention.sql")
else:
    print("\n[OK] All expected tables exist!")
