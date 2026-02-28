"""
Database Initialization Script
============================

This script initializes the database schema by creating all tables defined in the models.
It handles:
1. Connecting to PostgreSQL server (using 'postgres' default database).
2. Creating the target database if it doesn't exist.
3. Creating tables within the target database.
"""

import sys
import logging
import os
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Add project root to sys.path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from app.core.config import settings
from app.database.models import Base

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_database_if_not_exists(url):
    """
    Connect to default 'postgres' database and create the target database if it doesn't exist.
    """
    try:
        # Parse the URL
        db_url = make_url(url)
        db_name = db_url.database
        
        # Construct connection params for default 'postgres' user/db
        # We assume the same credentials work for 'postgres' database or specific maintenance db
        # Note: Usually we connect to 'postgres' db to create other dbs
        
        # Safe URL parsing
        user = db_url.username
        password = db_url.password
        host = db_url.host
        port = db_url.port or 5432
        
        logger.info(f"Checking if database '{db_name}' exists...")
        
        # Connect to 'postgres' system database
        conn = psycopg2.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database='postgres'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{db_name}'")
        exists = cursor.fetchone()
        
        if not exists:
            logger.info(f"Database '{db_name}' not found. Creating...")
            cursor.execute(f"CREATE DATABASE {db_name}")
            logger.info(f"Database '{db_name}' created successfully.")
        else:
            logger.info(f"Database '{db_name}' already exists.")
            
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Failed to check/create database: {e}")
        # We don't exit here, we try to proceed in case the DB exists but we lacked permissions to check 'postgres' db
        # but if the DB really doesn't exist, the next step will fail.

def init_db():
    """
    Initialize the database.
    """
    try:
        db_url = settings.DATABASE_URL
        
        # 1. Create DB if not exists
        create_database_if_not_exists(db_url)
        
        # 2. Initialize Tables
        logger.info(f"Initializing tables in: {db_url.split('@')[-1]}") # Log safe part
        
        engine = create_engine(db_url)
        
        # Create all tables
        logger.info("Creating tables...")
        Base.metadata.create_all(bind=engine)
        
        logger.info("Database initialization completed successfully.")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_db()
