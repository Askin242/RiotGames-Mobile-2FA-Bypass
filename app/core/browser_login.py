"""Log in using the system's installed Edge/Chrome instead of a bundled browser.

Launches the browser with a temporary profile + remote debugging, then reads the
session cookies (including the httpOnly `ssid`) and the CSRF token over the
Chrome DevTools Protocol. This avoids bundling Chromium (Qt WebEngine), which is
the bulk of the app's size.
"""

import os
import json
import time
import socket
import shutil
import tempfile
import subprocess

import requests
from websocket import create_connection


def find_browser():
    candidates = [
        r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
        r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
        r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
        r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
        r"%LocalAppData%\Google\Chrome\Application\chrome.exe",
    ]
    for c in candidates:
        path = os.path.expandvars(c)
        if os.path.exists(path):
            return path
    return None


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _page_ws(port, timeout=20):
    """Wait for the DevTools endpoint and return the Riot login page's ws URL."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            targets = requests.get(f"http://127.0.0.1:{port}/json", timeout=2).json()
            pages = [t for t in targets if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
            riot = [t for t in pages if "riotgames.com" in t.get("url", "")]
            chosen = riot[0] if riot else (pages[0] if pages else None)
            if chosen:
                return chosen["webSocketDebuggerUrl"]
        except Exception:
            pass
        time.sleep(0.4)
    return None


def _domain_matches(cookie_domain, host):
    """Whether a cookie set for `cookie_domain` is sent to `host`."""
    d = cookie_domain.lstrip(".")
    return host == d or host.endswith("." + d)


def _cookies_for_host(all_cookies, host):
    """Resolve the cookies a browser would actually send to `host`.

    `Network.getAllCookies` returns every domain's cookies at once, so a flat
    {name: value} dict lets same-named cookies from different domains (e.g. the
    `sub`/`csid`/`tdid` that exist on both auth.riotgames.com and .riotgames.com)
    clobber each other. We resolve per host, letting the more specific domain win.
    """
    relevant = [c for c in all_cookies if _domain_matches(c.get("domain", ""), host)]
    relevant.sort(key=lambda c: len(c.get("domain", "").lstrip(".")))
    jar = {}
    for c in relevant:
        jar[c["name"]] = c["value"]
    return jar


class _Cdp:
    def __init__(self, ws_url):
        self.ws = create_connection(ws_url, timeout=10)
        self._id = 0

    def call(self, method, **params):
        self._id += 1
        msg_id = self._id
        self.ws.send(json.dumps({"id": msg_id, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == msg_id:
                return msg.get("result", {})

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


def login(cancelled=lambda: False, timeout=600):
    """Drive the system browser through a Riot login.

    Returns a dict (or None) with domain-resolved cookies:
        {"cookies": account.riotgames.com jar, "auth_cookies": auth.riotgames.com
         jar (for the persistent `ssid` session), "csrf": str, "id_token": str}
    `cancelled` is polled so the caller can abort.
    """
    browser = find_browser()
    if not browser:
        return None
    port = _free_port()
    profile = tempfile.mkdtemp(prefix="riot2fa_login_")
    proc = subprocess.Popen(
        [
            browser,
            f"--remote-debugging-port={port}",
            "--remote-allow-origins=*",
            f"--user-data-dir={profile}",
            "--no-first-run",
            "--no-default-browser-check",
            "--new-window",
            "https://account.riotgames.com/",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    cdp = None
    try:
        ws_url = _page_ws(port)
        if not ws_url:
            return None
        cdp = _Cdp(ws_url)
        cdp.call("Network.enable")
        deadline = time.time() + timeout
        while time.time() < deadline:
            if cancelled() or proc.poll() is not None:
                return None
            cookies = cdp.call("Network.getAllCookies").get("cookies", [])
            account = _cookies_for_host(cookies, "account.riotgames.com")
            if "id_token" in account:
                csrf = cdp.call(
                    "Runtime.evaluate",
                    expression="(document.querySelector('meta[name=\"csrf-token\"]')||{}).content||''",
                    returnByValue=True,
                ).get("result", {}).get("value", "")
                if csrf:
                    auth = _cookies_for_host(cookies, "auth.riotgames.com")
                    return {
                        "cookies": account,
                        "auth_cookies": auth,
                        "csrf": csrf,
                        "id_token": account["id_token"],
                    }
            time.sleep(1)
        return None
    finally:
        if cdp:
            cdp.close()
        try:
            proc.terminate()
        except Exception:
            pass
        shutil.rmtree(profile, ignore_errors=True)
