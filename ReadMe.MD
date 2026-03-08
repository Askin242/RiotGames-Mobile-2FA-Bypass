<div align="center">
  <h1 align="center">Riot Games Mobile 2FA Bypass</h1>
  <p align="center">
    Desktop client to manage your own Riot Games mobile 2FA codes directly from your PC.
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

`Riot 2FA` is a small utility that lets you store and view the one-time passwords (TOTP codes) for your Riot Games account on your desktop instead of using the official mobile 2FA app.

It uses Riot's own login flow to fetch your 2FA secret, stores it locally on your machine, and continuously generates valid 2FA codes for any accounts you add, wich allow to queue ranked without using any mobile device.
> All accounts secrets are stored in `%appdata%\Riot2FA\accounts.json`

### ⚠️ Important warning

- **You must already have 2FA enabled via email on your Riot account before you use this tool.**
- This tool does not remove, disable, or bypass two-factor authentication; it only gives you another way to see the same codes that your authenticator app would show.
- Only use this tool on accounts you own and control.

### ✨ Features

- **Clean desktop UI**: All your Riot accounts and codes in a single window.
- **Add via Login**: Log in once through an embedded browser; the tool automatically extracts your 2FA secret and starts generating codes.
- **Add Manually**: Paste the TOTP secret from your Riot 2FA email or QR data and give it a custom account name.
- **Multiple accounts**: Manage more than one Riot account at the same time.
- **Quick copy**: Click to copy codes to your clipboard for easy pasting into the Riot client.
- **Local storage**: Account data is stored locally in a simple JSON file alongside the app, wich mean control on your datas, and easily sharable.

### 🖼️ Screenshot

Main window:

![Riot 2FA](./images/main.png)

### 🧰 Requirements

- Windows 10 or newer (tested)
- Python 3.10+ (only needed if running from source)
- Installed dependencies (PyQt6, PyQt6-WebEngine, requests)

---

### 🚀 Installation and usage

#### Option 1 — Download prebuilt release (recommended)

- Go to the [**Releases**](https://github.com/Askin242/RiotGames-Mobile-2FA-Bypass/releases/tag/v1.0.0) section of this project.
- Download the latest archive for your platform.
- Extract the contents somewhere on your machine.
- Run the provided executable (for example `Riot2FA.exe`) to start the app.
⚠️ [Nuitka](https://github.com/Nuitka/Nuitka) is kinda slow using PyQt6, it might take 30+ seconds to start.

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

---

### 📖 How to use

1. **Prepare your Riot account**
   - Make sure 2FA via email is already enabled for your Riot account.
   - Confirm you can receive and approve 2FA emails from Riot before using this tool.

2. **Add an account using "Add via Login"**
   - Open the app and click **Add via Login**.
   - Log in to your Riot account in the embedded browser window.
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

All account entries are persisted between runs, so you only need to add each account once.

---

### 🙌 Credits

- **Author**: [Sysy's](https://github.com/Askin242)

### 📜 License

This project is licensed under the **MIT License**. See `LICENSE` for details.
