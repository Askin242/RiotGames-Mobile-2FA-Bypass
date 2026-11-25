"""Keep one running copy of the app per user session.

The first process owns a named lock and listens on a local socket. A later
launch finds the lock, asks the running copy to show its window, and exits.
"""

import getpass
import re
import sys
import time

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

_SHOW = b"show\n"
_ERROR_ALREADY_EXISTS = 183
_ASFW_ANY = 0xFFFFFFFF


def default_key():
    try:
        user = getpass.getuser()
    except Exception:
        user = "user"
    return "Riot2FA-" + re.sub(r"[^A-Za-z0-9_.-]", "_", user)


class SingleInstance(QObject):
    """Owns the per-user lock and forwards later launches to this process."""

    activation_requested = pyqtSignal()

    def __init__(self, key=None, parent=None):
        super().__init__(parent)
        self.key = key or default_key()
        self._mutex = None
        self._server = None

    def acquire(self):
        """Return True when this process is the first copy."""
        if sys.platform != "win32":
            return True
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        handle = kernel32.CreateMutexW(None, False, "Local\\" + self.key)
        if not handle:
            return True
        if ctypes.get_last_error() == _ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(ctypes.c_void_p(handle))
            return False
        self._mutex = handle
        return True

    def listen(self):
        self._server = QLocalServer(self)
        self._server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        self._server.newConnection.connect(self._on_connection)
        if not self._server.listen(self.key):
            QLocalServer.removeServer(self.key)
            self._server.listen(self.key)

    def activate_existing(self, timeout_s=5.0):
        """Ask the running copy to show itself. Return True when it was reached."""
        if sys.platform == "win32":
            try:
                import ctypes

                ctypes.windll.user32.AllowSetForegroundWindow(_ASFW_ANY)
            except Exception:
                pass
        deadline = time.monotonic() + timeout_s
        while True:
            sock = QLocalSocket()
            sock.connectToServer(self.key)
            if sock.waitForConnected(500):
                sock.write(_SHOW)
                sock.flush()
                sock.waitForBytesWritten(1000)
                sock.disconnectFromServer()
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.2)

    def close(self):
        if self._server is not None:
            self._server.close()
            self._server = None
        if self._mutex is not None:
            import ctypes

            ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(self._mutex))
            self._mutex = None

    def _on_connection(self):
        while self._server is not None and self._server.hasPendingConnections():
            sock = self._server.nextPendingConnection()
            sock.readyRead.connect(lambda s=sock: self._on_ready_read(s))
            sock.disconnected.connect(sock.deleteLater)
            if sock.bytesAvailable():
                self._on_ready_read(sock)

    def _on_ready_read(self, sock):
        if b"show" in bytes(sock.readAll()):
            self.activation_requested.emit()
