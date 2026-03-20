# Building Claude Company

Produces a single self-contained executable and a distributable archive.

┌──────────────────────────────────┬──────────┬────────────────────────┐
│             Feature              │ build.sh │       build.ps1        │
├──────────────────────────────────┼──────────┼────────────────────────┤
│ --clean / -Clean flag            │ ✓        │ ✓                      │
├──────────────────────────────────┼──────────┼────────────────────────┤
│ Git tag versioning (strips v)    │ ✓        │ ✓                      │
├──────────────────────────────────┼──────────┼────────────────────────┤
│ Version in folder & archive name │ ✓        │ ✓                      │
├──────────────────────────────────┼──────────┼────────────────────────┤
│ Arch suffix                      │ uname -m │ Is64BitOperatingSystem │
├──────────────────────────────────┼──────────┼────────────────────────┤
│ Archive format                   │ .tar.gz  │ .zip                   │
└──────────────────────────────────┴──────────┴────────────────────────┘

## Prerequisites

| Requirement | Minimum version |
|---|---|
| Python | 3.9+ |
| pip | included with Python |
| venv | included with Python |
| Git | any (optional — used for version tagging) |

---

## Linux / Unix

### Build

```bash
bash build.sh
```

### Output

```
dist/
├── claude-company/               # unversioned (no Git tag on commit)
│   ├── claude-company            # single executable
│   └── data/
│       ├── employees.json
│       ├── projects.json
│       └── staffing.json
└── claude-company-linux-x86_64.tar.gz
```

When the current Git commit carries a tag (e.g. `v1.2.0`) the version is
included in the folder and archive names:

```
dist/
├── claude-company-1.2.0/
│   ├── claude-company
│   └── data/
└── claude-company-1.2.0-linux-x86_64.tar.gz
```

### Clean

```bash
bash build.sh --clean
```

Removes `build/`, `dist/`, and `claude-company.spec`.

### Run

```bash
export CHALLENGE_WORD=your-secret
dist/claude-company/claude-company
# Open http://localhost:8080
```

---

## Windows

### Requirements

- Python 3.9+ installed from [python.org](https://www.python.org/downloads/)
  with **Add Python to PATH** checked during setup.
- PowerShell 5.1 or later (included with Windows 10/11).

### Allow PowerShell scripts (once)

Open PowerShell as your normal user and run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### Build

```powershell
.\build.ps1
```

### Output

```
dist\
├── claude-company\               # unversioned (no Git tag on commit)
│   ├── claude-company.exe        # single executable
│   └── data\
│       ├── employees.json
│       ├── projects.json
│       └── staffing.json
└── claude-company-windows-x86_64.zip
```

When the current Git commit carries a tag (e.g. `v1.2.0`):

```
dist\
├── claude-company-1.2.0\
│   ├── claude-company.exe
│   └── data\
└── claude-company-1.2.0-windows-x86_64.zip
```

### Clean

```powershell
.\build.ps1 -Clean
```

Removes `build\`, `dist\`, and `claude-company.spec`.

### Run

```powershell
$env:CHALLENGE_WORD = "your-secret"
dist\claude-company\claude-company.exe
# Open http://localhost:8080
```

---

## Versioned releases

Tag the commit before building to embed the version in all output names:

```bash
git tag v1.2.0
bash build.sh        # Linux
.\build.ps1          # Windows
```

The leading `v` is stripped automatically — `v1.2.0` becomes `1.2.0` in
folder and archive names.
