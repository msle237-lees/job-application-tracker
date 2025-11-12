# GMAIL_SETUP.md

## Gmail Integration Setup

Use this guide to connect your tracker to Gmail for automatic status updates.

---

### 1) Create OAuth client in Google Cloud

1. Go to [https://console.cloud.google.com/](https://console.cloud.google.com/)
2. Create/select a project → **APIs & Services → Library** → enable **Gmail API**
3. **APIs & Services → Credentials → Create Credentials → OAuth client ID**

   * Application type: **Desktop**
   * Download the JSON

---

### 2) Prepare the secret

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

### 3) Install & initialize

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python cli.py init
```

---

### 4) Authenticate

```bash
python cli.py email-check --setup
```

This launches a browser for Google sign-in and creates `secret/token.pickle` once approved.

---

### 5) Run checks

```bash
# Dry run (no writes)
python cli.py email-check --dry-run

# Check 14 days back
python cli.py email-check --days 14

# Normal run
python cli.py email-check
```

---

### 6) Tuning behavior

Edit `email_config.json` to adjust:

* `status_rules.<status>.keywords` and `priority`
* `days_back`, `max_emails_per_company`
* `exclude_domains`

---

### 7) Common issues

* **Auth/token problems** → delete `secret/token.pickle` and re-run setup.
* **No messages found** → increase `--days`; ensure company names match senders.
* **Missing Google deps** → reinstall with `pip install -r requirements.txt`.

---

### 8) Demo without Gmail

```bash
python demo_email_checker.py
```

Shows what the classifier would do (no API calls).

---
