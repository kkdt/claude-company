#Requires -Version 5.1
<#
.SYNOPSIS
    Claude Company — Windows Installer
.DESCRIPTION
    Installs the Claude Company web application, sets up a Python virtual
    environment, and creates a launcher batch file.
.EXAMPLE
    .\install.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ── Helpers ───────────────────────────────────────────────────────────────────
function Write-Header {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║      Claude Company  —  Installer        ║" -ForegroundColor Cyan
    Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Info    { param($Msg) Write-Host "[INFO]  $Msg" -ForegroundColor Cyan }
function Write-Ok      { param($Msg) Write-Host "[OK]    $Msg" -ForegroundColor Green }
function Write-Warn    { param($Msg) Write-Host "[WARN]  $Msg" -ForegroundColor Yellow }
function Write-Err     { param($Msg) Write-Host "[ERROR] $Msg" -ForegroundColor Red }
function Abort         { param($Msg) Write-Err $Msg; exit 1 }

function Prompt-WithDefault {
    param(
        [string]$Prompt,
        [string]$Default
    )
    $display = "${Prompt} [${Default}]: "
    $value = Read-Host $display
    if ([string]::IsNullOrWhiteSpace($value)) { return $Default }
    return $value.Trim()
}

function Prompt-Confirm {
    param([string]$Prompt)
    $answer = Read-Host "$Prompt [y/N]"
    return ($answer -match '^[Yy](es)?$')
}

# ── Banner ────────────────────────────────────────────────────────────────────
Write-Header

# ── Source directory ──────────────────────────────────────────────────────────
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# ── Gather paths ──────────────────────────────────────────────────────────────
Write-Host "Installation Paths" -ForegroundColor White
Write-Host "──────────────────────────────────────────"

$DefaultInstall = Join-Path $env:USERPROFILE "claude-company"
$DefaultData    = Join-Path $env:USERPROFILE "claude-company\data"

$InstallDir = Prompt-WithDefault "Installation directory" $DefaultInstall
$DataDir    = Prompt-WithDefault "Data directory"         $DefaultData

Write-Host ""
Write-Host "Summary" -ForegroundColor White
Write-Host "──────────────────────────────────────────"
Write-Host "  Install directory : " -NoNewline; Write-Host $InstallDir -ForegroundColor Cyan
Write-Host "  Data directory    : " -NoNewline; Write-Host $DataDir    -ForegroundColor Cyan
Write-Host ""

if (-not (Prompt-Confirm "Proceed with installation?")) {
    Write-Host "Aborted."
    exit 0
}
Write-Host ""

# ── Pre-flight: Python ────────────────────────────────────────────────────────
Write-Info "Checking prerequisites..."

$PythonCmd = $null
foreach ($candidate in @('python', 'python3', 'py')) {
    try {
        $ver = & $candidate --version 2>&1
        if ($ver -match 'Python (\d+)\.(\d+)') {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 9)) {
                $PythonCmd = $candidate
                Write-Ok "Python $major.$minor found ($candidate)."
                break
            }
        }
    } catch { }
}

if (-not $PythonCmd) {
    Abort "Python 3.9+ is required but was not found. Download it from https://www.python.org/downloads/"
}

# Verify pip and venv
try { & $PythonCmd -m pip --version | Out-Null } catch { Abort "pip is not available. Reinstall Python and ensure 'pip' is included." }
try { & $PythonCmd -m venv --help   | Out-Null } catch { Abort "venv module is not available. Reinstall Python and ensure 'venv' is included." }
Write-Ok "pip and venv are available."

# ── Create directories ────────────────────────────────────────────────────────
Write-Info "Creating directories..."
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path $DataDir    | Out-Null
Write-Ok "Directories created."

# ── Copy application files ────────────────────────────────────────────────────
Write-Info "Copying application files..."

Copy-Item (Join-Path $ScriptDir "app.py")           (Join-Path $InstallDir "app.py")          -Force
Copy-Item (Join-Path $ScriptDir "requirements.txt") (Join-Path $InstallDir "requirements.txt") -Force
Copy-Item (Join-Path $ScriptDir "templates")        (Join-Path $InstallDir "templates")        -Recurse -Force

foreach ($csv in @('employees.csv', 'projects.csv')) {
    $src = Join-Path $ScriptDir $csv
    if (Test-Path $src) {
        Copy-Item $src (Join-Path $InstallDir $csv) -Force
    }
}

if (Test-Path (Join-Path $ScriptDir "pip.conf")) {
    Copy-Item (Join-Path $ScriptDir "pip.conf") (Join-Path $InstallDir "pip.conf") -Force
}

Write-Ok "Application files copied."

# ── Link / mirror data directory ──────────────────────────────────────────────
# app.py resolves data files relative to its own location.
# If the user chose a different data path we create a directory junction
# (Windows equivalent of a symlink for directories) at $InstallDir\data -> $DataDir.
$InstallDataLink = Join-Path $InstallDir "data"

if ($DataDir -ne $InstallDataLink) {
    Write-Info "Creating directory junction: $InstallDataLink -> $DataDir"

    if (Test-Path $InstallDataLink) {
        $item = Get-Item $InstallDataLink -Force
        if ($item.LinkType -eq 'Junction') {
            $item.Delete()
        } elseif ((Get-ChildItem $InstallDataLink -Force | Measure-Object).Count -eq 0) {
            Remove-Item $InstallDataLink -Force
        } else {
            Abort "A non-empty directory already exists at $InstallDataLink. Remove it manually and re-run."
        }
    }

    # cmd /c mklink /J is the reliable cross-version way to create junctions
    $result = cmd /c "mklink /J `"$InstallDataLink`" `"$DataDir`"" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Abort "Failed to create directory junction: $result"
    }
    Write-Ok "Directory junction created."
} else {
    New-Item -ItemType Directory -Force -Path $InstallDataLink | Out-Null
    Write-Ok "Data directory is co-located with install directory."
}

# ── Seed empty JSON data files ────────────────────────────────────────────────
Write-Info "Initialising data files..."
foreach ($json in @('employees.json', 'projects.json', 'staffing.json')) {
    $target = Join-Path $DataDir $json
    if (-not (Test-Path $target)) {
        Set-Content -Path $target -Value "[]" -Encoding UTF8
        Write-Info "  Created empty $json"
    } else {
        Write-Info "  Skipped $json (already exists)"
    }
}
Write-Ok "Data files ready."

# ── Virtual environment & dependencies ────────────────────────────────────────
$VenvDir = Join-Path $InstallDir "venv"
Write-Info "Creating virtual environment at $VenvDir..."
& $PythonCmd -m venv $VenvDir
Write-Ok "Virtual environment created."

Write-Info "Installing Python dependencies..."
$PipExe = Join-Path $VenvDir "Scripts\pip.exe"

$pipConf = Join-Path $InstallDir "pip.conf"
if (Test-Path $pipConf) {
    $env:PIP_CONFIG_FILE = $pipConf
}

& $PipExe install --quiet -r (Join-Path $InstallDir "requirements.txt")
if ($env:PIP_CONFIG_FILE) { Remove-Item Env:\PIP_CONFIG_FILE -ErrorAction SilentlyContinue }

Write-Ok "Dependencies installed."

# ── Write launcher batch file ─────────────────────────────────────────────────
$LauncherBat = Join-Path $InstallDir "claude-company.bat"
Write-Info "Writing launcher batch file..."

$batContent = @"
@echo off
REM claude-company.bat — start the Claude Company web application
setlocal

set "SCRIPT_DIR=%~dp0"
set "VENV_PYTHON=%SCRIPT_DIR%venv\Scripts\python.exe"

if "%CHALLENGE_WORD%"=="" (
    echo [WARN] CHALLENGE_WORD is not set. The login screen will accept any input.
    echo        Set it before starting: set CHALLENGE_WORD=your-secret
)

"%VENV_PYTHON%" "%SCRIPT_DIR%app.py" %*
endlocal
"@

Set-Content -Path $LauncherBat -Value $batContent -Encoding ASCII
Write-Ok "Launcher batch file written."

# ── Write launcher PowerShell script ─────────────────────────────────────────
$LauncherPs1 = Join-Path $InstallDir "claude-company.ps1"

$ps1Content = @"
# claude-company.ps1 — start the Claude Company web application
`$ScriptDir  = Split-Path -Parent `$MyInvocation.MyCommand.Path
`$VenvPython = Join-Path `$ScriptDir "venv\Scripts\python.exe"

if (-not `$env:CHALLENGE_WORD) {
    Write-Warning "CHALLENGE_WORD is not set. The login screen will accept any input."
    Write-Warning "Set it before starting: `$env:CHALLENGE_WORD = 'your-secret'"
}

& `$VenvPython (Join-Path `$ScriptDir "app.py") @args
"@

Set-Content -Path $LauncherPs1 -Value $ps1Content -Encoding UTF8
Write-Ok "Launcher PowerShell script written."

# ── Optional: Windows Start Menu shortcut ─────────────────────────────────────
$startMenuAvailable = Test-Path "$env:APPDATA\Microsoft\Windows\Start Menu\Programs"
if ($startMenuAvailable -and (Prompt-Confirm "Create Start Menu shortcut?")) {
    $shortcutPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Claude Company.lnk"
    $shell    = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath       = "cmd.exe"
    $shortcut.Arguments        = "/k `"$LauncherBat`""
    $shortcut.WorkingDirectory = $InstallDir
    $shortcut.Description      = "Claude Company Web Application"
    $shortcut.Save()
    Write-Ok "Start Menu shortcut created."
}

# ── Done ──────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Installation complete!" -ForegroundColor Green
Write-Host "──────────────────────────────────────────"
Write-Host "  Install directory : " -NoNewline; Write-Host $InstallDir  -ForegroundColor Cyan
Write-Host "  Data directory    : " -NoNewline; Write-Host $DataDir     -ForegroundColor Cyan
Write-Host "  Launcher (bat)    : " -NoNewline; Write-Host $LauncherBat -ForegroundColor Cyan
Write-Host ""
Write-Host "To start the application:"
Write-Host "  1. Open a Command Prompt or PowerShell window"
Write-Host "  2. Set your challenge word:"
Write-Host "       set CHALLENGE_WORD=your-secret        (cmd)" -ForegroundColor Cyan
Write-Host "       `$env:CHALLENGE_WORD = 'your-secret'   (PowerShell)" -ForegroundColor Cyan
Write-Host "  3. Run the launcher:"
Write-Host "       $LauncherBat" -ForegroundColor Cyan
Write-Host ""
Write-Host "Then open http://localhost:8080 in your browser." -ForegroundColor White
Write-Host ""
