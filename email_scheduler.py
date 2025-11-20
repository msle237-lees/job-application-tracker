#!/usr/bin/env python3
"""
@file email_scheduler.py
@brief Scheduled email checker service for Docker container.

@details
This service runs continuously in a Docker container and checks emails
on a configurable schedule (default: every hour).
"""

import time
import logging
import os
import sys
from datetime import datetime

# Configure logging
LOG_DIR = os.path.join(os.getcwd(), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "email_scheduler.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

def run_email_check():
    """Run the email checker"""
    try:
        from email_checker import GmailChecker
        from models import get_engine
        from sqlalchemy.orm import sessionmaker
        
        logging.info("Starting email check...")
        
        # Create database session
        engine = get_engine()
        SessionLocal = sessionmaker(bind=engine)
        
        # Create a simple storage adapter for the checker
        class DBStorage:
            def __init__(self, db_session):
                self.db = db_session
            
            def read(self, table):
                """Read data from database table"""
                from models import Company, Application, Contact, Stage
                
                table_map = {
                    'companies': Company,
                    'applications': Application,
                    'contacts': Contact,
                    'stages': Stage
                }
                
                if table not in table_map:
                    return []
                
                model = table_map[table]
                results = self.db.query(model).all()
                return [r.to_dict() for r in results]
            
            def write(self, table, rows):
                """Write data to database table"""
                # This is handled by the email checker updating individual records
                pass
        
        # Run email check
        db = SessionLocal()
        try:
            storage = DBStorage(db)
            checker = GmailChecker(storage)
            
            # Check if credentials are available
            if not os.path.exists('secret/googleapi.json'):
                logging.warning("Gmail credentials not found. Skipping email check.")
                return
            
            if not checker.setup_gmail_auth():
                logging.warning("Gmail authentication failed. Skipping email check.")
                return
            
            results = checker.check_applications(dry_run=False)
            
            logging.info(f"Email check completed:")
            logging.info(f"  Applications checked: {results['checked']}")
            logging.info(f"  Emails found: {results['emails_found']}")
            logging.info(f"  Updates made: {results['updates_made']}")
            
            if results['updates']:
                for update in results['updates']:
                    logging.info(f"  Updated: {update['company_name']} "
                               f"({update['old_status']} → {update['new_status']})")
        finally:
            db.close()
            
    except Exception as e:
        logging.error(f"Error during email check: {e}", exc_info=True)

def main():
    """Main scheduler loop"""
    # Get check interval from environment variable (default: 1 hour)
    check_interval_minutes = int(os.getenv('EMAIL_CHECK_INTERVAL_MINUTES', '60'))
    check_interval_seconds = check_interval_minutes * 60
    
    logging.info(f"Email scheduler started. Check interval: {check_interval_minutes} minutes")
    logging.info("Press Ctrl+C to stop")
    
    while True:
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logging.info(f"[{current_time}] Running scheduled email check...")
            
            run_email_check()
            
            logging.info(f"Next check in {check_interval_minutes} minutes")
            time.sleep(check_interval_seconds)
            
        except KeyboardInterrupt:
            logging.info("Scheduler stopped by user")
            break
        except Exception as e:
            logging.error(f"Scheduler error: {e}", exc_info=True)
            logging.info("Waiting 5 minutes before retry...")
            time.sleep(300)  # Wait 5 minutes on error

if __name__ == "__main__":
    main()
