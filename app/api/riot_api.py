import re
import time
import json
import base64

import requests

from app.core.auth_totp import get_code

def decode_jwt_payload(token):
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        payload = parts[1]
        rem = len(payload) % 4
        if rem:
            payload += "=" * (4 - rem)
        return json.loads(base64.urlsafe_b64decode(payload))
    except Exception:
        return None

def is_valid_jwt(token):
    payload = decode_jwt_payload(token)
    if payload is None:
        return False
    exp = payload.get("exp")
    if exp is not None and exp < time.time():
        return False
    return True

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
)

def _riot_api_headers(csrf_token):
    return {
        "accept": "application/json",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/json",
        "csrf-token": csrf_token,
        "origin": "https://account.riotgames.com",
        "referer": "https://account.riotgames.com/",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": _USER_AGENT,
    }

def fetch_riot_id(cookies, csrf_token):
    resp = requests.get(
        "https://account.riotgames.com/api/account/v1/user",
        cookies=cookies,
        headers=_riot_api_headers(csrf_token),
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    alias = data.get("alias", {})
    gn = alias.get("game_name") if alias else None
    tl = alias.get("tag_line") if alias else None
    if gn and tl:
        return f"{gn}#{tl}"
    if gn:
        return gn
    return data.get("username", data.get("sub", "Unknown"))

def fetch_mfa_factors(cookies, csrf_token):
    """List the account's MFA factors (email, riotmobile, ...) and their status."""
    resp = requests.get(
        "https://account.riotgames.com/api/mfa/v2/factors",
        cookies=cookies,
        headers=_riot_api_headers(csrf_token),
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()

def is_email_mfa_enabled(factors):
    """True if the account has email MFA enabled (a prerequisite for riotmobile)."""
    items = factors if isinstance(factors, list) else factors.get("factors", [])
    for f in items:
        if isinstance(f, dict) and f.get("factor") == "email":
            return f.get("status") == "enabled"
    return False

def enable_mfa(cookies, csrf_token):
    resp = requests.post(
        "https://account.riotgames.com/api/mfa/v2/factors/riotmobile/enable",
        cookies=cookies,
        headers=_riot_api_headers(csrf_token),
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["secret"]

def verify_mfa(id_token, seed):
    resp = requests.post(
        "https://api.account.riotgames.com/mfa/v1/factor/riotmobile/verify",
        headers={
            "Authorization": f"Bearer {id_token}",
            "Content-Type": "application/json",
        },
        data=json.dumps({"device": "Riot 2FA Manager", "otp": get_code(seed)}),
        timeout=15,
    )
    resp.raise_for_status()
    return resp

MPS_REGISTER_MFA_URL = (
    "https://riot-geo.mps.si.riotgames.com/mps/v1/app/riotmobile-mfa/device"
)
TOTP_VERIFICATION_URL = (
    "https://authenticate.riotgames.com/api/v1/session/totp-verification"
)

def extract_puuid(id_token):
    """The account puuid is the `sub` claim of the login id_token."""
    payload = decode_jwt_payload(id_token)
    if not payload:
        return None
    return payload.get("sub")

def register_mfa_push_device(access_token, fcm_token):
    """Register our FCM token with Riot MPS so this account's logins push to us.

    Authenticated with the account's RSO access token (the `access_token`
    cookie from account.riotgames.com works). This is a PUT and returns 204.
    """
    resp = requests.put(
        MPS_REGISTER_MFA_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        data=json.dumps(
            {"device_token": fcm_token, "platform": "android", "locale": "en-US"}
        ),
        timeout=20,
    )
    resp.raise_for_status()
    return resp

RSO_AUTHORIZE_URL = "https://auth.riotgames.com/api/v1/authorization"
SSO_COOKIE_NAMES = ("ssid", "clid", "csid", "tdid", "sub", "ccid", "asid")

_REAUTH_BODY = {
    "client_id": "ritoplus",
    "nonce": "1",
    "redirect_uri": "http://localhost/redirect",
    "response_type": "token id_token",
    "scope": "openid account link ban lol summoner offline_access "
    "riot://riot.authenticator/session.auth",
}

def mint_access_token(sso_cookies):
    """Mint a fresh RSO access token from stored SSO cookies (needs `ssid`).

    Returns the access token, or None if the session has expired (re-login needed).
    """
    if not sso_cookies or not sso_cookies.get("ssid"):
        return None
    session = requests.Session()
    for name, value in sso_cookies.items():
        if value:
            session.cookies.set(name, value, domain="auth.riotgames.com")
    resp = session.post(
        RSO_AUTHORIZE_URL,
        json=_REAUTH_BODY,
        headers={"Content-Type": "application/json", "User-Agent": _USER_AGENT},
        timeout=20,
        allow_redirects=False,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("type") != "response":
        return None
    uri = (((data.get("response") or {}).get("parameters") or {}).get("uri")) or ""
    match = re.search(r"access_token=([^&]+)", uri)
    return match.group(1) if match else None

RSO_AUTH_HOST = "https://authenticate.riotgames.com"
QR_SESSION_INFO_PATH = "/api/v1/session/info"
QR_SESSION_AUTH_PATH = "/api/v1/session/authentication"

_RSO_AUTH_UA = (
    "RiotGamesApi/26.3.0.0 rso-authenticator "
    "(Android;12.31;SKQ1.211019.001 test-keys;) ritoplus/5.3.0"
)

def _rso_auth_headers(access_token):
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": _RSO_AUTH_UA,
    }

def parse_qr_login(text):
    """Extract (suuid, cluster) from a scanned Riot QR login string."""
    import urllib.parse

    text = (text or "").strip()
    if text.startswith("http"):
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(text).query)
        return qs.get("suuid", [None])[0], qs.get("cluster", [None])[0]
    if ":" in text:
        suuid, cluster = text.split(":", 1)
        return suuid.strip(), cluster.strip()
    return None, None

def qr_session_info(access_token, suuid, cluster):
    """Fetch the pending QR-login details (geolocation, request info)."""
    resp = requests.get(
        f"{RSO_AUTH_HOST}{QR_SESSION_INFO_PATH}?suuid={suuid}&cluster={cluster}",
        headers=_rso_auth_headers(access_token),
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()

def qr_approve(access_token, suuid, cluster, remember=True):
    """Approve a QR login attempt, signing the device in."""
    resp = requests.post(
        f"{RSO_AUTH_HOST}{QR_SESSION_AUTH_PATH}",
        headers=_rso_auth_headers(access_token),
        data=json.dumps({"suuid": suuid, "cluster": cluster, "remember": remember}),
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json() if resp.content else {}

def respond_to_mfa(suuid, cluster, puuid, seed, approve):
    """Approve or deny a login attempt received via push.

    Signed by the current TOTP generated from the account seed.
    """
    body = {
        "suuid": suuid,
        "cluster": cluster,
        "puuid": puuid,
        "totp": get_code(seed),
        "action": "approve" if approve else "deny",
        "known_value": None,
    }
    resp = requests.post(
        TOTP_VERIFICATION_URL,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        data=json.dumps(body),
        timeout=20,
    )
    resp.raise_for_status()
    return resp
