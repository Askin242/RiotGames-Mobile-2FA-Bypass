<div align="center">
  <h1 align="center">Riot Games Mobile 2FA Bypass</h1>
  <p align="center">
    A desktop port of the Riot Games mobile 2FA app — manage your own Riot 2FA codes directly from your PC.
      <br />
    <br />
    <a href="https://github.com/Askin242/RiotGames-Mobile-2FA-Bypass/issues">⚠️ Report Bug</a>
    ·
    <a href="https://github.com/Askin242/RiotGames-Mobile-2FA-Bypass/issues">💡 Request Feature</a>
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/language-Python-00ADD8?style=for-the-badge&labelColor=000000" />
    <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-6E56CF?style=for-the-badge&labelColor=000000" />
    <img src="https://img.shields.io/badge/status-Working-28A745?style=for-the-badge&labelColor=000000" />
  </p>
  <p align="center">
      <img src="./images/main.png" alt="Riot 2FA main window" />
  </p>
</div>

---

### 🔍 Overview

`Riot 2FA` is a desktop port of Riot's official mobile 2FA app. It lets you store and view the one-time passwords (TOTP codes) for your Riot Games account on your desktop instead of on your phone.

It uses Riot's own login flow to fetch your 2FA secret, stores it locally on your machine, and continuously generates valid 2FA codes for any accounts you add, wich allow to queue ranked without using any mobile device.
> All accounts secrets are stored in `%appdata%\Riot2FA\accounts.json`

### ⚠️ Important warning

- **You must already have 2FA enabled via email on your Riot account before you use this tool.**
- This tool does not remove, disable, or bypass two-factor authentication; it only gives you another way to see the same codes that your authenticator app would show.
- Only use this tool on accounts you own and control.

### ✨ Features

- **Clean desktop UI**: All your Riot accounts and codes in a single window.
- **Add via Login**: Log in with your username & password and instantly enable Riot Mobile from your desktop .
- **Add Manually**: Paste the TOTP secret from your Riot 2FA email or QR data and give it a custom account name.
- **Multiple accounts**: Manage more than one Riot account at the same time from the same device.
- **Push login approval**: Just like the mobile app - when someone logs into your account you get a desktop prompt showing the login's location and time, with **Allow / Refuse** buttons. The app stays in the system tray so prompts arrive even when the window is closed.
- **QR code sign-in**: Scan the Riot client's "sign in with QR" code straight off your screen (drag the little reader over it) to sign that account into the client — no phone needed. Uses your saved session, so it works any time.
- **Local storage**: Account data is stored locally in a simple JSON file alongside the app, wich mean control on your datas, and easily sharable.
- **Auto-update**: On launch the app checks GitHub for a newer release and, if one exists, offers to update with one click.

### 🎥 Video Tutorial

To have a full tutorial on how to use: [Click here](https://youtu.be/f1bqPi2Ku9E)

### 🖼️ Screenshot

Main window:

![Riot 2FA](./images/main.png)

### 🧰 Requirements

- Windows 10 or newer (tested)
- Python 3.10+ (only needed if running from source)
- Microsoft Edge or Google Chrome installed (used for the login window)
- Installed dependencies (PyQt6, requests, websocket-client)

---

### 🚀 Installation and usage

#### Option 1 — Download prebuilt release (recommended)

- Go to the [**Releases**](https://github.com/Askin242/RiotGames-Mobile-2FA-Bypass/releases) section of this project.
- Download `Riot2FA.exe`.
- Run it. The app checks for updates on launch and can update itself.

#### Option 2 — Run from source

1. Install Python 3.10+.
2. Clone or download this repository.
3. Open a terminal in the project root and install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Start the application:

   ```bash
   python main.py
   ```

#### Building the executable

The build is tuned for the **lowest antivirus false positives** (PyArmor + PyInstaller, UPX off, version resource, no Nuitka):

```bash
pip install -r build/requirements-build.txt
python build/build.py          # -> dist/Riot2FA.exe
```

For the absolute fewest false positives, first rebuild PyInstaller's bootloader with GCC — see [`build/BOOTLOADER.md`](build/BOOTLOADER.md).

---

### 📖 How to use

1. **Prepare your Riot account**
   - Make sure 2FA via email is already enabled for your Riot account.
   - Confirm you can receive and approve 2FA emails from Riot before using this tool.

2. **Add an account using "Add via Login"**
   - Open the app and click **Add via Login**.
   - A normal Edge/Chrome window opens — log in to your Riot account there.
   - After a successful login, the tool will attempt to enable or attach MFA and fetch the TOTP secret.
   - The account will appear in the list with a live 2FA code and timer.

3. **Add an account manually (optional)**
   - Click **Add Manually**.
   - Enter an account name and your TOTP secret key.
   - Save to start generating codes for that account.

4. **Logging in with a code**
   - When Riot asks to accept on the notification, click on enter a code.
   - Open this tool.
   - Find your account in the list and copy or type the current 6‑digit code into the Riot client.

5. **Approving a login from the push prompt**
   - Add the account with **Add via Login** — this also registers the account for push approval.
   - Keep the app running (it lives in the system tray; closing the window only hides it).
   - When you log in elsewhere and Riot offers "approve on your phone", a prompt appears on your desktop showing the login location and time.
   - Click **Allow** to let the login through, or **Refuse** to reject it.
   > Accounts added before this feature need to be re-added via login once to enable push approval.

6. **Signing in with a QR code**
   - In the Riot client, choose **Sign in with QR code**.
   - In this app, click the **▣** button, then drag the little reader over the QR code on screen.
   - Pick which account to sign in as, confirm the login location, and click **Allow**.
   - The Riot client signs in — no phone required. Works any time thanks to the saved session.
   > Requires an account added via **Add via Login** (so it has a saved session).

All account entries are persisted between runs, so you only need to add each account once.

---

### 🙌 Credits

- **Author**: [Sysy's](https://github.com/Askin242)

### 📜 License

This project is licensed under the **MIT License**. See `LICENSE` for details.
