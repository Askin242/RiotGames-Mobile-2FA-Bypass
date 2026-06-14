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
    "cv2", "numpy", "requests", "websocket",
):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass
hiddenimports += collect_submodules("firebase_messaging")
# PyQt6 (Widgets only — no WebEngine, login now uses the system browser via CDP).
hiddenimports += [
    "PyQt6.sip",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "PyQt6.QtNetwork",
]

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
        "PyQt6.QtQml", "PyQt6.QtPrintSupport",
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
