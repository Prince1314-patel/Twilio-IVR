
import sys
import os
sys.path.append(os.getcwd())

from sqlalchemy import text
from app.database.session import SessionLocal

def fix_schema():
    db = SessionLocal()
    try:
        print("Altering users table to allow NULL full_name...")
        # Check if column is nullable (PostgreSQL specific query)
        check_query = text("""
            SELECT is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'full_name';
        """)
        result = db.execute(check_query).scalar()
        print(f"Current is_nullable status: {result}")
        
        if result == 'NO':
            alter_query = text("ALTER TABLE users ALTER COLUMN full_name DROP NOT NULL;")
            db.execute(alter_query)
            db.commit()
            print("Successfully altered full_name to be nullable.")
        else:
            print("full_name is already nullable.")
            
    except Exception as e:
        print(f"Error altering table: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_schema()
