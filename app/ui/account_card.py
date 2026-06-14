from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QMenu,
    QProgressBar,
    QGraphicsBlurEffect,
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QCursor

from app.core import get_code

class AccountCard(QFrame):
    remove_requested = pyqtSignal(str, str)
    copy_requested = pyqtSignal()

    def __init__(self, name, seed, parent=None):
        super().__init__(parent)
        self.setObjectName("accountCard")
        self.account_name = name
        self.seed = seed
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(62)

        self._blur = QGraphicsBlurEffect(self)
        self._blur.setBlurRadius(20)

        self._blur_anim = QPropertyAnimation(self._blur, b"blurRadius", self)
        self._blur_anim.setDuration(250)
        self._blur_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 10, 14, 6)
        root.setSpacing(4)

        top = QHBoxLayout()
        top.setSpacing(0)

        lbl_name = QLabel(name)
        lbl_name.setObjectName("accountName")
        top.addWidget(lbl_name)

        top.addStretch()

        self.lbl_code = QLabel("------")
        self.lbl_code.setObjectName("codeLabel")
        self.lbl_code.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.lbl_code.setToolTip("Click to copy")
        self.lbl_code.setGraphicsEffect(self._blur)
        self.lbl_code.mousePressEvent = self._copy_code
        top.addWidget(self.lbl_code)

        top.addSpacing(12)

        self.lbl_timer = QLabel("30s")
        self.lbl_timer.setObjectName("timerLabel")
        self.lbl_timer.setFixedWidth(24)
        self.lbl_timer.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top.addWidget(self.lbl_timer)

        top.addSpacing(8)

        btn_menu = QPushButton("\u22EE")
        btn_menu.setObjectName("menuBtn")
        btn_menu.setFixedWidth(30)
        btn_menu.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        menu = QMenu(self)
        menu.addAction("View Seed", self._show_seed)
        menu.addAction("Copy Seed", self._copy_seed)
        menu.addSeparator()
        menu.addAction("Remove", self._confirm_remove)
        btn_menu.setMenu(menu)
        top.addWidget(btn_menu)

        root.addLayout(top)

        self.bar = QProgressBar()
        self.bar.setRange(0, 1000)
        self.bar.setValue(1000)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(3)
        root.addWidget(self.bar)

        self.refresh_code()

    def _animate_blur(self, target):
        self._blur_anim.stop()
        self._blur_anim.setStartValue(self._blur.blurRadius())
        self._blur_anim.setEndValue(target)
        self._blur_anim.start()

    def enterEvent(self, event):
        self._animate_blur(0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animate_blur(20)
        super().leaveEvent(event)

    def refresh_code(self):
        try:
            self.lbl_code.setText(get_code(self.seed))
        except Exception:
            self.lbl_code.setText("ERROR")

    def update_bar(self, remaining_frac, remaining_sec):
        self.bar.setValue(int(remaining_frac * 1000))
        self.lbl_timer.setText(f"{remaining_sec}s")

    def _copy_code(self, _event):
        txt = self.lbl_code.text()
        if txt and txt not in ("------", "ERROR"):
            QApplication.clipboard().setText(txt)
            self.copy_requested.emit()

    def _show_seed(self):
        from PyQt6.QtWidgets import QMessageBox

        box = QMessageBox(self)
        box.setWindowTitle("Seed")
        box.setText(self.account_name)
        box.setInformativeText(self.seed)
        box.setStandardButtons(QMessageBox.StandardButton.Ok)
        box.exec()

    def _copy_seed(self):
        QApplication.clipboard().setText(self.seed)
        self.copy_requested.emit()

    def _confirm_remove(self):
        from PyQt6.QtWidgets import QMessageBox

        box = QMessageBox(self)
        box.setWindowTitle("Remove Account")
        box.setText(f"Remove 2FA for \"{self.account_name}\"?")
        box.setInformativeText("This cannot be undone.")
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        if box.exec() == QMessageBox.StandardButton.Yes:
            self.remove_requested.emit(self.account_name, self.seed)
