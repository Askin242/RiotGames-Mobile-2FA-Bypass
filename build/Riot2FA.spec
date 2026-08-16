# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for Riot 2FA. Build it via build/build.py (which obfuscates
# with PyArmor first), or directly:  pyinstaller --clean -y build/Riot2FA.spec
#
# If build/obf/main.py exists (PyArmor output), it is used as the entry so the
# packaged code is obfuscated; otherwise the plain source is packed.

import os

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = os.path.dirname(os.path.abspath(SPECPATH))
OBF = os.path.join(SPECPATH, "obf")

if os.path.exists(os.path.join(OBF, "main.py")):
    entry = os.path.join(OBF, "main.py")
    pathex = [OBF, ROOT]
else:
    entry = os.path.join(ROOT, "main.py")
    pathex = [ROOT]

datas = [
    (os.path.join(ROOT, "images"), "images"),
    (os.path.join(ROOT, "app", "assets", "style.qss"), os.path.join("app", "assets")),
]
binaries = []
hiddenimports = []

# PyArmor obfuscation hides the app's imports from PyInstaller, so every
# third-party dependency must be declared explicitly here.
for pkg in (
    "firebase_messaging", "google.protobuf", "http_ece", "cryptography",
    "cv2", "numpy", "requests", "patchright", "greenlet", "pyee",
):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass
hiddenimports += collect_submodules("firebase_messaging")
hiddenimports += collect_submodules("patchright")

# PyQt6 (Widgets only — login uses Patchright's Chromium now, not WebEngine).
hiddenimports += [
    "PyQt6.sip",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "PyQt6.QtNetwork",
]

# Patchright's Node driver (node.exe + package/cli.js) — bundle the whole folder
# so the frozen app can spawn it. collect_all above may miss the non-.py driver.
import patchright  # noqa: E402

_pw_dir = os.path.dirname(patchright.__file__)
datas.append((os.path.join(_pw_dir, "driver"), os.path.join("patchright", "driver")))

# Patchright's Chromium (headed — needed for the login captcha). Detect the exact
# revision Patchright uses and bundle just that browser under ms-playwright/,
# which PLAYWRIGHT_BROWSERS_PATH points at in patchright_login._use_bundled_chromium.
import subprocess as _sp

try:
    _exe = _sp.check_output(
        [__import__("sys").executable, "-c",
         "from patchright.sync_api import sync_playwright;"
         "p=sync_playwright().start();print(p.chromium.executable_path);p.stop()"],
        text=True,
    ).strip().splitlines()[-1]
    _cdir = _exe
    while os.path.basename(_cdir) and not os.path.basename(_cdir).startswith("chromium-"):
        _cdir = os.path.dirname(_cdir)
    _ms_root = os.path.dirname(_cdir)
    datas.append((_cdir, os.path.join("ms-playwright", os.path.basename(_cdir))))
    for _ff in __import__("glob").glob(os.path.join(_ms_root, "ffmpeg-*")):
        datas.append((_ff, os.path.join("ms-playwright", os.path.basename(_ff))))
    print("[spec] bundling Chromium:", os.path.basename(_cdir))
except Exception as _e:
    print("[spec] WARNING: could not locate Patchright Chromium:", _e)

# The app's OWN modules are obfuscated too, so PyInstaller can't see them
# imported -- declare every app submodule (and the package) explicitly.
import glob

hiddenimports.append("app")
for _py in glob.glob(os.path.join(ROOT, "app", "**", "*.py"), recursive=True):
    _mod = os.path.relpath(_py, ROOT)[:-3].replace(os.sep, ".")
    if _mod.endswith(".__init__"):
        _mod = _mod[:-9]
    hiddenimports.append(_mod)

# PyArmor runtime, when packing the obfuscated build.
if entry.startswith(OBF):
    for name in os.listdir(OBF):
        if name.startswith("pyarmor_runtime"):
            hiddenimports.append(name)

a = Analysis(
    [entry],
    pathex=pathex,
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "tkinter", "matplotlib", "pytest",
        "PyQt6.QtWebEngineCore", "PyQt6.QtWebEngineWidgets",
        "PyQt6.QtWebEngineQuick", "PyQt6.QtWebChannel", "PyQt6.QtQuick",
        "PyQt6.QtQml",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Riot2FA",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                       # UPX raises AV false positives — keep off
    runtime_tmpdir=None,
    console=False,                   # GUI app, no console window
    disable_windowed_traceback=False,
    icon=os.path.join(ROOT, "images", "icon.ico"),
    version=os.path.join(SPECPATH, "version_info.txt")
    if os.path.exists(os.path.join(SPECPATH, "version_info.txt"))
    else None,
)
