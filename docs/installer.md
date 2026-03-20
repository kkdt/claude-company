# Installers

## Linux / Unix

● The installer is at install.sh. Here's what it does:

Prompts
- Installation directory (default $HOME/claude-company)
- Data directory (default $HOME/claude-company/data)
- Confirms before proceeding
- Optionally installs a systemd user service

Steps performed
1. Pre-flight checks — Python 3.9+, pip, venv
2. Creates both directories
3. Copies app.py, templates/, requirements.txt, sample CSVs, pip.conf
4. Handles the data path — since app.py resolves data files relative to its own location (os.path.dirname(__file__)), if the data dir differs from $INSTALL_DIR/data a symlink is created transparently (no code changes needed)
5. Seeds empty employees.json, projects.json, staffing.json if they don't exist yet
6. Creates a Python virtualenv and installs dependencies
7. Writes a claude-company.sh launcher that warns if CHALLENGE_WORD is unset
8. Optionally installs a ~/.config/systemd/user/claude-company.service

Usage
bash install.sh
export CHALLENGE_WORD=your-secret
~/claude-company/claude-company.sh

## Windows

install.ps1 — what it does:

  Prompts
  - Installation directory — default %USERPROFILE%\claude-company
  - Data directory — default %USERPROFILE%\claude-company\data
  - Confirms before proceeding
  - Optionally creates a Start Menu shortcut

  Steps performed
  1. Pre-flight — finds python / python3 / py, requires 3.9+, checks pip & venv
  2. Creates both directories
  3. Copies app.py, templates\, requirements.txt, sample CSVs, pip.conf
  4. Creates a directory junction (mklink /J) from $InstallDir\data → $DataDir when they differ (same transparent trick as the Linux installer — no changes to app.py needed)
  5. Seeds empty employees.json, projects.json, staffing.json
  6. Creates a Python virtualenv and installs dependencies
  7. Writes two launchers: claude-company.bat (cmd) and claude-company.ps1 (PowerShell), both warn if CHALLENGE_WORD is unset

  Usage
  # Run the installer (may need to allow scripts once)
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  .\install.ps1

  # Then start the app
  $env:CHALLENGE_WORD = "your-secret"
  ~\claude-company\claude-company.bat
