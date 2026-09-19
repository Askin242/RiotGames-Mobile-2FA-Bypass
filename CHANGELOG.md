# Changelog

All notable changes to this project are documented here. The section whose
heading matches a release tag (e.g. `## v2.1.1`) is used as that release's notes,
with GitHub's auto-generated commit list appended below it.

## v2.1.2

### Fixed
- Push notifications now arrive reliably. A bug in the FCM library made it crash
  while decrypting an incoming push ("Incorrect padding") and shut the whole
  listener down, so no login approvals were delivered; the decryption is now
  padded correctly.

## v2.1.1

### Fixed
- Login-approval prompts no longer pile up on every launch. The FCM listener now
  persists which pushes it has seen and acknowledges them, so the server stops
  replaying its backlog of old login attempts.
- Auto-update no longer crashes with "Failed to load python312.dll" on restart.
  The updater clears the PyInstaller onefile hand-off variables before relaunch,
  downloads on a background thread with a progress bar, verifies the download,
  and runs the swap silently (no console windows).

### Added
- Detailed error dialog: a clear message plus an expandable, copy-pasteable pane
  showing the full server response (status, headers, body) for easy bug reports,
  with a Discord contact for help.
- Share & import accounts with a single code. Sharing carries the 2FA seed and
  sign-in session; on import the push device is re-registered so login approvals
  arrive on the importing machine.

## v2.1.0

### Changed
- Add-via-Login now uses a bundled stealth Chromium (Patchright) instead of the
  Qt WebEngine browser, which the login captcha was blocking.
