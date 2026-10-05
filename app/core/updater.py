"""Auto-update: check the GitHub releases for a newer version and apply it."""

import os
import sys
import subprocess
import tempfile
from urllib.parse import urlparse

import requests

from app.version import __version__, GITHUB_REPO

RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{GITHUB_REPO}/releases/latest"


def _parse(version):
    version = version.lstrip("vV").split("-")[0].split("+")[0]
    parts = []
    for piece in version.split("."):
        try:
            parts.append(int(piece))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def is_frozen():
    """True when running as a packaged build (Nuitka/PyInstaller) rather than source."""
    return bool(getattr(sys, "frozen", False)) or "__compiled__" in globals()


def check_for_update(timeout=8):
    """Return release info dict if a newer version exists, else None.

    Dict: {"tag", "version", "url", "asset_url"}.
    """
    try:
        resp = requests.get(
            RELEASES_API,
            headers={"Accept": "application/vnd.github+json"},
            timeout=timeout,
        )
        if resp.status_code != 200:
            return None
        release = resp.json()
        tag = release.get("tag_name") or ""
        if not tag or _parse(tag) <= _parse(__version__):
            return None
        assets = release.get("assets", [])
        installer = next(
            (a for a in assets if a.get("name", "").lower() == "riot2fa-setup.exe"),
            None,
        )
        portable = next(
            (a for a in assets if a.get("name", "").lower() == "riot2fa.exe"),
            None,
        )
        asset_url = (installer or portable or {}).get("browser_download_url")
        return {
            "tag": tag,
            "version": tag.lstrip("vV"),
            "url": release.get("html_url") or RELEASES_PAGE,
            "asset_url": asset_url,
            "notes": (release.get("body") or "").strip(),
        }
    except Exception:
        return None


def download_update(asset_url, progress_cb=None, timeout=120):
    """Download an installer to a temporary directory or a portable exe beside the app.

    `progress_cb(done_bytes, total_bytes)` is called as bytes arrive (total is
    0 when the server sends no Content-Length). Raises on failure.
    """
    installer = os.path.basename(urlparse(asset_url).path).lower() == "riot2fa-setup.exe"
    new_path = (
        os.path.join(tempfile.mkdtemp(prefix="riot2fa-update-"), "Riot2FA-Setup.exe")
        if installer else os.path.abspath(sys.argv[0]) + ".new"
    )
    try:
        with requests.get(asset_url, stream=True, timeout=timeout) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("Content-Length") or 0)
            done = 0
            with open(new_path, "wb") as out:
                for chunk in resp.iter_content(65536):
                    if not chunk:
                        continue
                    out.write(chunk)
                    done += len(chunk)
                    if progress_cb:
                        progress_cb(done, total)
        if total and done < total:
            raise IOError(f"Download incomplete ({done} of {total} bytes).")
    except Exception:
        try:
            os.remove(new_path)
        except OSError:
            pass
        if installer:
            try:
                os.rmdir(os.path.dirname(new_path))
            except OSError:
                pass
        raise
    return new_path


# Env vars the PyInstaller onefile bootloader sets in a running app to tell a
# re-executed copy which temp dir it already unpacked into. They MUST be cleared
# before relaunching the freshly-swapped exe, or its bootloader trusts this
# process's (about-to-be-deleted) dir and dies with "Failed to load python312.dll".
# 6.x uses the _PYI_* names; _MEIPASS2 is kept for older builds.
_PYI_HANDOFF_VARS = (
    "_MEIPASS2",
    "_PYI_APPLICATION_HOME_DIR",
    "_PYI_ARCHIVE_FILE",
    "_PYI_PARENT_PROCESS_LEVEL",
    "_PYI_SPLASH_IPC",
)


def launch_swap(new_path):
    """Start the installer, or swap and relaunch a portable executable."""
    env = dict(os.environ)
    for name in list(env):
        if name in _PYI_HANDOFF_VARS or name.startswith("_PYI"):
            env.pop(name, None)

    if os.path.basename(new_path).lower() == "riot2fa-setup.exe":
        subprocess.Popen([new_path], close_fds=True, env=env)
        return

    target = os.path.abspath(sys.argv[0])
    bat_path = target + ".update.bat"
    unset = "".join(f'set "{name}="\r\n' for name in _PYI_HANDOFF_VARS)
    script = (
        "@echo off\r\n"
        f"{unset}"
        ":waitdel\r\n"
        "ping 127.0.0.1 -n 2 >nul\r\n"
        f'del "{target}" >nul 2>&1\r\n'
        f'if exist "{target}" goto waitdel\r\n'
        ":domove\r\n"
        f'move /y "{new_path}" "{target}" >nul 2>&1\r\n'
        f'if not exist "{target}" ( ping 127.0.0.1 -n 2 >nul & goto domove )\r\n'
        f'start "" "{target}"\r\n'
        'del "%~f0"\r\n'
    )
    with open(bat_path, "w") as out:
        out.write(script)

    CREATE_NO_WINDOW = 0x08000000
    subprocess.Popen(
        ["cmd", "/c", bat_path],
        creationflags=CREATE_NO_WINDOW,
        close_fds=True,
        env=env,
    )
