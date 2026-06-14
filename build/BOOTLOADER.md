# Rebuilding the PyInstaller bootloader with GCC (lowest false positives)

Most AV false positives come from the **default PyInstaller bootloader**, which
is shipped pre-compiled with MSVC and is identical across millions of apps — so
AV heuristics flag it. Rebuilding it yourself with **GCC (MinGW-w64)** produces a
unique binary that AV engines don't recognise. Combined with PyArmor (see
`build.py`), this took the project from ~16 false positives to **1**. (see https://stackoverflow.com/a/79004611)

Do this **once**; afterwards `build/build.py` uses your rebuilt PyInstaller.

## 1. Install MinGW-w64 (GCC for Windows)
Easiest via [MSYS2](https://www.msys2.org/):
```
# in the MSYS2 MinGW64 shell:
pacman -S --needed mingw-w64-x86_64-gcc mingw-w64-x86_64-python
```
Then add `C:\msys64\mingw64\bin` to your PATH (so `gcc --version` works in a
normal terminal).

## 2. Get the PyInstaller source (same version you'll use)
```
pip download pyinstaller --no-binary :all: --no-deps -d pyinstaller-src
# or: git clone https://github.com/pyinstaller/pyinstaller
cd pyinstaller            # the extracted/cloned source
```

## 3. Build the bootloader with GCC
```
cd bootloader
python ./waf distclean all --target-arch=64bit --gcc
cd ..
```
`--gcc` forces the MinGW toolchain. You should see freshly compiled
`run.exe` / `run_d.exe` etc. under `PyInstaller/bootloader/Windows-64bit*/`.

## 4. Install your custom PyInstaller
```
pip install .          # from the pyinstaller source root
```
Verify:
```
pyinstaller --version
```

## 5. Build the app
```
pip install -r build/requirements-build.txt   # pyarmor (pyinstaller already custom)
python build/build.py
```
Output: `dist/Riot2FA.exe`.

## Other things that keep false positives down (already configured)
- **No UPX** (`upx=False` in the spec) — packers are a top AV trigger.
- **Version resource** — `build.py` stamps CompanyName / ProductName / version,
  so the exe looks like a real product rather than an anonymous blob.
- **PyArmor obfuscation** — avoids the plain-PyInstaller code signature.
- **Never Nuitka one-file** — it produced the most false positives in testing.
