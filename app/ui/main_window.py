import os
import time
import threading
import webbrowser

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QMessageBox,
    QDialog,
    QInputDialog,
    QSystemTrayIcon,
    QMenu,
    QApplication,
)
from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal
from PyQt6.QtGui import QIcon

from app.core import load_accounts, save_accounts, PERIOD
from app.core.fcm_service import FcmService
from app.core import updater
from app.core import browser_login
from app.core.paths import resource_path
from app.version import __version__
from app.api import (
    is_valid_jwt,
    fetch_riot_id,
    fetch_mfa_factors,
    is_email_mfa_enabled,
    enable_mfa,
    verify_mfa,
    extract_puuid,
    register_mfa_push_device,
    mint_access_token,
    SSO_COOKIE_NAMES,
    parse_qr_login,
    qr_session_info,
    qr_approve,
)
from app.ui.toast import Toast
from app.ui.account_card import AccountCard
from app.ui.manual_add_dialog import ManualAddDialog
from app.ui.mfa_prompt_dialog import MfaPromptDialog
from app.ui.qr_scanner_dialog import QrScannerDialog
from app.ui.qr_confirm_dialog import QrConfirmDialog

ICON_PATH = resource_path(os.path.join("images", "icon.png"))
QR_ICON_PATH = resource_path(os.path.join("images", "qr.png"))

class MainWindow(QMainWindow):
    _update_found = pyqtSignal(dict)
    _login_result = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Riot 2FA  v{__version__}")
        self.setMinimumSize(560, 300)
        self.resize(560, 400)

        self.accounts = load_accounts()
        self.cards: list[AccountCard] = []
        self._last_step = int(time.time()) // PERIOD

        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(18, 14, 18, 14)
        outer.setSpacing(0)

        hdr = QHBoxLayout()
        title = QLabel("RIOT 2FA")
        title.setObjectName("titleLabel")
        hdr.addWidget(title)
        hdr.addStretch()

        b1 = QPushButton("Add via Login")
        b1.setObjectName("addLoginBtn")
        b1.setFixedWidth(130)
        b1.clicked.connect(self._add_via_login)
        self._login_btn = b1
        hdr.addWidget(b1)
        hdr.addSpacing(6)
        b2 = QPushButton("Add Manually")
        b2.setObjectName("addManualBtn")
        b2.setFixedWidth(120)
        b2.clicked.connect(self._add_manually)
        hdr.addWidget(b2)
        hdr.addSpacing(6)
        bqr = QPushButton()
        bqr.setObjectName("qrBtn")
        bqr.setFixedWidth(38)
        bqr.setIcon(QIcon(QR_ICON_PATH))
        bqr.setIconSize(QSize(18, 18))
        bqr.setToolTip("Sign in by scanning a QR code on screen")
        bqr.clicked.connect(self._scan_qr)
        hdr.addWidget(bqr)
        outer.addLayout(hdr)
        outer.addSpacing(12)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setContentsMargins(0, 0, 2, 0)
        self.scroll_layout.setSpacing(6)
        self.scroll_layout.addStretch()
        self.scroll.setWidget(self.scroll_widget)
        outer.addWidget(self.scroll, stretch=1)

        self.toast = Toast(central)

        self._populate()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(50)

        self._active_prompts = []
        self._tray_hint_shown = False
        self._setup_tray()

        self.fcm = FcmService(self)
        self.fcm.push_received.connect(self._on_push)
        self.fcm.start()

        self._update_found.connect(self._on_update_found)
        self._login_result.connect(self._on_login_result)
        self._login_busy = False
        threading.Thread(target=self._check_update, daemon=True).start()

    def _check_update(self):
        info = updater.check_for_update()
        if info:
            self._update_found.emit(info)

    def _on_update_found(self, info):
        reply = QMessageBox.question(
            self,
            "Update available",
            f"A newer version ({info['version']}) is available "
            f"(you have {__version__}).\n\nWould you like to update?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if updater.is_frozen() and info.get("asset_url"):
            try:
                self.fcm.stop()
                updater.apply_exe_update(info["asset_url"])
                return
            except Exception:
                pass
        webbrowser.open(info["url"])

    def _setup_tray(self):
        icon = QIcon(ICON_PATH)
        self.setWindowIcon(icon)
        self.tray = QSystemTrayIcon(icon, self)
        self.tray.setToolTip("Riot 2FA")
        menu = QMenu()
        menu.addAction("Show", self._show_from_tray)
        menu.addSeparator()
        menu.addAction("Quit", self._quit_app)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_from_tray()

    def _show_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit_app(self):
        self.fcm.stop()
        self.tray.hide()
        QApplication.instance().quit()

    def closeEvent(self, event):

        event.ignore()
        self.hide()
        if not self._tray_hint_shown:
            self._tray_hint_shown = True
            self.tray.showMessage(
                "Riot 2FA",
                "Still running in the tray — you'll get login approval prompts here.",
                QSystemTrayIcon.MessageIcon.Information,
                4000,
            )

    def _populate(self):
        for c in self.cards:
            c.setParent(None)
            c.deleteLater()
        self.cards.clear()

        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        if not self.accounts:
            lbl = QLabel("No accounts yet — add one with the buttons above")
            lbl.setObjectName("emptyLabel")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.scroll_layout.addWidget(lbl)
        else:
            for acct in self.accounts:
                card = AccountCard(acct["name"], acct["seed"])
                card.remove_requested.connect(self._remove_account)
                card.copy_requested.connect(lambda: self.toast.popup("Copied to clipboard"))
                self.cards.append(card)
                self.scroll_layout.addWidget(card)
        self.scroll_layout.addStretch()

    def _tick(self):
        now = time.time()
        elapsed = now % PERIOD
        remaining_frac = 1.0 - elapsed / PERIOD
        remaining_sec = int(PERIOD - elapsed)
        step = int(now // PERIOD)
        code_changed = step != self._last_step
        self._last_step = step

        for card in self.cards:
            card.update_bar(remaining_frac, remaining_sec)
            if code_changed:
                card.refresh_code()

    def _save_and_refresh(self):
        save_accounts(self.accounts)
        self._populate()

    def _remove_account(self, name, seed):
        self.accounts = [
            a for a in self.accounts if not (a["name"] == name and a["seed"] == seed)
        ]
        self._save_and_refresh()

    def _on_push(self, data):
        """A login attempt arrived via push — show the approve/deny prompt."""
        puuid = data.get("puuid")
        account = next(
            (a for a in self.accounts if a.get("puuid") and a["puuid"] == puuid), None
        )
        if account is None:

            return

        self.tray.showMessage(
            "Riot login attempt",
            f"Approve or deny the login for {account.get('name', 'your account')}.",
            QSystemTrayIcon.MessageIcon.Warning,
            5000,
        )

        prompt = MfaPromptDialog(data, account, self)
        self._active_prompts.append(prompt)

        def _cleanup(_result, p=prompt):
            if p in self._active_prompts:
                self._active_prompts.remove(p)
            verb = p.outcome or "dismissed"
            if self.isVisible():
                self.toast.popup(f"Login {verb}")

        prompt.finished.connect(_cleanup)
        prompt.show()
        prompt.raise_()
        prompt.activateWindow()

    def _add_via_login(self):
        if self._login_busy:
            return
        if browser_login.find_browser() is None:
            QMessageBox.warning(
                self,
                "No browser found",
                "Could not find Microsoft Edge or Google Chrome.\n\nInstall one of "
                "them, or use \"Add Manually\" with the secret from your Riot 2FA email.",
            )
            return
        self._login_busy = True
        self._login_btn.setEnabled(False)
        self._login_btn.setText("Logging in…")
        self.toast.popup("Complete the login in the browser window that opened")
        threading.Thread(target=self._login_worker, daemon=True).start()

    def _login_worker(self):
        """Runs off the GUI thread: drive the system browser, then build the account."""
        try:
            data = browser_login.login()
        except Exception as exc:
            self._login_result.emit({"kind": "error", "title": "Login Failed", "text": str(exc)})
            return
        if not data:
            self._login_result.emit({"kind": "cancelled"})
            return

        cookies = data.get("cookies", {})
        csrf = data.get("csrf", "")
        id_tok = data.get("id_token", "")
        if not csrf or not id_tok:
            self._login_result.emit({
                "kind": "error",
                "title": "Error",
                "text": "Login OK but tokens could not be extracted.",
            })
            return

        try:
            name = fetch_riot_id(cookies, csrf)
        except Exception:
            name = "Unknown"

        try:
            factors = fetch_mfa_factors(cookies, csrf)
        except Exception:
            factors = None
        if factors is not None and not is_email_mfa_enabled(factors):
            self._login_result.emit({
                "kind": "error",
                "title": "Email 2FA required",
                "text": (
                    "You must enable email-based Multi-Factor Authentication on your "
                    "Riot account before you can add it here.\n\nTurn it on at "
                    "account.riotgames.com (Security → Multi-factor authentication), "
                    "then try again."
                ),
            })
            return

        try:
            seed = enable_mfa(cookies, csrf)
        except Exception as exc:
            self._login_result.emit({"kind": "error", "title": "Enable MFA Failed", "text": str(exc)})
            return

        warn = None
        try:
            verify_mfa(id_tok, seed)
        except Exception as exc:
            warn = f"MFA enabled but verification failed:\n{exc}\n\nSeed saved anyway."

        account = {"name": name, "seed": seed}
        puuid = extract_puuid(id_tok)
        if puuid:
            account["puuid"] = puuid

        auth_cookies = data.get("auth_cookies", {})
        sso = {k: auth_cookies[k] for k in SSO_COOKIE_NAMES if auth_cookies.get(k)}
        access_token = None
        if sso.get("ssid"):
            account["sso"] = sso
            try:
                access_token = mint_access_token(sso)
            except Exception:
                access_token = None
            if access_token:
                account["access_token"] = access_token

        push_note = self._register_push(access_token, id_tok, puuid)

        self._login_result.emit({
            "kind": "success",
            "account": account,
            "name": name,
            "warn": warn,
            "push_note": push_note,
        })

    def _on_login_result(self, result):
        self._login_busy = False
        self._login_btn.setEnabled(True)
        self._login_btn.setText("Add via Login")

        kind = result.get("kind")
        if kind == "cancelled":
            return
        if kind == "error":
            QMessageBox.warning(self, result.get("title", "Error"), result.get("text", ""))
            return

        if result.get("warn"):
            QMessageBox.warning(self, "Verify Warning", result["warn"])

        self.accounts.append(result["account"])
        self._save_and_refresh()
        QMessageBox.information(
            self, "Success", f"2FA added for {result['name']}{result['push_note']}"
        )

    def _register_push(self, access_token, id_tok, puuid):
        """Register this account's FCM device so logins push here. Best-effort."""
        if not puuid:
            return "\n\n(Push approval unavailable: could not read account id.)"

        tokens = [t for t in (access_token, id_tok) if t]
        if not tokens:
            return "\n\n(Push approval unavailable: missing access token.)"
        fcm_token = self.fcm.wait_for_token(30)
        if not fcm_token:
            return "\n\n(Push approval unavailable: listener not ready.)"
        last_exc = None
        for token in tokens:
            try:
                register_mfa_push_device(token, fcm_token)
                return "\n\nPush approval is enabled for this account."
            except Exception as exc:
                last_exc = exc
        return f"\n\n(Push approval registration failed: {last_exc})"

    def _valid_access_token(self, account):
        """A currently-valid access token for the account.

        Mints a fresh token from the stored SSO cookies (the persistent session —
        no re-login needed), so it always carries the current scopes (including
        session.auth for QR). Falls back to a cached token only if minting fails.
        """
        sso = account.get("sso")
        if sso:
            try:
                token = mint_access_token(sso)
            except Exception:
                token = None
            if token:
                account["access_token"] = token
                save_accounts(self.accounts)
                return token
        token = account.get("access_token")
        if token and is_valid_jwt(token):
            return token
        return None

    def _pick_account(self):
        """Choose which stored account to sign in with (the QR doesn't say which).

        Always asks, so you explicitly pick the account every time.
        """
        usable = [a for a in self.accounts if a.get("sso")]
        if not usable:
            QMessageBox.warning(
                self,
                "No usable account",
                "QR sign-in needs an account added via 'Add via Login'. "
                "Accounts added manually or before this feature can't sign in.",
            )
            return None

        labels = [a.get("name", "Unknown") for a in usable]
        for i, label in enumerate(labels):
            if labels.count(label) > 1:
                tail = (usable[i].get("puuid") or "")[:6] or str(i + 1)
                labels[i] = f"{label}  ·  {tail}"
        label, ok = QInputDialog.getItem(
            self, "Sign in with QR", "Choose the account to sign in:", labels, 0, False
        )
        if not ok:
            return None
        return usable[labels.index(label)]

    def _scan_qr(self):
        scanner = QrScannerDialog(self)
        if scanner.exec() != QDialog.DialogCode.Accepted or not scanner.result_text:
            return
        suuid, cluster = parse_qr_login(scanner.result_text)
        if not suuid or not cluster:
            QMessageBox.warning(
                self,
                "Not a Riot QR",
                "That QR code isn't a Riot sign-in code.",
            )
            return

        account = self._pick_account()
        if account is None:
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            token = self._valid_access_token(account)
            if not token:
                QApplication.restoreOverrideCursor()
                QMessageBox.warning(
                    self,
                    "Session expired",
                    f"Couldn't refresh the session for {account.get('name')}. "
                    "Re-add it via 'Add via Login'.",
                )
                return
            try:
                info = qr_session_info(token, suuid, cluster)
            except Exception as exc:
                info = {}
                self._qr_warn("Could not load the sign-in request", exc)
                return
        finally:
            QApplication.restoreOverrideCursor()

        confirm = QrConfirmDialog(account.get("name", "Account"), info, self)
        if confirm.exec() != QDialog.DialogCode.Accepted:
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            result = qr_approve(token, suuid, cluster, remember=True)
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            self._qr_warn("Sign-in failed", exc)
            return
        QApplication.restoreOverrideCursor()

        if result.get("success") is True or result == {}:
            self.toast.popup("Signed in ✓")
            QMessageBox.information(
                self, "Signed in", f"Approved the QR sign-in for {account.get('name')}."
            )
        else:
            QMessageBox.warning(
                self, "Sign-in not confirmed", f"Riot returned: {result}"
            )

    def _qr_warn(self, title, exc):
        detail = str(exc)
        try:
            if hasattr(exc, "response") and exc.response is not None:
                detail = f"HTTP {exc.response.status_code}: {exc.response.text[:300]}"
        except Exception:
            pass
        QMessageBox.warning(self, title, detail)

    def _add_manually(self):
        dlg = ManualAddDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_data:
            self.accounts.append(dlg.result_data)
            self._save_and_refresh()
