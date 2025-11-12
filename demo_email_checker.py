#!/usr/bin/env python3
"""
Demo script showing email checker functionality without actual Gmail access.
This simulates what the email checker would do with real emails.
"""

import json
from datetime import datetime, timedelta
from cli import JSONStorage
from email_checker import GmailChecker


def demo_email_analysis():
    """Demonstrate email content analysis without Gmail API."""
    
    print("🤖 Email Checker Demo - Content Analysis")
    print("=" * 50)
    
    # Sample email contents that would trigger different statuses
    sample_emails = [
        {
            "subject": "Thank you for your application - Software Engineer",
            "body": "Thank you for your interest in our Software Engineer position. Unfortunately, we have decided to move forward with other candidates who more closely match our requirements.",
            "expected_status": "rejected"
        },
        {
            "subject": "Next steps - Engineering Interview",
            "body": "Hi! Thanks for applying to our team. We'd love to schedule a phone interview to discuss your background further. Are you available next week?",
            "expected_status": "interview"
        },
        {
            "subject": "Job Offer - Senior Developer Position",
            "body": "Congratulations! We're pleased to extend a job offer for the Senior Developer position. The compensation package includes a competitive salary and benefits.",
            "expected_status": "offer"
        },
        {
            "subject": "Application Received - Data Scientist Role",
            "body": "Hello, our recruiter team has received your application for the Data Scientist position. We're currently reviewing your profile and will follow up soon.",
            "expected_status": "recruiter"
        }
    ]
    
    # Initialize email checker (without Gmail service)
    storage = JSONStorage("data")
    checker = GmailChecker(storage)
    
    print("📧 Analyzing sample emails:")
    print()
    
    for i, email in enumerate(sample_emails, 1):
        print(f"{i}. Subject: {email['subject']}")
        print(f"   Body: {email['body'][:80]}...")
        
        # Create email data structure like the real checker would
        email_data = {
            'subject': email['subject'],
            'full_body': email['body'],
            'sender': 'noreply@company.com',
            'date': datetime.now().timestamp()
        }
        
        # Analyze content
        result = checker._analyze_email_content(email_data)
        
        if result:
            detected_status, confidence = result
            expected = email['expected_status']
            
            status_emoji = "✅" if detected_status == expected else "❌"
            print(f"   {status_emoji} Detected: {detected_status} (confidence: {confidence})")
            print(f"   Expected: {expected}")
        else:
            print("   ❓ No status detected")
        
        print()


def demo_status_progression():
    """Demonstrate smart status progression logic."""
    
    print("🎯 Status Progression Logic Demo")
    print("=" * 40)
    
    storage = JSONStorage("data")
    checker = GmailChecker(storage)
    
    # Test cases for status progression
    test_cases = [
        ("new", "applied", True),          # Valid progression
        ("applied", "interview", True),    # Valid progression  
        ("interview", "offer", True),      # Valid progression
        ("interview", "rejected", True),   # Valid (can be rejected at any stage)
        ("offer", "interview", False),     # Invalid (backwards progression)
        ("rejected", "interview", False),  # Invalid (can't come back from rejection)
        ("new", "offer", True),           # Valid (skip stages)
    ]
    
    print("Testing status update logic:")
    print()
    
    for current, new, expected in test_cases:
        result = checker._should_update_status(current, new)
        status_emoji = "✅" if result == expected else "❌"
        action = "ALLOW" if result else "BLOCK"
        
        print(f"{status_emoji} {current} → {new}: {action}")
    
    print()


def show_setup_instructions():
    """Show setup instructions for Gmail integration."""
    
    print("📋 Gmail Setup Instructions")
    print("=" * 30)
    print()
    print("To enable automatic email checking:")
    print()
    print("1. 🔗 Set up Gmail API:")
    print("   • Go to https://console.cloud.google.com/")
    print("   • Create/select project → Enable Gmail API")
    print("   • Create OAuth credentials → Download as credentials.json")
    print("   • Save to secret/credentials.json")
    print()
    print("2. 🔐 Authenticate:")
    print("   python cli.py email-check --setup")
    print()
    print("3. 📧 Check emails:")
    print("   python cli.py email-check --dry-run  # Preview mode")
    print("   python cli.py email-check            # Update mode")
    print()
    print("📖 See GMAIL_SETUP.md for detailed guide")
    print()


def main():
    """Run the demo."""
    
    print("🚀 Job Application Tracker - Email Integration Demo")
    print("=" * 60)
    print()
    
    # Demo the email analysis
    demo_email_analysis()
    
    # Demo status progression logic
    demo_status_progression()
    
    # Show setup instructions
    show_setup_instructions()
    
    print("💡 This demo shows how the email checker would work with real Gmail data.")
    print("   Run 'python cli.py email-check --setup' to connect to your Gmail!")


if __name__ == "__main__":
    main()