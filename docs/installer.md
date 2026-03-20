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

## Single-file executable (Linux / Unix)

● For a Flask app like this, PyInstaller is the standard approach. Here's how:

  1. Install PyInstaller

  source venv/bin/activate
  pip install pyinstaller

  2. Build the executable

  pyinstaller --onefile \
    --add-data "templates:templates" \
    --name claude-company \
    app.py

  - --onefile — bundles everything into a single binary
  - --add-data "templates:templates" — embeds the Jinja2 templates folder
  - Output lands in dist/claude-company

  3. Fix the template path in app.py

  PyInstaller extracts bundled files to a temp dir at runtime (sys._MEIPASS). Flask won't find the templates unless you account for this:

● Read 1 file (ctrl+o to expand)

● You need a small change to app.py lines 8-9 so Flask finds the embedded templates:

  import sys

  # Resolve template folder whether running normally or frozen by PyInstaller
  _base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
  app = Flask(__name__, template_folder=os.path.join(_base, 'templates'))

  4. Full build steps (from repo root)

  source venv/bin/activate
  pip install pyinstaller

  pyinstaller --onefile \
    --add-data "templates:templates" \
    --name claude-company \
    app.py

  # Test it
  DATA_DIR=./data CHALLENGE_WORD=secret dist/claude-company

  Notes

  ┌─────────────┬──────────────────────────────────────────────────────────────────────────────────────────────────┐
  │   Concern   │                                              Detail                                              │
  ├─────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Data files  │ data/*.json are not embedded — they live outside the binary (correct behaviour, they're mutable) │
  ├─────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Binary size │ Expect ~15–25 MB; Flask + Werkzeug + deps all get bundled                                        │
  ├─────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Platform    │ The binary is Linux-only — build on the target OS/arch                                           │
  ├─────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ --strip     │ Add --strip to shave ~20% off the binary size                                                    │
  ├─────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Spec file   │ PyInstaller generates claude-company.spec — commit it for reproducible builds                    │
  └─────────────┴──────────────────────────────────────────────────────────────────────────────────────────────────┘

  Distributing

  dist/claude-company        ← the single binary
  data/
    employees.json
    projects.json
    staffing.json

  Ship the binary alongside an empty data/ directory (or let the installer create it). The install.sh you already have can be updated to run the binary instead of python app.py.


## Single-file executable (Windows)

❯ How do I build single file executable to run this application on Windows host?

● The process mirrors Linux — PyInstaller on Windows — but must be run on a Windows machine (PyInstaller cannot cross-compile).

  Requirements

  - Python 3.9+ installed with pip and venv checked
  - Run in Command Prompt or PowerShell

  Steps

  1. Set up the virtual environment
  cd claude-company
  python -m venv venv
  venv\Scripts\activate
  pip install -r requirements.txt
  pip install pyinstaller

  2. Build the executable
  pyinstaller --onefile --strip --name claude-company --add-data "templates;templates" app.py

  ▎ Note the separator is semicolon (;) on Windows, not colon.

  Output: dist\claude-company.exe

  3. Assemble the package
  mkdir dist\claude-company-package
  move dist\claude-company.exe dist\claude-company-package\
  mkdir dist\claude-company-package\data
  echo [] > dist\claude-company-package\data\employees.json
  echo [] > dist\claude-company-package\data\projects.json
  echo [] > dist\claude-company-package\data\staffing.json

  4. Run it
  set CHALLENGE_WORD=your-secret
  dist\claude-company-package\claude-company.exe

  Then open http://localhost:8080.

  ---
  Add a build.ps1 script?

  I can create a build.ps1 that automates all of this — with the same --clean flag, Git tag versioning, and a .zip archive — mirroring what build.sh does on Linux. Want me to do that?
  