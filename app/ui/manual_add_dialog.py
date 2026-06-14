import base64

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QMessageBox,
)

from app.core import extract_seed

class ManualAddDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Account Manually")
        self.setFixedSize(420, 280)
        self.result_data = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(5)

        title = QLabel("Add Account")
        title.setObjectName("dialogTitle")
        lay.addWidget(title)
        lay.addSpacing(10)

        lbl1 = QLabel("ACCOUNT NAME")
        lbl1.setObjectName("fieldLabel")
        lay.addWidget(lbl1)
        self.inp_name = QLineEdit()
        self.inp_name.setPlaceholderText("e.g. MyRiotAccount")
        lay.addWidget(self.inp_name)
        lay.addSpacing(6)

        lbl2 = QLabel("SEED OR URL")
        lbl2.setObjectName("fieldLabel")
        lay.addWidget(lbl2)
        self.inp_seed = QLineEdit()
        self.inp_seed.setPlaceholderText("Base32 seed or qrlogin URL")
        lay.addWidget(self.inp_seed)
        lay.addSpacing(14)

        btns = QHBoxLayout()
        btns.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setObjectName("dialogCancelBtn")
        cancel.clicked.connect(self.reject)
        btns.addWidget(cancel)
        add = QPushButton("Add")
        add.setObjectName("dialogAddBtn")
        add.clicked.connect(self._on_add)
        btns.addWidget(add)
        lay.addLayout(btns)

    def _on_add(self):
        name = self.inp_name.text().strip()
        raw = self.inp_seed.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing Field", "Enter an account name.")
            return
        if not raw:
            QMessageBox.warning(self, "Missing Field", "Enter a seed or URL.")
            return
        seed = extract_seed(raw)
        if not seed:
            QMessageBox.warning(self, "Invalid Input", "Could not parse a seed from the input.")
            return
        try:
            base64.b32decode(seed.upper().encode("ascii"))
        except Exception:
            QMessageBox.warning(self, "Invalid Seed", "The seed is not valid base32.")
            return
        self.result_data = {"name": name, "seed": seed}
        self.accept()
