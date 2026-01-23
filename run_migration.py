"""
Run database migration for duplicate prevention system.

This script applies the migration to add fingerprint columns and duplicate detection tables.
"""

import os
from supabase_client import get_supabase_client
from logger_config import get_logger

logger = get_logger(__name__)

def run_migration():
    """Run the duplicate prevention migration."""
    try:
        # Read the migration SQL
        migration_path = "migrations/003_add_duplicate_prevention.sql"
        
        if not os.path.exists(migration_path):
            logger.error(f"Migration file not found: {migration_path}")
            return False
        
        with open(migration_path, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        # Get Supabase client
        supabase = get_supabase_client()
        
        logger.info("Running duplicate prevention migration...")
        
        # Execute the migration
        # Note: Supabase Python client doesn't support raw SQL execution
        # We need to use the REST API or run this manually in the Supabase dashboard
        
        logger.warning("Migration SQL prepared. Please run this manually in Supabase SQL Editor:")
        logger.warning("=" * 60)
        print(migration_sql)
        logger.warning("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"Error running migration: {e}")
        return False

if __name__ == "__main__":
    run_migration()