import PyQt6.QtWidgets as QtW
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import QLabel, QGraphicsOpacityEffect

class Toast(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("toast")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(34)
        self.hide()

        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity)

        self._fade_in = QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade_in.setDuration(200)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)

        self._fade_out = QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade_out.setDuration(400)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.setEasingCurve(QEasingCurve.Type.InQuad)
        self._fade_out.finished.connect(self.hide)

        self._hold = QTimer(self)
        self._hold.setSingleShot(True)
        self._hold.timeout.connect(self._fade_out.start)

    def popup(self, text, ms=1400):
        self.setText(f"  {text}  ")
        self.adjustSize()
        self.setFixedWidth(self.sizeHint().width() + 24)
        p = self.parent()
        if p:
            self.move((p.width() - self.width()) // 2, p.height() - self.height() - 16)
        self._fade_out.stop()
        self._hold.stop()
        self._opacity.setOpacity(0.0)
        self.show()
        self.raise_()
        self._fade_in.start()
        self._hold.start(ms)
