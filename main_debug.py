"""Debug entrypoint: forces verbose logging on, then runs the app.

Packaged as the console build `Riot2FA_debug.exe` for diagnosing push issues.
"""

import os

os.environ.setdefault("RIOT2FA_DEBUG", "1")

from app.main import main

if __name__ == "__main__":
    main()
