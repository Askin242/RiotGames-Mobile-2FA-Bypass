"""Auto-update: check the GitHub releases for a newer version and apply it."""

import os
import sys
import subprocess

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
        asset_url = None
        for asset in release.get("assets", []):
            if asset.get("name", "").lower().endswith(".exe"):
                asset_url = asset.get("browser_download_url")
                break
        return {
            "tag": tag,
            "version": tag.lstrip("vV"),
            "url": release.get("html_url") or RELEASES_PAGE,
            "asset_url": asset_url,
        }
    except Exception:
        return None


def apply_exe_update(asset_url):
    """Download the new exe and swap it via a helper batch, then exit.

    Only valid for a frozen Windows build. Raises on download failure.
    """
    target = os.path.abspath(sys.argv[0])
    new_path = target + ".new"
    with requests.get(asset_url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        with open(new_path, "wb") as out:
            for chunk in resp.iter_content(65536):
                out.write(chunk)

    bat_path = target + ".update.bat"
    script = (
        "@echo off\r\n"
        ":wait\r\n"
        "timeout /t 1 /nobreak >nul\r\n"
        f'del "{target}" >nul 2>&1\r\n'
        f'if exist "{target}" goto wait\r\n'
        f'move /y "{new_path}" "{target}" >nul\r\n'
        f'start "" "{target}"\r\n'
        'del "%~f0"\r\n'
    )
    with open(bat_path, "w") as out:
        out.write(script)

    creationflags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(["cmd", "/c", bat_path], creationflags=creationflags, close_fds=True)
    sys.exit(0)
