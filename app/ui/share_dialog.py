from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QPlainTextEdit,
    QApplication,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

class ShareCodeDialog(QDialog):
    """Shows a copy-pasteable share code for one account."""

    def __init__(self, account_name, code, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Share account")
        self.setMinimumWidth(460)
        self._code = code

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 18)
        lay.setSpacing(10)

        title = QLabel(f"Share “{account_name}”")
        title.setObjectName("dialogTitle")
        lay.addWidget(title)

        warn = QLabel(
            "Anyone with this code gets full access to the account (2FA seed and "
            "sign-in session). Only share it with people you trust."
        )
        warn.setObjectName("shareWarnLabel")
        warn.setWordWrap(True)
        lay.addWidget(warn)

        self.box = QPlainTextEdit()
        self.box.setObjectName("detailsBox")
        self.box.setReadOnly(True)
        self.box.setPlainText(code)
        self.box.setFont(QFont("Consolas", 9))
        self.box.setMinimumHeight(120)
        lay.addWidget(self.box)

        lay.addSpacing(6)
        row = QHBoxLayout()
        row.setSpacing(8)
        self.copy_btn = QPushButton("Copy code")
        self.copy_btn.setObjectName("dialogCancelBtn")
        self.copy_btn.clicked.connect(self._copy)
        row.addWidget(self.copy_btn)
        row.addStretch()
        ok = QPushButton("Done")
        ok.setObjectName("dialogAddBtn")
        ok.clicked.connect(self.accept)
        row.addWidget(ok)
        lay.addLayout(row)

    def _copy(self):
        QApplication.clipboard().setText(self._code)
        self.copy_btn.setText("Copied ✓")
        QTimer.singleShot(1500, lambda: self.copy_btn.setText("Copy code"))
