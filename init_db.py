#!/usr/bin/env python3
"""
@file init_db.py
@brief Database initialization and migration script.

@details
This script initializes the SQLite database with SQLAlchemy models.
Run this before starting the API server for the first time.
"""

import os
import sys
from models import init_db, Base, get_engine

def main():
    """Initialize the database"""
    database_url = os.getenv("DATABASE_URL", "sqlite:///./job_tracker.db")
    
    print(f"Initializing database: {database_url}")
    engine = init_db(database_url)
    print(f"✅ Database initialized successfully!")
    print(f"Tables created: {', '.join(Base.metadata.tables.keys())}")
    
    # Print database file location if SQLite
    if database_url.startswith("sqlite"):
        db_file = database_url.replace("sqlite:///./", "")
        db_path = os.path.abspath(db_file)
        print(f"Database file: {db_path}")

if __name__ == "__main__":
    main()
