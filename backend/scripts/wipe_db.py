from app.database.session import SessionLocal, engine
from app.database.models import User, Appointment, Base
from sqlalchemy import text

def wipe_data():
    """
    Wipes all data from User and Appointment tables.
    """
    db = SessionLocal()
    try:
        print("Starting data wipe...")
        
        # Disable foreign key checks temporarily to avoid constraint errors
        # (Though we delete children first, this is safer)
        # However, SQLite doesn't support disabling foreign keys easily in a session like MySQL
        # But for PostgreSQL/MySQL/SQLite, deleting children first is standard.
        
        # 1. Delete all appointments first (Child table)
        num_deleted_appt = db.query(Appointment).delete()
        print(f"Deleted {num_deleted_appt} appointments.")
        
        # 2. Delete all users (Parent table)
        num_deleted_users = db.query(User).delete()
        print(f"Deleted {num_deleted_users} users.")
        
        # Commit changes
        db.commit()
        print("Data wipe complete successfully.")
        
        # Optional: Reset auto-increment counters (PostgreSQL specific)
        try:
            db.execute(text("TRUNCATE TABLE appointments RESTART IDENTITY CASCADE;"))
            db.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE;"))
            db.commit()
            print("Reset auto-increment counters.")
        except Exception as e:
            print(f"Note: Could not reset counters (might be SQLite or permissions issue): {e}")

    except Exception as e:
        print(f"Error wiping data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    confirm = input("This will DELETE ALL DATA from users and appointments tables. Are you sure? (type 'yes' to confirm): ")
    if confirm.lower() == 'yes':
        wipe_data()
    else:
        print("Operation cancelled.")
