"""
Simple migration applier without unicode issues
"""
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv(override=True)

client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

print("=" * 60)
print("APPLYING MIGRATIONS")
print("=" * 60)

# Migration files to apply
migrations = [
    'migrations/003_add_duplicate_prevention.sql',
    'migrations/004_add_reward_taxonomy.sql'
]

for migration_file in migrations:
    print(f"\nApplying: {migration_file}")

    try:
        # Read SQL file
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql = f.read()

        # Execute SQL via Supabase RPC or direct SQL
        # Note: Supabase client doesn't directly support raw SQL execution
        # We need to use the underlying PostgreSQL connection
        print(f"  [INFO] SQL file read successfully ({len(sql)} characters)")
        print(f"  [WARNING] Cannot execute via Python Supabase client")
        print(f"  [ACTION] Please run this SQL manually in Supabase SQL Editor:")
        print(f"           1. Go to Supabase Dashboard > SQL Editor")
        print(f"           2. Copy contents of {migration_file}")
        print(f"           3. Execute the SQL")

    except Exception as e:
        print(f"  [ERROR] {e}")

print("\n" + "=" * 60)
print("MANUAL MIGRATION REQUIRED")
print("=" * 60)
print("\nThe Supabase Python client doesn't support raw SQL execution.")
print("Please apply migrations manually:")
print("\n1. Go to: https://supabase.com/dashboard")
print("2. Select your project")
print("3. Navigate to: SQL Editor")
print("4. Run migration files in order:")
print("   - migrations/003_add_duplicate_prevention.sql")
print("   - migrations/004_add_reward_taxonomy.sql")
print("\nOr use psql command:")
print("   psql -h [host] -U [user] -d [db] -f migrations/003_add_duplicate_prevention.sql")
print("   psql -h [host] -U [user] -d [db] -f migrations/004_add_reward_taxonomy.sql")
