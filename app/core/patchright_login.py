"""Riot login via Patchright (a stealth Playwright fork).

Qt WebEngine now trips hCaptcha's bot detection on the Riot login page, so the
login is driven through Patchright's undetected Chromium instead. This module
does ONLY the login: the user signs in, and once the RSO session cookies appear
we hand them back. Everything else (csrf refresh, enabling MFA, fetching the
account) is done by the normal `requests`-based API afterwards.

Detection is done purely by polling the cookie jar (read over CDP, never
touching the page) — poking the page with `evaluate`/in-page fetch during Riot's
login redirects destabilises the browser.
"""

import os
import sys
import time
import tempfile
import shutil

from app.api import SSO_COOKIE_NAMES


def _use_bundled_chromium():
    """In the frozen build, point Patchright at the Chromium packed beside it."""
    if not getattr(sys, "frozen", False):
        return
    from app.core.paths import resource_path

    bundled = resource_path("ms-playwright")
    if os.path.isdir(bundled):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = bundled


def _domain_matches(cookie_domain, host):
    d = (cookie_domain or "").lstrip(".")
    return bool(d) and (host == d or host.endswith("." + d))


def _jar_for_host(cookies, host):
    relevant = [c for c in cookies if _domain_matches(c.get("domain", ""), host)]
    relevant.sort(key=lambda c: len(c.get("domain", "").lstrip(".")))
    jar = {}
    for c in relevant:
        jar[c["name"]] = c["value"]
    return jar


def login(cancelled=lambda: False, timeout=600):
    """Open the stealth browser, let the user sign in, capture the session.

    Returns {"cookies", "sso", "csrf"} once signed in, or None (browser closed /
    timed out). Blocks — run it off the GUI thread.
    """
    _use_bundled_chromium()
    from patchright.sync_api import sync_playwright

    user_data = tempfile.mkdtemp(prefix="riot2fa_pw_")
    try:
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data,
                headless=False,
                no_viewport=True,
            )
            page = context.pages[0] if context.pages else context.new_page()
            try:
                page.goto("https://account.riotgames.com/", wait_until="commit")
            except Exception:
                pass

            deadline = time.time() + timeout
            while time.time() < deadline:
                time.sleep(1.5)
                if cancelled() or not context.pages:
                    return None
                try:
                    cookies = context.cookies()
                except Exception:
                    continue
                acc = _jar_for_host(cookies, "account.riotgames.com")
                auth = _jar_for_host(cookies, "auth.riotgames.com")
                # ssid = RSO auth completed; a12l-csrf-prod = the account session
                # is live. Both present => signed in and the account API will work.
                if auth.get("ssid") and acc.get("a12l-csrf-prod"):
                    sso = {k: auth[k] for k in SSO_COOKIE_NAMES if auth.get(k)}
                    return {
                        "cookies": acc,
                        "sso": sso,
                        "csrf": acc.get("a12l-csrf-prod"),
                    }
            return None
    finally:
        shutil.rmtree(user_data, ignore_errors=True)
