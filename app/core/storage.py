import os
import json

APPDATA_DIR = os.path.join(os.getenv("APPDATA"), "Riot2FA")
ACCOUNTS_FILE = os.path.join(APPDATA_DIR, "accounts.json")
FCM_CREDENTIALS_FILE = os.path.join(APPDATA_DIR, "fcm_credentials.json")
FCM_PERSISTENT_IDS_FILE = os.path.join(APPDATA_DIR, "fcm_persistent_ids.json")
_MAX_PERSISTENT_IDS = 256

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

def load_persistent_ids():
    """Ids of FCM pushes already received, seeded into the login handshake so the
    server stops replaying its backlog on every restart."""
    if not os.path.exists(FCM_PERSISTENT_IDS_FILE):
        return []
    try:
        with open(FCM_PERSISTENT_IDS_FILE, "r", encoding="utf-8") as f:
            ids = json.load(f)
        return [str(i) for i in ids] if isinstance(ids, list) else []
    except (OSError, json.JSONDecodeError):
        return []

def save_persistent_ids(ids):
    os.makedirs(APPDATA_DIR, exist_ok=True)
    trimmed = list(ids)[-_MAX_PERSISTENT_IDS:]
    with open(FCM_PERSISTENT_IDS_FILE, "w", encoding="utf-8") as f:
        json.dump(trimmed, f)
