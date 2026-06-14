import os
import sys


def resource_path(relative):
    """Absolute path to a bundled resource, in source or frozen (PyInstaller) mode."""
    base = getattr(sys, "_MEIPASS", None)
    if base is None:
        base = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
    return os.path.join(base, relative)
