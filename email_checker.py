#!/usr/bin/env python3
"""
@file email_checker.py
@brief Gmail integration for automatic job application status updates.

@details
This module integrates with Gmail API to:
- Search for emails from companies in your application tracker
- Parse email content for status indicators (rejection, interview invites, etc.)
- Automatically update application statuses and add stages
- Maintain audit trail of email-based updates

Features:
- Gmail OAuth2 authentication
- Intelligent email parsing with keyword detection
- Configurable status mapping rules
- Batch processing of applications
- Detailed logging of all updates

Usage:
    python email_checker.py setup          # Initial Gmail OAuth setup
    python email_checker.py check          # Check emails and update statuses
    python email_checker.py check --dry-run # Preview changes without updating
"""

from __future__ import annotations

import base64
import email
import json
import logging
import os
import pickle
import re
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Set

import click
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Import from our existing CLI system
from cli import JSONStorage, Storage, TABLES, _get_storage_from_ctx, _now_s

# =============================================================================
# Configuration and Constants
# =============================================================================

# Gmail API scopes - we need readonly access to emails
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Default paths
CREDENTIALS_FILE = 'secret/googleapi.json'  # Download from Google Cloud Console
TOKEN_FILE = 'secret/token.pickle'           # Generated after first auth
CONFIG_FILE = 'email_config.json'            # Email checker configuration

# Status mapping based on email content keywords
DEFAULT_STATUS_RULES = {
    'rejected': {
        'keywords': [
            'unfortunately', 'regret', 'not moving forward', 'not selected', 'passed on',
            'decided to go', 'pursuing other candidates', 'will not be proceeding',
            'not the right fit', 'position has been filled', 'thank you for your interest',
            'move forward with other candidates', 'decided to move forward with other',
            'will not be moving forward', 'have decided to go with'
        ],
        'domains': [],  # Can add specific rejection email domains
        'priority': 15  # Higher priority than interview to catch rejections better
    },
    'interview': {
        'keywords': [
            'interview', 'phone screen', 'next step', 'would like to schedule',
            'move forward', 'discuss further', 'technical assessment', 'coding challenge',
            'meet with', 'available for a call', 'screening call'
        ],
        'domains': [],
        'priority': 20
    },
    'offer': {
        'keywords': [
            'offer', 'congratulations', 'pleased to extend', 'job offer',
            'terms of employment', 'compensation package', 'start date'
        ],
        'domains': [],
        'priority': 30
    },
    'recruiter': {
        'keywords': [
            'recruiter', 'talent acquisition', 'hr representative', 'hiring manager',
            'received your application', 'reviewing your profile', 'follow up'
        ],
        'domains': [],
        'priority': 5
    }
}

# =============================================================================
# Gmail API Integration
# =============================================================================

class GmailChecker:
    """Gmail API integration for checking job application emails."""
    
    def __init__(self, storage: Storage, credentials_file: str = CREDENTIALS_FILE, 
                 token_file: str = TOKEN_FILE, config_file: str = CONFIG_FILE):
        self.storage = storage
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.config_file = config_file
        self.service = None
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load email checker configuration."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    # Ensure we have status rules
                    if 'status_rules' not in config:
                        config['status_rules'] = DEFAULT_STATUS_RULES
                    return config
            except Exception as e:
                logging.warning(f"Failed to load config from {self.config_file}: {e}")
        
        # Default configuration
        return {
            'status_rules': DEFAULT_STATUS_RULES,
            'days_back': 7,  # How many days back to check emails
            'max_emails_per_company': 10,  # Limit emails per company to avoid rate limits
            'exclude_domains': ['noreply@', 'no-reply@', 'donotreply@'],  # Skip automated emails
            'last_check': None  # Timestamp of last check
        }
    
    def _save_config(self) -> None:
        """Save current configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save config to {self.config_file}: {e}")
    
    def _load_credentials_from_file(self) -> Optional[Dict[str, Any]]:
        """Load Gmail credentials from custom JSON format with 'key' field."""
        try:
            with open(self.credentials_file, 'r') as f:
                data = json.load(f)
                # Extract credentials from the 'key' field
                if 'key' in data:
                    return data['key']
                else:
                    # Fallback: assume the whole file is the credentials
                    return data
        except Exception as e:
            logging.error(f"Failed to load credentials from {self.credentials_file}: {e}")
            return None
    
    def setup_gmail_auth(self) -> bool:
        """Set up Gmail OAuth2 authentication."""
        creds = None
        
        # Load existing token if available
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'rb') as token:
                    creds = pickle.load(token)
            except Exception as e:
                logging.warning(f"Failed to load existing token: {e}")
        
        # If there are no valid credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logging.warning(f"Failed to refresh token: {e}")
                    creds = None
            
            if not creds:
                if not os.path.exists(self.credentials_file):
                    click.echo(f"❌ Gmail credentials file not found: {self.credentials_file}")
                    click.echo("\n📋 To set up Gmail integration:")
                    click.echo("1. Go to https://console.cloud.google.com/")
                    click.echo("2. Create or select a project")
                    click.echo("3. Enable Gmail API")
                    click.echo("4. Create credentials (OAuth 2.0 Client ID)")
                    click.echo("5. Save credentials in secret/googleapi.json under 'key' field")
                    return False
                
                # Load credentials from custom format
                credentials_data = self._load_credentials_from_file()
                if not credentials_data:
                    click.echo(f"❌ Failed to load credentials from {self.credentials_file}")
                    click.echo("Expected format: {'key': {<oauth_credentials>}}")
                    return False
                
                try:
                    # Create a temporary file with the credentials in the expected format
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                        json.dump(credentials_data, temp_file, indent=2)
                        temp_credentials_path = temp_file.name
                    
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            temp_credentials_path, SCOPES)
                        creds = flow.run_local_server(port=0)
                    finally:
                        # Clean up temporary file
                        os.unlink(temp_credentials_path)
                        
                except Exception as e:
                    click.echo(f"❌ Failed to authenticate with Gmail: {e}")
                    click.echo("Please check that your credentials file contains valid OAuth 2.0 credentials under the 'key' field")
                    return False
            
            # Save credentials for the next run
            try:
                os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
                with open(self.token_file, 'wb') as token:
                    pickle.dump(creds, token)
            except Exception as e:
                logging.warning(f"Failed to save token: {e}")
        
        # Build Gmail service
        try:
            self.service = build('gmail', 'v1', credentials=creds)
            # Test the connection
            self.service.users().getProfile(userId='me').execute()
            click.echo("✅ Gmail authentication successful!")
            return True
        except Exception as e:
            click.echo(f"❌ Failed to connect to Gmail API: {e}")
            return False
    
    def _get_company_domains(self) -> Dict[str, str]:
        """Get mapping of company domains to company IDs."""
        companies = self.storage.read("companies")
        domain_map = {}
        
        for company in companies:
            company_id = company.get('company_id')
            name = company.get('name', '').lower()
            website = company.get('website', '')
            
            if not company_id:
                continue
            
            # Extract domain from website
            if website:
                domain = re.sub(r'^https?://(www\.)?', '', website.lower())
                domain = domain.split('/')[0]
                if domain:
                    domain_map[domain] = company_id
            
            # Also map company name variations
            if name:
                # Remove common suffixes for better matching
                clean_name = re.sub(r'\s+(inc|corp|corporation|ltd|limited|llc|company|co)\.?$', '', name, flags=re.IGNORECASE)
                domain_map[clean_name.replace(' ', '').lower()] = company_id
        
        return domain_map
    
    def _search_emails_for_company(self, company_id: str, company_name: str, 
                                  days_back: int = 7) -> List[Dict[str, Any]]:
        """Search Gmail for emails from a specific company."""
        if not self.service:
            return []
        
        # Build search query
        query_parts = []
        
        # Search by company name
        if company_name:
            query_parts.append(f'from:("{company_name}")')
        
        # Time range
        date_filter = (datetime.now() - timedelta(days=days_back)).strftime('%Y/%m/%d')
        query_parts.append(f'after:{date_filter}')
        
        query = ' '.join(query_parts)
        
        try:
            # Search for messages
            result = self.service.users().messages().list(
                userId='me', 
                q=query,
                maxResults=self.config.get('max_emails_per_company', 10)
            ).execute()
            
            messages = result.get('messages', [])
            emails = []
            
            for message in messages:
                try:
                    # Get full message
                    msg = self.service.users().messages().get(
                        userId='me', 
                        id=message['id'],
                        format='full'
                    ).execute()
                    
                    email_data = self._parse_email(msg, company_id)
                    if email_data:
                        emails.append(email_data)
                        
                except Exception as e:
                    logging.warning(f"Failed to fetch message {message['id']}: {e}")
                    continue
            
            return emails
            
        except HttpError as e:
            logging.error(f"Gmail API error for company {company_name}: {e}")
            return []
    
    def _parse_email(self, message: Dict[str, Any], company_id: str) -> Optional[Dict[str, Any]]:
        """Parse a Gmail message and extract relevant information."""
        try:
            headers = message['payload'].get('headers', [])
            
            # Extract basic info
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '')
            date_str = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
            message_id = message.get('id', '')
            
            # Skip if from excluded domains
            for excluded in self.config.get('exclude_domains', []):
                if excluded.lower() in sender.lower():
                    return None
            
            # Extract email body
            body = self._extract_body(message['payload'])
            
            # Parse date
            email_date = None
            try:
                # Gmail date format parsing
                from email.utils import parsedate_to_datetime
                email_date = parsedate_to_datetime(date_str).timestamp()
            except:
                email_date = time.time()
            
            return {
                'message_id': message_id,
                'company_id': company_id,
                'sender': sender,
                'subject': subject,
                'body': body[:1000],  # First 1000 chars for analysis
                'date': email_date,
                'full_body': body  # Keep full body for detailed analysis
            }
            
        except Exception as e:
            logging.warning(f"Failed to parse email message: {e}")
            return None
    
    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """Extract text body from email payload."""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    if data:
                        body += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                elif part['mimeType'] == 'multipart/alternative':
                    body += self._extract_body(part)
        else:
            if payload['mimeType'] == 'text/plain':
                data = payload['body'].get('data', '')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        
        return body
    
    def _analyze_email_content(self, email_data: Dict[str, Any]) -> Optional[Tuple[str, int]]:
        """Analyze email content and determine status update."""
        subject = email_data.get('subject', '').lower()
        body = email_data.get('full_body', '').lower()
        content = f"{subject} {body}"
        
        best_match = None
        highest_priority = 0
        best_score = 0
        
        for status, rules in self.config['status_rules'].items():
            priority = rules.get('priority', 0)
            keywords = rules.get('keywords', [])
            
            # Check for keyword matches - count total matches for scoring
            matches = sum(1 for keyword in keywords if keyword.lower() in content)
            
            # Calculate score: number of matches * priority
            score = matches * priority
            
            # Use highest score to break ties, with priority as tiebreaker
            if matches > 0 and (score > best_score or (score == best_score and priority > highest_priority)):
                best_match = status
                highest_priority = priority
                best_score = score
        
        return (best_match, best_score) if best_match else None
    
    def check_applications(self, dry_run: bool = False) -> Dict[str, Any]:
        """Check emails for all applications and update statuses."""
        if not self.service:
            raise click.ClickException("Gmail service not initialized. Run 'setup' first.")
        
        # Get all applications
        applications = self.storage.read("applications")
        companies = self.storage.read("companies")
        
        # Create company lookup
        company_lookup = {c['company_id']: c for c in companies}
        
        results = {
            'checked': 0,
            'emails_found': 0,
            'updates_made': 0,
            'updates': []
        }
        
        days_back = self.config.get('days_back', 7)
        
        click.echo(f"🔍 Checking emails from last {days_back} days...")
        
        for app in applications:
            company_id = app.get('company_id')
            if not company_id:
                continue
            
            company = company_lookup.get(company_id)
            if not company:
                continue
            
            company_name = company.get('name', '')
            results['checked'] += 1
            
            # Search emails for this company
            emails = self._search_emails_for_company(company_id, company_name, days_back)
            results['emails_found'] += len(emails)
            
            if not emails:
                continue
            
            click.echo(f"  📧 Found {len(emails)} emails from {company_name}")
            
            # Analyze each email
            for email_data in emails:
                status_result = self._analyze_email_content(email_data)
                
                if status_result:
                    new_status, confidence = status_result
                    current_status = app.get('status', 'new')
                    
                    # Only update if status is different and makes sense
                    if new_status != current_status and self._should_update_status(current_status, new_status):
                        update_info = {
                            'application_id': app.get('application_id'),
                            'company_name': company_name,
                            'old_status': current_status,
                            'new_status': new_status,
                            'email_subject': email_data.get('subject'),
                            'email_date': email_data.get('date'),
                            'confidence': confidence
                        }
                        
                        results['updates'].append(update_info)
                        
                        if not dry_run:
                            # Update application status
                            app['status'] = new_status
                            app['last_update'] = _now_s()
                            
                            # Add a stage entry
                            self._add_email_stage(app['application_id'], new_status, email_data)
                            
                        results['updates_made'] += 1
                        
                        click.echo(f"    🔄 {company_name}: {current_status} → {new_status}")
        
        if not dry_run and results['updates_made'] > 0:
            # Save updated applications
            self.storage.write("applications", applications)
            
            # Update last check time
            self.config['last_check'] = _now_s()
            self._save_config()
        
        return results
    
    def _should_update_status(self, current: str, new: str) -> bool:
        """Determine if status update makes logical sense."""
        # Define status progression rules
        progressions = {
            'new': ['applied', 'recruiter', 'interview', 'rejected'],
            'applied': ['recruiter', 'interview', 'rejected'],
            'recruiter': ['interview', 'technical', 'rejected'],
            'interview': ['technical', 'onsite', 'offer', 'rejected'],
            'technical': ['onsite', 'offer', 'rejected'],
            'onsite': ['offer', 'rejected'],
        }
        
        # Always allow rejection or offer (final states)
        if new in ['rejected', 'offer']:
            return True
        
        # Check if progression makes sense
        allowed = progressions.get(current, [])
        return new in allowed
    
    def _add_email_stage(self, application_id: str, status: str, email_data: Dict[str, Any]) -> None:
        """Add a stage entry based on email analysis."""
        stages = self.storage.read("stages")
        
        from cli import _new_id
        stage_id = _new_id("stg_")
        
        # Convert email timestamp to readable date
        email_date = datetime.fromtimestamp(email_data.get('date', time.time()))
        
        stage = {
            "stage_id": stage_id,
            "application_id": application_id,
            "stage": f"Email: {status}",
            "date": email_date.strftime('%Y-%m-%d'),
            "outcome": status,
            "notes": f"Auto-detected from email: {email_data.get('subject', 'No subject')[:100]}"
        }
        
        stages.append(stage)
        self.storage.write("stages", stages)


# =============================================================================
# CLI Commands
# =============================================================================

@click.group()
@click.option(
    "--data-dir",
    default="data",
    help="Directory for JSON storage."
)
@click.pass_context
def cli(ctx: click.Context, data_dir: str) -> None:
    """Gmail integration for job application tracking."""
    storage = JSONStorage(data_dir=data_dir)
    ctx.obj = {"storage": storage}


@cli.command()
@click.pass_context
def setup(ctx: click.Context) -> None:
    """Set up Gmail OAuth2 authentication."""
    storage = ctx.obj["storage"]
    checker = GmailChecker(storage)
    
    click.echo("🔧 Setting up Gmail integration...")
    
    if checker.setup_gmail_auth():
        click.echo("✅ Setup complete! You can now run 'check' to scan your emails.")
    else:
        click.echo("❌ Setup failed. Please check the instructions above.")


@cli.command()
@click.option("--dry-run", is_flag=True, help="Preview changes without updating database.")
@click.option("--days", default=7, help="Number of days back to check emails.")
@click.pass_context
def check(ctx: click.Context, dry_run: bool, days: int) -> None:
    """Check Gmail for application updates."""
    storage = ctx.obj["storage"]
    checker = GmailChecker(storage)
    
    # Update config with custom days
    checker.config['days_back'] = days
    
    if not checker.setup_gmail_auth():
        return
    
    if dry_run:
        click.echo("🔍 DRY RUN: Checking emails without making changes...")
    
    try:
        results = checker.check_applications(dry_run=dry_run)
        
        # Show summary
        click.echo(f"\n📊 Results:")
        click.echo(f"  Applications checked: {results['checked']}")
        click.echo(f"  Emails found: {results['emails_found']}")
        click.echo(f"  Updates {'would be made' if dry_run else 'made'}: {results['updates_made']}")
        
        # Show detailed updates
        if results['updates']:
            click.echo(f"\n📋 Status Updates:")
            for update in results['updates']:
                status_text = "WOULD UPDATE" if dry_run else "UPDATED"
                click.echo(f"  {status_text}: {update['company_name']} "
                          f"({update['old_status']} → {update['new_status']})")
                click.echo(f"    📧 Email: {update['email_subject'][:60]}...")
        
        if not dry_run and results['updates_made'] > 0:
            logging.info(f"Email checker updated {results['updates_made']} applications")
    
    except Exception as e:
        click.echo(f"❌ Error checking emails: {e}")
        logging.error(f"Email checker error: {e}")


@cli.command()
@click.pass_context
def config(ctx: click.Context) -> None:
    """Show current email checker configuration."""
    storage = ctx.obj["storage"]
    checker = GmailChecker(storage)
    
    click.echo("📋 Email Checker Configuration:")
    click.echo(f"  Days back to check: {checker.config.get('days_back', 7)}")
    click.echo(f"  Max emails per company: {checker.config.get('max_emails_per_company', 10)}")
    click.echo(f"  Last check: {checker.config.get('last_check', 'Never')}")
    
    click.echo(f"\n🏷️  Status Detection Rules:")
    for status, rules in checker.config['status_rules'].items():
        keywords = ', '.join(rules['keywords'][:3])  # Show first 3 keywords
        if len(rules['keywords']) > 3:
            keywords += "..."
        click.echo(f"  {status}: {keywords}")


if __name__ == "__main__":
    cli()
