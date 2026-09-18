from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QPlainTextEdit,
    QApplication,
)
from PyQt6.QtWidgets import QStyle
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QFont

from app.core.errors import describe_exception

DISCORD_CONTACT = "hsw.___"  # three trailing underscores

def _build_details(exc, details):
    parts = []
    if details:
        parts.append(details)
    if exc is not None:
        parts.append(describe_exception(exc))
    return "\n\n".join(parts).strip()

class ErrorDialog(QDialog):
    """A warning dialog with an expandable, copy-pasteable details pane."""

    def __init__(self, title, message, details="", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(440)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 18)
        lay.setSpacing(10)

        head = QHBoxLayout()
        head.setSpacing(10)
        icon = QLabel()
        icon.setPixmap(
            self.style()
            .standardIcon(QStyle.StandardPixmap.SP_MessageBoxCritical)
            .pixmap(QSize(26, 26))
        )
        icon.setFixedSize(26, 26)
        head.addWidget(icon, alignment=Qt.AlignmentFlag.AlignTop)
        heading = QLabel(title)
        heading.setObjectName("dialogTitle")
        heading.setWordWrap(True)
        head.addWidget(heading, stretch=1)
        lay.addLayout(head)

        msg = QLabel(message or "Something went wrong.")
        msg.setObjectName("errorMessage")
        msg.setWordWrap(True)
        msg.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(msg)

        self._details = details or ""
        if self._details:
            self.toggle = QPushButton("Show details ▾")
            self.toggle.setObjectName("detailsToggleBtn")
            self.toggle.setCheckable(True)
            self.toggle.clicked.connect(self._on_toggle)
            lay.addWidget(self.toggle, alignment=Qt.AlignmentFlag.AlignLeft)

            self.detail_box = QPlainTextEdit()
            self.detail_box.setObjectName("detailsBox")
            self.detail_box.setReadOnly(True)
            self.detail_box.setPlainText(self._details)
            self.detail_box.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
            self.detail_box.setFont(QFont("Consolas", 9))
            self.detail_box.setMinimumHeight(220)
            self.detail_box.hide()
            lay.addWidget(self.detail_box)

        contact = QLabel(
            f"Still stuck? Message me on Discord: "
            f"<span style='font-family:Consolas,monospace; color:#7ec8e3;'>"
            f"{DISCORD_CONTACT}</span> (three underscores)"
        )
        contact.setObjectName("contactLabel")
        contact.setWordWrap(True)
        contact.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(contact)

        lay.addSpacing(6)
        row = QHBoxLayout()
        row.setSpacing(8)
        if self._details:
            self.copy_btn = QPushButton("Copy details")
            self.copy_btn.setObjectName("dialogCancelBtn")
            self.copy_btn.clicked.connect(self._copy)
            row.addWidget(self.copy_btn)
        row.addStretch()
        ok = QPushButton("Close")
        ok.setObjectName("dialogAddBtn")
        ok.clicked.connect(self.accept)
        row.addWidget(ok)
        lay.addLayout(row)

    def _on_toggle(self, checked):
        self.detail_box.setVisible(checked)
        self.toggle.setText("Hide details ▴" if checked else "Show details ▾")
        self.adjustSize()

    def _copy(self):
        QApplication.clipboard().setText(self._details)
        self.copy_btn.setText("Copied ✓")
        QTimer.singleShot(1500, lambda: self.copy_btn.setText("Copy details"))

def show_error(parent, title, message, exc=None, details=""):
    """Show an error with an expandable details pane.

    `details` is free-form text; when `exc` is given, a full describe_exception
    dump (request/response/traceback) is appended automatically.
    """
    ErrorDialog(title, message, _build_details(exc, details), parent).exec()
