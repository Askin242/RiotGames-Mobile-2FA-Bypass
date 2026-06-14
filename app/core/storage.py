import os
import json

APPDATA_DIR = os.path.join(os.getenv("APPDATA"), "Riot2FA")
ACCOUNTS_FILE = os.path.join(APPDATA_DIR, "accounts.json")
FCM_CREDENTIALS_FILE = os.path.join(APPDATA_DIR, "fcm_credentials.json")

def load_accounts():
    if not os.path.exists(ACCOUNTS_FILE):
        return []
    with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_accounts(accounts):
    os.makedirs(APPDATA_DIR, exist_ok=True)
    with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
        json.dump(accounts, f, indent=2, ensure_ascii=False)

def load_fcm_credentials():
    """One-time FCM device registration, shared across all accounts."""
    if not os.path.exists(FCM_CREDENTIALS_FILE):
        return None
    try:
        with open(FCM_CREDENTIALS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

def save_fcm_credentials(creds):
    os.makedirs(APPDATA_DIR, exist_ok=True)
    with open(FCM_CREDENTIALS_FILE, "w", encoding="utf-8") as f:
        json.dump(creds, f, indent=2)
