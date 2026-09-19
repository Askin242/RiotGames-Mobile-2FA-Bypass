import os
import sys

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from app.styles import load_stylesheet
from app.core.paths import resource_path
from app.core import debug_log
from app.ui import MainWindow

ICON_PATH = resource_path(os.path.join("images", "icon.png"))


def _set_app_id():
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "sysys.riot2fa.desktop"
            )
        except Exception:
            pass


def main():
    log_path = debug_log.init()
    if log_path:
        import logging

        from app.version import __version__

        logging.getLogger(__name__).info(
            "Riot2FA v%s starting (debug logging active) -> %s", __version__, log_path
        )
    _set_app_id()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(load_stylesheet())
    app.setWindowIcon(QIcon(ICON_PATH))
    app.setQuitOnLastWindowClosed(False)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
