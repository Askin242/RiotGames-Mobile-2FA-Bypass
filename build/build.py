"""Build Riot2FA.exe with the lowest AV false-positive footprint.

Pipeline (proven to minimise false positives):
    PyArmor obfuscate  ->  PyInstaller pack (UPX off, version resource on)

For the very lowest count, also use a PyInstaller bootloader rebuilt with GCC
(MinGW) instead of MSVC — see build/BOOTLOADER.md. This script uses whatever
PyInstaller is installed, so install your GCC-built one first.

Usage:
    python build/build.py                # obfuscate + pack
    python build/build.py --no-obfuscate # plain PyInstaller (more false positives)
"""

import os
import sys
import shutil
import subprocess

BUILD_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BUILD_DIR)
OBF = os.path.join(BUILD_DIR, "obf")
SPEC = os.path.join(BUILD_DIR, "Riot2FA.spec")
WORK = os.path.join(BUILD_DIR, "_work")
DIST = os.path.join(ROOT, "dist")

sys.path.insert(0, ROOT)
from app.version import __version__  # noqa: E402


def _have(module):
    try:
        subprocess.run(
            [sys.executable, "-m", module, "--version"],
            capture_output=True, check=True,
        )
        return True
    except Exception:
        return False


def write_version_info():
    parts = (__version__.split(".") + ["0", "0", "0", "0"])[:4]
    nums = tuple(int(p) if p.isdigit() else 0 for p in parts)
    content = f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={nums}, prodvers={nums},
    mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
        StringStruct('CompanyName', 'Sysys'),
        StringStruct('FileDescription', 'Riot 2FA'),
        StringStruct('FileVersion', '{__version__}'),
        StringStruct('InternalName', 'Riot2FA'),
        StringStruct('OriginalFilename', 'Riot2FA.exe'),
        StringStruct('ProductName', 'Riot 2FA'),
        StringStruct('ProductVersion', '{__version__}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])]
)
"""
    path = os.path.join(BUILD_DIR, "version_info.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[build] wrote version resource ({__version__})")


def clean():
    for path in (OBF, WORK, DIST):
        shutil.rmtree(path, ignore_errors=True)
    print("[build] cleaned obf / work / dist")


def obfuscate():
    if not _have("pyarmor.cli"):
        print("[build] PyArmor not installed -> skipping obfuscation "
              "(pip install pyarmor for fewer false positives)")
        return False
    print("[build] obfuscating with PyArmor ...")
    subprocess.run(
        [sys.executable, "-m", "pyarmor.cli", "gen", "-O", OBF, "-r", "app", "main.py"],
        cwd=ROOT, check=True,
    )
    return True


def package():
    if not _have("PyInstaller"):
        sys.exit("[build] PyInstaller not installed (pip install pyinstaller).")
    print("[build] packing with PyInstaller ...")
    subprocess.run(
        [
            sys.executable, "-m", "PyInstaller", "--clean", "-y",
            "--workpath", WORK, "--distpath", DIST, SPEC,
        ],
        cwd=ROOT, check=True,
    )


def main():
    do_obf = "--no-obfuscate" not in sys.argv
    write_version_info()
    clean()
    if do_obf:
        obfuscate()
    package()
    exe = os.path.join(DIST, "Riot2FA.exe")
    print("\n[build] done ->", exe if os.path.exists(exe) else DIST)
    print("[build] for the lowest false positives, build with a GCC-rebuilt "
          "PyInstaller bootloader (see build/BOOTLOADER.md).")


if __name__ == "__main__":
    main()
