"""Encode/decode an account as a single shareable string.

Format: ``RIOT2FA1-`` + urlsafe-base64(zlib(json)). The payload carries the
seed plus, when present, the puuid and the RSO session (SSO cookies /
access token) so the importer can also receive push login approvals.
"""

import json
import zlib
import base64

SHARE_PREFIX = "RIOT2FA1-"
_ALLOWED_FIELDS = ("name", "seed", "puuid", "sso", "access_token")

class ShareError(Exception):
    """A share code could not be parsed."""

def export_account(account):
    payload = {k: account[k] for k in _ALLOWED_FIELDS if account.get(k) is not None}
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    packed = base64.urlsafe_b64encode(zlib.compress(raw, 9)).decode("ascii")
    return SHARE_PREFIX + packed

def import_account(text):
    text = (text or "").strip()
    if not text.startswith(SHARE_PREFIX):
        raise ShareError("That doesn't look like a Riot 2FA share code.")
    packed = text[len(SHARE_PREFIX):]
    try:
        raw = zlib.decompress(base64.urlsafe_b64decode(packed))
        data = json.loads(raw)
    except Exception as exc:
        raise ShareError("The share code is corrupted or incomplete.") from exc
    if not isinstance(data, dict) or not data.get("seed"):
        raise ShareError("The share code is missing the account seed.")
    account = {k: data[k] for k in _ALLOWED_FIELDS if k in data}
    account.setdefault("name", "Imported account")
    return account
