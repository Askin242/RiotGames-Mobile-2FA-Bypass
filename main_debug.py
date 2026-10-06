"""Manual diagnostic entry point, separate from the release build."""

import logging

from app.core import debug_log

# Debug logging is enabled only when this script is run directly.
debug_log.init(force=True)

if __name__ == "__main__":
    try:
        from app.main import main

        main()
    except Exception:
        logging.getLogger(__name__).exception("Debug build startup failed")
        raise
