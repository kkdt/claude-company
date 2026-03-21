# Claude Company — Installation Guide

## Prerequisites

| Platform | Requirement |
|----------|-------------|
| Linux / macOS | Python 3.9+, `python3-venv` |
| Windows | Python 3.9+ (from python.org, with pip and venv included) |

---

## Linux / macOS

### 1. Run the installer

```bash
./install.sh
```

### 2. Answer the prompts

**Installation Paths** — press Enter to accept each default or type a custom path.

| Prompt | Default |
|--------|---------|
| Installation directory | `~/claude-company` |
| Data directory | `~/claude-company/data` |

**Security** — type a challenge word (input is hidden). You will be asked to confirm it. The word must match before the installer continues. It is saved to `.challenge_word` in the installation directory (readable only by your user account).

**Summary** — review the settings, then type `y` to proceed.

### 3. Optional: systemd service

If systemd is available you will be asked whether to install a user service that starts the application automatically on login.

### 4. Start the application

```bash
~/claude-company/claude-company.sh
```

Then open `http://localhost:8080` in your browser.

---

## Windows

### 1. Allow script execution (if not already set)

Open PowerShell as your normal user and run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 2. Run the installer

```powershell
.\install.ps1
```

### 3. Answer the prompts

**Installation Paths** — press Enter to accept each default or type a custom path.

| Prompt | Default |
|--------|---------|
| Installation directory | `%USERPROFILE%\claude-company` |
| Data directory | `%USERPROFILE%\claude-company\data` |

**Security** — type a challenge word (input is hidden). You will be asked to confirm it. The word must match before the installer continues. It is saved as a hidden file `.challenge_word` in the installation directory.

**Summary** — review the settings, then type `y` to proceed.

### 4. Optional: Start Menu shortcut

If a Start Menu is available you will be asked whether to create a shortcut.

### 5. Start the application

```powershell
& "$env:USERPROFILE\claude-company\claude-company.bat"
```

Or double-click `claude-company.bat` in the installation directory.

Then open `http://localhost:8080` in your browser.

---

## Security note

The challenge word is stored as a local, plain-text, hidden file at:

- **Linux / macOS:** `<install-dir>/.challenge_word` (permissions: `600`)
- **Windows:** `<install-dir>\.challenge_word` (hidden file attribute)

The launcher reads this file automatically on every start — no environment variable needs to be set manually. Keep the file safe and do not commit it to version control.

---

## Troubleshooting

**`venv module is not available`** (Linux)
```bash
# Debian / Ubuntu
sudo apt install python3-venv

# RHEL / Fedora
sudo dnf install python3
```

**`Python 3.9+ is required`**
Download the latest Python from [python.org](https://www.python.org/downloads/) and ensure it is on your PATH.

**`pip is not available`** (Windows)
Reinstall Python from [python.org](https://www.python.org/downloads/) and check the option to include pip during setup.
