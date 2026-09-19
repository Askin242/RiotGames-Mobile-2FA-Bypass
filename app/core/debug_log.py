"""Opt-in verbose logging for diagnosing push-notification problems.

Enabled when the env var ``RIOT2FA_DEBUG`` is set (the debug build sets it), or
via ``init(force=True)``. Writes to ``%APPDATA%/Riot2FA/debug.log`` and, when a
console is attached, to stderr. All logging calls elsewhere use the stdlib
``logging`` module at DEBUG level, so they are silent in normal builds.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler

from app.core.storage import APPDATA_DIR

LOG_FILE = os.path.join(APPDATA_DIR, "debug.log")

_FORCED = False
_INITED = False


def enabled():
    return _FORCED or bool(os.getenv("RIOT2FA_DEBUG"))


def init(force=False):
    """Attach file + console handlers at DEBUG level. Returns the log path."""
    global _FORCED, _INITED
    if force:
        _FORCED = True
    if not enabled() or _INITED:
        return LOG_FILE if _INITED else None

    os.makedirs(APPDATA_DIR, exist_ok=True)
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-7s %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S"
    )
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    fh = RotatingFileHandler(
        LOG_FILE, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)

    try:
        if sys.stderr is not None:
            ch = logging.StreamHandler(sys.stderr)
            ch.setFormatter(fmt)
            root.addHandler(ch)
    except Exception:
        pass

    # firebase_messaging is muted to CRITICAL in normal runs; open it up here.
    logging.getLogger("firebase_messaging").setLevel(logging.DEBUG)

    _INITED = True
    logging.getLogger(__name__).info("=== Riot2FA debug logging -> %s ===", LOG_FILE)
    return LOG_FILE


def mask(value):
    """Short, non-secret fingerprint of a token/cookie for logs."""
    if not value:
        return repr(value)
    s = str(value)
    if len(s) <= 12:
        return f"***(len={len(s)})"
    return f"{s[:6]}...{s[-4:]}(len={len(s)})"
