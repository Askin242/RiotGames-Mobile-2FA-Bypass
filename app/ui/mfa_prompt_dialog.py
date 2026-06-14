import time
import threading
from datetime import datetime

import requests

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
)
from PyQt6.QtCore import Qt, pyqtSignal

from app.api import respond_to_mfa

def _format_time(attempted_at):
    try:
        ts = int(attempted_at) / 1000.0
        return datetime.fromtimestamp(ts).strftime("%H:%M:%S")
    except (TypeError, ValueError):
        return "just now"

def reverse_geocode(lat, lon, timeout=6):
    """Resolve coordinates to 'City, Country' via OpenStreetMap Nominatim."""
    resp = requests.get(
        "https://nominatim.openstreetmap.org/reverse",
        params={"lat": lat, "lon": lon, "format": "json", "zoom": 10},
        headers={"User-Agent": "Riot2FA-Desktop/1.0"},
        timeout=timeout,
    )
    resp.raise_for_status()
    addr = resp.json().get("address", {})
    city = (
        addr.get("city")
        or addr.get("town")
        or addr.get("village")
        or addr.get("county")
        or addr.get("state")
    )
    country = addr.get("country")
    parts = [p for p in (city, country) if p]
    return ", ".join(parts) if parts else None

class MfaPromptDialog(QDialog):
    """Allow/Refuse prompt for an incoming login attempt received via push."""

    _geocode_done = pyqtSignal(str)
    _respond_done = pyqtSignal(bool, str)

    def __init__(self, push, account, parent=None):
        super().__init__(parent)
        self.push = push
        self.account = account
        self._answered = False
        self._pending_approve = None
        self.outcome = None

        self.setWindowTitle("Login Attempt")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setMinimumWidth(380)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 18)
        lay.setSpacing(10)

        title = QLabel("Login attempt")
        title.setObjectName("dialogTitle")
        lay.addWidget(title)

        gn = push.get("riot_id_game_name")
        tl = push.get("riot_id_tag_line")
        if gn and tl:
            who = f"{gn}#{tl}"
        elif gn:
            who = gn
        else:
            who = account.get("name", "Unknown account")
        lbl_who = QLabel(who)
        lbl_who.setObjectName("accountName")
        lay.addWidget(lbl_who)

        self.lbl_location = QLabel("Location: locating…")
        self.lbl_location.setStyleSheet("color:#8888aa;")
        self.lbl_location.setOpenExternalLinks(True)
        self.lbl_location.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
        )
        lay.addWidget(self.lbl_location)

        lbl_time = QLabel(f"Time: {_format_time(push.get('attempted_at'))}")
        lbl_time.setStyleSheet("color:#666677; font-size:11px;")
        lay.addWidget(lbl_time)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color:#aaaa55; font-size:11px;")
        self.lbl_status.hide()
        lay.addWidget(self.lbl_status)

        lay.addSpacing(6)
        row = QHBoxLayout()
        row.setSpacing(8)
        self.btn_refuse = QPushButton("Refuse")
        self.btn_refuse.setObjectName("dialogCancelBtn")
        self.btn_refuse.clicked.connect(lambda: self._respond(False))
        row.addWidget(self.btn_refuse)
        row.addStretch()
        self.btn_allow = QPushButton("Allow")
        self.btn_allow.setObjectName("dialogAddBtn")
        self.btn_allow.clicked.connect(lambda: self._respond(True))
        row.addWidget(self.btn_allow)
        lay.addLayout(row)

        self._geocode_done.connect(self.lbl_location.setText)
        self._respond_done.connect(self._on_respond_done)

        self._start_geocode()

    def _start_geocode(self):
        lat = self.push.get("geolocation_latitude")
        lon = self.push.get("geolocation_longitude")
        if not lat or not lon:
            self.lbl_location.setText("Location: unknown")
            return

        def work():
            maps = f'<a href="https://www.google.com/maps?q={lat},{lon}" style="color:#7ec8e3;">map</a>'
            try:
                place = reverse_geocode(lat, lon)
            except Exception:
                place = None
            if place:
                text = f"Location: {place} ({maps})"
            else:
                text = f"Location: {lat}, {lon} ({maps})"
            self._geocode_done.emit(text)

        threading.Thread(target=work, daemon=True).start()

    def _respond(self, approve):
        if self._answered:
            return
        self._answered = True
        self._pending_approve = approve
        self.btn_allow.setEnabled(False)
        self.btn_refuse.setEnabled(False)
        self.lbl_status.setText("Allowing…" if approve else "Refusing…")
        self.lbl_status.show()

        push = self.push
        seed = self.account.get("seed")

        def work():
            try:
                respond_to_mfa(
                    push.get("suuid"),
                    push.get("cluster"),
                    push.get("puuid"),
                    seed,
                    approve,
                )
                self._respond_done.emit(True, "approved" if approve else "denied")
            except requests.HTTPError as exc:
                code = exc.response.status_code if exc.response is not None else 0
                if code in (400, 404, 409, 410):
                    self._respond_done.emit(False, "expired")
                else:
                    self._respond_done.emit(False, f"error ({code})")
            except Exception:
                self._respond_done.emit(False, "error")

        threading.Thread(target=work, daemon=True).start()

    def _on_respond_done(self, ok, detail):
        if ok:
            self.outcome = "approved" if self._pending_approve else "denied"
            self.accept()
            return

        self._answered = False
        self.btn_allow.setEnabled(True)
        self.btn_refuse.setEnabled(True)
        if detail == "expired":
            self.lbl_status.setText("This attempt expired or was already handled.")
        else:
            self.lbl_status.setText(f"Could not respond — {detail}. Try again.")
