"""
Apply duplicate prevention migration to Supabase database.

Since the Python Supabase client doesn't support raw SQL execution,
this script provides the SQL to run manually in the Supabase dashboard.
"""

import os

def show_migration_instructions():
    """Show instructions for applying the migration."""
    migration_path = "migrations/003_add_duplicate_prevention.sql"
    
    if not os.path.exists(migration_path):
        print(f"❌ Migration file not found: {migration_path}")
        return
    
    with open(migration_path, 'r', encoding='utf-8') as f:
        migration_sql = f.read()
    
    print("🔧 DUPLICATE PREVENTION MIGRATION")
    print("=" * 60)
    print()
    print("To apply this migration:")
    print("1. Go to your Supabase Dashboard → SQL Editor")
    print("   (https://supabase.com/dashboard → Your Project → SQL Editor)")
    print("2. Copy and paste the SQL below into the SQL Editor")
    print("3. Click 'Run' to execute the migration")
    print()
    print("📋 MIGRATION SQL:")
    print("=" * 60)
    print(migration_sql)
    print("=" * 60)
    print()
    print("✅ After running the migration, you can run the scraper again:")
    print("   python enhanced_scraper.py")

if __name__ == "__main__":
    show_migration_instructions()