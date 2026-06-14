import os

from app.core.paths import resource_path


def load_stylesheet():
    path = resource_path(os.path.join("app", "assets", "style.qss"))
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""
