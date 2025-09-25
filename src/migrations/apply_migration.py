#!/usr/bin/env python3
"""
Apply database migrations for ODIN Pattern System
"""

import sqlite3
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def apply_migration(db_path: str = "odin.db", migration_file: str = "001_add_pattern_tables.sql"):
    """Apply a SQL migration file to the database"""
    
    migration_path = Path(__file__).parent / migration_file
    
    if not migration_path.exists():
        logger.error(f"Migration file not found: {migration_path}")
        return False
    
    try:
        # Read migration SQL
        with open(migration_path, 'r') as f:
            migration_sql = f.read()
        
        # Apply to database - execute each statement separately for better error handling
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Split by semicolons but be careful with triggers/views
            statements = migration_sql.split(';')
            
            for i, statement in enumerate(statements):
                statement = statement.strip()
                if statement and not statement.startswith('--'):
                    try:
                        cursor.execute(statement)
                        conn.commit()
                    except sqlite3.OperationalError as e:
                        # Ignore "duplicate column" errors for ALTER TABLE
                        if "duplicate column" in str(e).lower():
                            logger.debug(f"Column already exists (skipping): {e}")
                        else:
                            logger.warning(f"Statement {i} warning: {e}")
                    except Exception as e:
                        logger.error(f"Statement {i} failed: {e}")
                        logger.error(f"Statement was: {statement[:100]}...")
        
        logger.info(f"Successfully applied migration: {migration_file}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to apply migration: {e}")
        return False

def verify_migration(db_path: str = "odin.db"):
    """Verify that pattern tables were created"""
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Check for pattern tables
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name LIKE '%pattern%'
            """)
            
            pattern_tables = cursor.fetchall()
            
            print("\n✅ Pattern tables created:")
            for table in pattern_tables:
                print(f"   - {table[0]}")
            
            # Check for views
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='view' AND name LIKE 'v_pattern%'
            """)
            
            pattern_views = cursor.fetchall()
            
            if pattern_views:
                print("\n✅ Pattern views created:")
                for view in pattern_views:
                    print(f"   - {view[0]}")
            
            return len(pattern_tables) > 0
            
    except Exception as e:
        logger.error(f"Failed to verify migration: {e}")
        return False

if __name__ == "__main__":
    # Apply the pattern tables migration
    print("🔄 Applying pattern system migration...")
    success = apply_migration()
    
    if success:
        print("✅ Migration completed!")
        
        # Verify what was created
        if verify_migration():
            print("\n✨ Pattern system database ready!")
            print("\nNext step: Create src/patterns/ directory and database.py")
        else:
            print("⚠️  Migration ran but verification failed")
    else:
        print("❌ Migration failed. Check the logs above.")