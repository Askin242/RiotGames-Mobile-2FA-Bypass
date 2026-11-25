import subprocess
import sys
import time
import unittest
import uuid
from pathlib import Path

from PyQt6.QtCore import QCoreApplication

from app.core.single_instance import SingleInstance

ROOT = Path(__file__).resolve().parents[1]

SECOND_LAUNCH = """
import sys
from PyQt6.QtCore import QCoreApplication
from app.core.single_instance import SingleInstance
app = QCoreApplication(sys.argv)
inst = SingleInstance(sys.argv[1])
if inst.acquire():
    sys.exit(3)  # should have found the running copy
sys.exit(0 if inst.activate_existing(timeout_s=5) else 4)
"""


class SingleInstanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication(sys.argv)

    def test_second_launch_activates_running_copy(self):
        key = "Riot2FA-test-" + uuid.uuid4().hex
        first = SingleInstance(key)
        self.addCleanup(first.close)
        self.assertTrue(first.acquire())
        first.listen()
        requests = []
        first.activation_requested.connect(lambda: requests.append(True))

        second = subprocess.Popen(
            [sys.executable, "-c", SECOND_LAUNCH, key], cwd=ROOT
        )
        deadline = time.monotonic() + 15
        while second.poll() is None or not requests:
            QCoreApplication.processEvents()
            if time.monotonic() > deadline:
                second.kill()
                self.fail("second launch did not reach the running copy")
            time.sleep(0.01)

        self.assertEqual(second.returncode, 0)
        self.assertEqual(requests, [True])

    def test_lock_is_free_again_after_close(self):
        key = "Riot2FA-test-" + uuid.uuid4().hex
        first = SingleInstance(key)
        self.assertTrue(first.acquire())
        first.listen()
        first.close()
        again = SingleInstance(key)
        self.addCleanup(again.close)
        self.assertTrue(again.acquire())


if __name__ == "__main__":
    unittest.main()
