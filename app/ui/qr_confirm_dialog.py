import threading
from datetime import datetime

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal

from app.ui.mfa_prompt_dialog import reverse_geocode

def _extract_geo(info):
    """Pull (lat, lon, timestamp_ms) out of a session-info response."""
    for key in ("request", "auth_session"):
        node = info.get(key) if isinstance(info, dict) else None
        if isinstance(node, dict):
            geo = node.get("geolocation")
            if isinstance(geo, dict) and geo.get("lat") and geo.get("lon"):
                ts = node.get("timestamp") if isinstance(node.get("timestamp"), (int, str)) else None
                return geo.get("lat"), geo.get("lon"), ts
    return None, None, None

class QrConfirmDialog(QDialog):
    """Confirm a QR sign-in: shows account + login location, then Allow/Cancel."""

    _geocode_done = pyqtSignal(str)

    def __init__(self, account_name, info, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sign in with QR")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setMinimumWidth(380)
        self._lat, self._lon, ts = _extract_geo(info)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 18)
        lay.setSpacing(10)

        title = QLabel("Approve this sign-in?")
        title.setObjectName("dialogTitle")
        lay.addWidget(title)

        who = QLabel(account_name)
        who.setObjectName("accountName")
        lay.addWidget(who)

        self.lbl_location = QLabel("Location: locating…" if self._lat else "Location: unknown")
        self.lbl_location.setStyleSheet("color:#8888aa;")
        self.lbl_location.setOpenExternalLinks(True)
        self.lbl_location.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
        )
        lay.addWidget(self.lbl_location)

        if ts:
            try:
                when = datetime.fromtimestamp(int(ts) / 1000.0).strftime("%H:%M:%S")
            except (TypeError, ValueError):
                when = str(ts)
            t = QLabel(f"Time: {when}")
            t.setStyleSheet("color:#666677; font-size:11px;")
            lay.addWidget(t)

        lay.addSpacing(6)
        row = QHBoxLayout()
        row.setSpacing(8)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("dialogCancelBtn")
        cancel.clicked.connect(self.reject)
        row.addWidget(cancel)
        row.addStretch()
        allow = QPushButton("Allow")
        allow.setObjectName("dialogAddBtn")
        allow.clicked.connect(self.accept)
        row.addWidget(allow)
        lay.addLayout(row)

        self._geocode_done.connect(self.lbl_location.setText)
        if self._lat and self._lon:
            self._start_geocode()

    def _start_geocode(self):
        lat, lon = self._lat, self._lon

        def work():
            maps = f'<a href="https://www.google.com/maps?q={lat},{lon}" style="color:#7ec8e3;">map</a>'
            try:
                place = reverse_geocode(lat, lon)
            except Exception:
                place = None
            text = f"Location: {place} ({maps})" if place else f"Location: {lat}, {lon} ({maps})"
            self._geocode_done.emit(text)

        threading.Thread(target=work, daemon=True).start()
