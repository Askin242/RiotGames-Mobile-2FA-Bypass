import uuid

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel
from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile

from app.api import SSO_COOKIE_NAMES


def _domain_matches(cookie_domain, host):
    d = (cookie_domain or "").lstrip(".")
    return bool(d) and (host == d or host.endswith("." + d))


class LoginBrowserDialog(QDialog):
    """Embedded Riot login. Logs in inside the app (Qt WebEngine) and captures
    the account session cookies, the csrf token and the persistent `ssid`.

    Cookies are kept with their domain so same-named cookies from different
    Riot subdomains don't clobber each other: `cookies` resolves to what
    account.riotgames.com would receive, `sso_cookies` to auth.riotgames.com
    (the `ssid` that lets us mint fresh access tokens later without re-login).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Riot Account Login")
        self.resize(960, 720)
        self.cookies = {}
        self.sso_cookies = {}
        self.csrf_token = None
        self.id_token = None
        self.profile_id = "rso_" + uuid.uuid4().hex
        self._all = []
        self._detected = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.status = QLabel("  Waiting for login...")
        self.status.setFixedHeight(28)
        self.status.setStyleSheet(
            "background-color:#111118; color:#666677; font-size:11px; padding-left:10px;"
        )
        lay.addWidget(self.status)

        self.profile = QWebEngineProfile(self.profile_id, self)
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )
        self.profile.cookieStore().cookieAdded.connect(self._cookie_added)

        self._page = QWebEnginePage(self.profile, self)
        self.browser = QWebEngineView(self)
        self.browser.setPage(self._page)
        lay.addWidget(self.browser)

        self._page.urlChanged.connect(self._url_changed)
        self._page.loadFinished.connect(self._load_finished)
        self.browser.setUrl(QUrl("https://account.riotgames.com/"))

    def _cleanup_browser(self):
        if self._page is None:
            return
        self._page.disconnect()
        self.browser.setPage(None)
        self._page.deleteLater()
        self._page = None

    def done(self, result):
        self._cleanup_browser()
        super().done(result)

    def _cookie_added(self, cookie):
        name = bytes(cookie.name()).decode("utf-8", errors="replace")
        value = bytes(cookie.value()).decode("utf-8", errors="replace")
        self._all.append((cookie.domain(), name, value))
        # `sid` = the new account-portal session cookie; `ssid` = the SSO session
        # we mint tokens from. Either arriving means we may now be logged in.
        if name in ("sid", "ssid", "id_token"):
            QTimer.singleShot(400, self._try_detect)

    def _cookies_for_host(self, host):
        relevant = [t for t in self._all if _domain_matches(t[0], host)]
        relevant.sort(key=lambda t: len(t[0].lstrip(".")))
        jar = {}
        for _domain, name, value in relevant:
            jar[name] = value
        return jar

    def _url_changed(self, _url):
        QTimer.singleShot(500, self._try_detect)

    def _load_finished(self, ok):
        if ok:
            QTimer.singleShot(500, self._try_detect)

    def _try_detect(self):
        if self._detected or self._page is None:
            return
        host = self._page.url().host()
        acct = self._cookies_for_host("account.riotgames.com")
        auth = self._cookies_for_host("auth.riotgames.com")
        # The new Riot account portal (client `accountodactyl-prod`) no longer
        # sets an `id_token` cookie. Login is done once we're back on the account
        # site with its session cookie (`sid`) AND we hold the SSO `ssid` (which
        # lets us mint the id_token/access_token that the old cookie used to give).
        have_session = "sid" in acct or bool(acct.get("id_token"))
        have_ssid = bool(auth.get("ssid"))
        if host != "account.riotgames.com" or not have_session or not have_ssid:
            return
        self._detected = True
        self.status.setText("  Login detected — extracting session...")
        self.status.setStyleSheet(
            "background-color:#0e1a0e; color:#55aa55; font-size:11px; padding-left:10px;"
        )
        self._page.toHtml(self._html_received)

    def _html_received(self, _html):
        acct = self._cookies_for_host("account.riotgames.com")
        self.cookies = acct
        # id_token is minted later from the SSO cookies (no longer a cookie here).
        self.id_token = acct.get("id_token")
        auth = self._cookies_for_host("auth.riotgames.com")
        self.sso_cookies = {k: auth[k] for k in SSO_COOKIE_NAMES if auth.get(k)}
        self.status.setText("  Success! Capturing session...")
        # The real CSRF token lives in a <meta name="csrf-token"> tag that the SPA
        # injects after render (NOT the a12l-csrf-prod cookie, which is a
        # different value the API rejects). Read it from the live DOM, retrying
        # until the SPA has injected it.
        self._capture_csrf(0)

    def _capture_csrf(self, attempt):
        js = (
            "(function(){var m=document.querySelector("
            "'meta[name=\"csrf-token\"]');return m?m.getAttribute('content'):'';})()"
        )
        self._page.runJavaScript(js, lambda tok: self._csrf_captured(tok, attempt))

    def _csrf_captured(self, tok, attempt):
        if self._page is None:
            return
        if tok:
            self.csrf_token = tok
            QTimer.singleShot(100, self.accept)
            return
        if attempt < 10:
            QTimer.singleShot(500, lambda: self._capture_csrf(attempt + 1))
            return
        # Last resort: the csrf cookie (works for some flows even if not ideal).
        for name, value in self.cookies.items():
            if "csrf" in name.lower():
                self.csrf_token = value
                break
        QTimer.singleShot(100, self.accept)
