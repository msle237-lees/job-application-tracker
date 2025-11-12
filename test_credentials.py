#!/usr/bin/env python3
"""
Test script to verify credential loading from googleapi.json with 'key' field.
"""

import json
import os
import sys
sys.path.append('.')

from email_checker import GmailChecker
from cli import JSONStorage


def test_credential_loading():
    """Test loading credentials from the new format."""
    
    print("🧪 Testing Credential Loading")
    print("=" * 35)
    
    # Initialize checker
    storage = JSONStorage("data")
    checker = GmailChecker(storage)
    
    # Test 1: Check if credential file exists
    if os.path.exists(checker.credentials_file):
        print(f"✅ Credential file found: {checker.credentials_file}")
    else:
        print(f"❌ Credential file not found: {checker.credentials_file}")
        print("   (This is expected if you haven't set up real credentials)")
    
    # Test 2: Try loading credentials
    try:
        creds_data = checker._load_credentials_from_file()
        if creds_data:
            print("✅ Credentials loaded successfully from 'key' field")
            
            # Check if it has the expected OAuth2 structure
            expected_fields = ['client_id', 'client_secret', 'auth_uri', 'token_uri']
            has_required = all(field in creds_data.get('installed', {}) for field in expected_fields)
            
            if has_required:
                print("✅ Credential structure looks valid (has required OAuth2 fields)")
            else:
                print("⚠️  Credential structure incomplete (missing OAuth2 fields)")
                print(f"   Found fields: {list(creds_data.get('installed', {}).keys())}")
        else:
            print("❌ Failed to load credentials or 'key' field not found")
            
    except Exception as e:
        print(f"❌ Error loading credentials: {e}")
    
    # Test 3: Show expected format
    print("\n📋 Expected format for secret/googleapi.json:")
    print("""
{
  "key": {
    "installed": {
      "client_id": "your-actual-client-id.googleusercontent.com",
      "client_secret": "your-actual-client-secret", 
      "auth_uri": "https://accounts.google.com/o/oauth2/auth",
      "token_uri": "https://oauth2.googleapis.com/token",
      "redirect_uris": ["http://localhost"]
    }
  }
}
""")
    
    print("💡 To get real credentials:")
    print("  1. Go to https://console.cloud.google.com/")
    print("  2. Enable Gmail API")
    print("  3. Create OAuth 2.0 credentials")
    print("  4. Download and format as shown above")


if __name__ == "__main__":
    test_credential_loading()