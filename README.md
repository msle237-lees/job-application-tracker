# 🧭 Job Application Tracker

A lightweight, local-first toolkit to track applications, store contacts, log stages, and (optionally) auto-update statuses from Gmail.

---

## Progress Chart

- [x] Configure CLI tool to track job applications manually.
- [x] Configure Gmail hook to search and update job application status.
- [ ] Create GUI or TUI framework for easier tracking.

---

## Quick start

```bash
# 1) Create and activate a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2) Install dependencies
pip install -r requirements.txt

# 3) Initialize storage (creates ./data/*.json and ./logs/)
python cli.py init

# 4) Add a company
python cli.py add-company --name "Acme Corp" --location "Remote"

# 5) Add an application (you’ll be prompted for fields)
python cli.py add-application

# 6) List your data
python cli.py list --table applications
```

---

## Project layout

```
.
├─ cli.py                 # Main CLI (CRUD, remove, update, email-check command)
├─ email_checker.py       # Gmail integration (OAuth, scan, classify, update)
├─ demo_email_checker.py  # No-API demo of the classifier & progression logic
├─ test_credentials.py    # Verifies secret/googleapi.json parsing
├─ config.yaml            # (Optional) App config
├─ email_config.json      # Created/updated by the email checker (rules, last_check)
├─ requirements.txt
├─ GMAIL_SETUP.md
├─ data/                  # JSON tables (created by init)
├─ logs/                  # cli.log
└─ secret/                # OAuth creds + token (created during Gmail setup)
```

---

## Core CLI commands

### Initialize

```bash
python cli.py init
```

### Create

```bash
# Add a company
python cli.py add-company --name "Acme" --location "Remote" --industry "SWE" --website "https://acme.dev" --source "LinkedIn" --rating "5/5"

# Add an application
python cli.py add-application --company-name "Acme" --position "Backend Engineer" --status "applied" --job-url "https://..." --salary-min 120000 --salary-max 150000
```

### Read

```bash
python cli.py list --table companies
python cli.py list --table applications
python cli.py list --table contacts
python cli.py list --table stages
```

### Update

```bash
python cli.py update-application --application-id app_123 --status interview --notes "Phone screen scheduled"
```

### Remove

```bash
python cli.py remove application --application-id app_123
python cli.py remove company --name "Acme" --cascade
```

---

## Gmail integration (optional)

### One-time auth

```bash
python cli.py email-check --setup
```

### Run checks

```bash
python cli.py email-check --dry-run
python cli.py email-check --days 14
```

### Editable rules

`email_config.json` stores keyword rules, priority, last_check, and limits.

---

## Credential file (secrets)

Place your OAuth client in `secret/googleapi.json` with this structure:

```json
{
  "key": {
    "installed": {
      "client_id": "...apps.googleusercontent.com",
      "client_secret": "...",
      "auth_uri": "https://accounts.google.com/o/oauth2/auth",
      "token_uri": "https://oauth2.googleapis.com/token",
      "redirect_uris": ["http://localhost"]
    }
  }
}
```

Validate:

```bash
python test_credentials.py
```

---

## GMAIL_SETUP.md

# Gmail Integration Setup

Use this guide to connect your tracker to Gmail for automatic status updates.

---

## 1) Create OAuth client in Google Cloud

1. Go to [https://console.cloud.google.com/](https://console.cloud.google.com/)
2. Create/select a project → **APIs & Services → Library** → enable **Gmail API**
3. **APIs & Services → Credentials → Create Credentials → OAuth client ID**

   * Application type: **Desktop**
   * Download the JSON

---

## 2) Prepare the secret

Save the credentials at `secret/googleapi.json` using this structure:

```json
{
  "key": {
    "installed": {
      "client_id": "your-client-id.apps.googleusercontent.com",
      "client_secret": "your-secret",
      "auth_uri": "https://accounts.google.com/o/oauth2/auth",
      "token_uri": "https://oauth2.googleapis.com/token",
      "redirect_uris": ["http://localhost"]
    }
  }
}
```

The checker reads the "key" field and writes `secret/token.pickle` after auth.

---

## 3) Install & initialize

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python cli.py init
```

---

## 4) Authenticate

```bash
python cli.py email-check --setup
```

This launches a browser for Google sign-in and creates `secret/token.pickle` once approved.

---

## 5) Run checks

```bash
# Dry run (no writes)
python cli.py email-check --dry-run

# Check 14 days back
python cli.py email-check --days 14

# Normal run
python cli.py email-check
```

---

## 6) Tuning behavior

Edit `email_config.json` to adjust:

* `status_rules.<status>.keywords` and `priority`
* `days_back`, `max_emails_per_company`
* `exclude_domains`

---

## 7) Common issues

* **Auth/token problems** → delete `secret/token.pickle` and re-run setup.
* **No messages found** → increase `--days`; ensure company names match senders.
* **Missing Google deps** → reinstall with `pip install -r requirements.txt`.

---

## 8) Demo without Gmail

```bash
python demo_email_checker.py
```

Shows what the classifier would do (no API calls).

---

## License & Author

MIT — Michael Lees
