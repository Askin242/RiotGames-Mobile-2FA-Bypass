import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from app.core import updater


class ReleaseHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/releases/latest":
            body = json.dumps({
                "tag_name": "v99.0",
                "assets": [
                    {"name": "Riot2FA.exe", "browser_download_url": self.server.base + "/Riot2FA.exe"},
                    {"name": "Riot2FA-Setup.exe", "browser_download_url": self.server.base + "/Riot2FA-Setup.exe"},
                ],
            }).encode()
            content_type = "application/json"
        elif self.path in ("/Riot2FA.exe", "/Riot2FA-Setup.exe"):
            body = b"update payload"
            content_type = "application/octet-stream"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


class UpdaterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), ReleaseHandler)
        cls.server.base = f"http://127.0.0.1:{cls.server.server_port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_installer_update_download_and_launch(self):
        with patch.object(updater, "RELEASES_API", self.server.base + "/releases/latest"):
            info = updater.check_for_update()
        self.assertEqual(info["asset_url"], self.server.base + "/Riot2FA-Setup.exe")
        progress = []
        path = Path(updater.download_update(info["asset_url"], progress_cb=lambda done, total: progress.append((done, total))))
        try:
            self.assertEqual(path.read_bytes(), b"update payload")
            self.assertEqual(progress[-1], (14, 14))
            with patch.dict(os.environ, {"_PYI_APPLICATION_HOME_DIR": "stale"}):
                with patch.object(updater.subprocess, "Popen") as popen:
                    updater.launch_swap(str(path))
            self.assertEqual(popen.call_args.args[0], [str(path)])
            self.assertNotIn("_PYI_APPLICATION_HOME_DIR", popen.call_args.kwargs["env"])
        finally:
            path.unlink()
            path.parent.rmdir()

    def test_portable_update_download(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "Riot2FA.exe"
            with patch.object(updater.sys, "argv", [str(target)]):
                path = Path(updater.download_update(self.server.base + "/Riot2FA.exe"))
            self.assertEqual(path, Path(str(target) + ".new"))
            self.assertEqual(path.read_bytes(), b"update payload")

    def test_cancelled_installer_download_is_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "Riot2FA-Setup.exe"
            with patch.object(updater.tempfile, "mkdtemp", return_value=directory):
                with self.assertRaisesRegex(RuntimeError, "cancelled"):
                    updater.download_update(
                        self.server.base + "/Riot2FA-Setup.exe",
                        progress_cb=lambda *_: (_ for _ in ()).throw(RuntimeError("cancelled")),
                    )
            self.assertFalse(target.exists())
