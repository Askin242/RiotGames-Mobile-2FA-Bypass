from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
)
from PyQt6.QtCore import Qt

class UpdateDialog(QDialog):
    """'Update available' prompt showing the release notes; accept = update now."""

    def __init__(self, current_version, info, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Update available")
        self.setMinimumWidth(500)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 18)
        lay.setSpacing(10)

        title = QLabel(f"Version {info.get('version', '?')} is available")
        title.setObjectName("dialogTitle")
        lay.addWidget(title)

        sub = QLabel(f"You have {current_version}. What's new:")
        sub.setObjectName("errorMessage")
        sub.setWordWrap(True)
        lay.addWidget(sub)

        notes = QTextBrowser()
        notes.setObjectName("detailsBox")
        notes.setOpenExternalLinks(True)
        notes.setMarkdown(info.get("notes") or "_No release notes provided._")
        notes.setMinimumHeight(240)
        lay.addWidget(notes)

        lay.addSpacing(6)
        row = QHBoxLayout()
        row.setSpacing(8)
        later = QPushButton("Later")
        later.setObjectName("dialogCancelBtn")
        later.clicked.connect(self.reject)
        row.addWidget(later)
        row.addStretch()
        update = QPushButton("Update now")
        update.setObjectName("dialogAddBtn")
        update.setDefault(True)
        update.clicked.connect(self.accept)
        row.addWidget(update)
        lay.addLayout(row)
