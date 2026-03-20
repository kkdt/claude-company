#Requires -Version 5.1
<#
.SYNOPSIS
    Claude Company — Windows Build Script
.DESCRIPTION
    Builds a single-file Windows executable using PyInstaller, assembles a
    distributable package folder, and creates a .zip archive.
.PARAMETER Clean
    Remove all build artifacts (build\, dist\, claude-company.spec) and exit.
.EXAMPLE
    .\build.ps1
    .\build.ps1 -Clean
#>

param(
    [switch]$Clean
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ── Helpers ───────────────────────────────────────────────────────────────────
function Write-Info    { param($Msg) Write-Host "[INFO]  $Msg" -ForegroundColor Cyan }
function Write-Ok      { param($Msg) Write-Host "[OK]    $Msg" -ForegroundColor Green }
function Write-Err     { param($Msg) Write-Host "[ERROR] $Msg" -ForegroundColor Red }
function Abort         { param($Msg) Write-Err $Msg; exit 1 }

function Format-Size {
    param([string]$Path)
    $bytes = (Get-Item $Path).Length
    if     ($bytes -ge 1MB) { return "{0:N1} MB" -f ($bytes / 1MB) }
    elseif ($bytes -ge 1KB) { return "{0:N1} KB" -f ($bytes / 1KB) }
    else                    { return "$bytes B" }
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# ── --Clean ───────────────────────────────────────────────────────────────────
if ($Clean) {
    Write-Info "Cleaning build artifacts..."
    foreach ($target in @('build', 'dist', 'claude-company.spec')) {
        $full = Join-Path $ScriptDir $target
        if (Test-Path $full) {
            Remove-Item $full -Recurse -Force
            Write-Info "  Removed $target"
        }
    }
    Write-Ok "Cleaned: build\  dist\  claude-company.spec"
    exit 0
}

# ── Banner ────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "╔══════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║      Claude Company  —  Build            ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── Git version / tag detection ───────────────────────────────────────────────
$Version = ""
try {
    $null = & git -C $ScriptDir rev-parse --is-inside-work-tree 2>&1
    if ($LASTEXITCODE -eq 0) {
        $gitTag = & git -C $ScriptDir tag --points-at HEAD 2>$null |
                  Where-Object { $_ -ne "" } |
                  Select-Object -First 1
        if ($gitTag) {
            $Version = $gitTag -replace '^v', ''
            Write-Info "Git tag detected: $Version"
        }
    }
} catch { }

if (-not $Version) {
    Write-Info "No Git tag on current commit — building without version suffix."
}

# Package / archive names
$PackageName = if ($Version) { "claude-company-$Version" } else { "claude-company" }
$PackageDir  = Join-Path $ScriptDir "dist\$PackageName"

# ── Pre-flight: Python ────────────────────────────────────────────────────────
Write-Info "Checking prerequisites..."

$PythonCmd = $null
foreach ($candidate in @('python', 'python3', 'py')) {
    try {
        $ver = & $candidate --version 2>&1
        if ($ver -match 'Python (\d+)\.(\d+)') {
            $major = [int]$Matches[1]; $minor = [int]$Matches[2]
            if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 9)) {
                $PythonCmd = $candidate
                Write-Ok "Python $major.$minor found ($candidate)."
                break
            }
        }
    } catch { }
}
if (-not $PythonCmd) { Abort "Python 3.9+ is required but was not found." }

# ── Virtual environment ───────────────────────────────────────────────────────
$VenvDir = Join-Path $ScriptDir "venv"
if (-not (Test-Path $VenvDir)) {
    Write-Info "No venv found — creating one..."
    & $PythonCmd -m venv $VenvDir
}

$PipExe        = Join-Path $VenvDir "Scripts\pip.exe"
$PyInstallerExe = Join-Path $VenvDir "Scripts\pyinstaller.exe"

# ── Install dependencies ──────────────────────────────────────────────────────
Write-Info "Installing dependencies..."
$pipConf = Join-Path $ScriptDir "pip.conf"
if (Test-Path $pipConf) { $env:PIP_CONFIG_FILE = $pipConf }

& $PipExe install --quiet -r (Join-Path $ScriptDir "requirements.txt")
& $PipExe install --quiet pyinstaller

if ($env:PIP_CONFIG_FILE) { Remove-Item Env:\PIP_CONFIG_FILE -ErrorAction SilentlyContinue }
Write-Ok "Dependencies ready."

# ── Clean previous package dir ────────────────────────────────────────────────
Write-Info "Cleaning previous build artifacts..."
foreach ($target in @((Join-Path $ScriptDir "build"), $PackageDir)) {
    if (Test-Path $target) { Remove-Item $target -Recurse -Force }
}
Write-Ok "Clean."

# ── PyInstaller ───────────────────────────────────────────────────────────────
Write-Info "Running PyInstaller..."
& $PyInstallerExe `
    --onefile `
    --name claude-company `
    --add-data "$ScriptDir\templates;templates" `
    --distpath $PackageDir `
    --workpath "$ScriptDir\build" `
    --specpath $ScriptDir `
    "$ScriptDir\app.py"

if ($LASTEXITCODE -ne 0) { Abort "PyInstaller failed." }
Write-Ok "Binary built: $PackageDir\claude-company.exe"

# ── Seed data directory ───────────────────────────────────────────────────────
Write-Info "Creating data directory..."
$DataDir = Join-Path $PackageDir "data"
New-Item -ItemType Directory -Force -Path $DataDir | Out-Null

foreach ($json in @('employees.json', 'projects.json', 'staffing.json')) {
    $target = Join-Path $DataDir $json
    if (-not (Test-Path $target)) {
        Set-Content -Path $target -Value "[]" -Encoding UTF8
        Write-Info "  Created empty $json"
    } else {
        Write-Info "  Skipped $json (already exists)"
    }
}
Write-Ok "data\ directory ready."

# ── Zip archive ───────────────────────────────────────────────────────────────
$Arch    = if ([Environment]::Is64BitOperatingSystem) { 'x86_64' } else { 'x86' }
$ZipPath = Join-Path $ScriptDir "dist\$PackageName-windows-$Arch.zip"

Write-Info "Creating zip archive..."
Compress-Archive -Path $PackageDir -DestinationPath $ZipPath -Force
Write-Ok "Archive created: $ZipPath  ($(Format-Size $ZipPath))"

# ── Summary ───────────────────────────────────────────────────────────────────
$Binary   = Join-Path $PackageDir "claude-company.exe"
$BinSize  = Format-Size $Binary

Write-Host ""
Write-Host "Build complete!" -ForegroundColor Green
Write-Host "──────────────────────────────────────────"
Write-Host "  Package : " -NoNewline; Write-Host $PackageDir -ForegroundColor Cyan
Write-Host "  Binary  : " -NoNewline; Write-Host "$Binary  ($BinSize)" -ForegroundColor Cyan
Write-Host "  Archive : " -NoNewline; Write-Host $ZipPath -ForegroundColor Cyan
Write-Host ""
Write-Host "Package contents:"
Get-ChildItem $PackageDir -Recurse | ForEach-Object {
    "  " + $_.FullName.Replace($PackageDir, $PackageName)
}
Write-Host ""
Write-Host "To run:"
Write-Host "  `$env:CHALLENGE_WORD = 'your-secret'" -ForegroundColor Cyan
Write-Host "  $Binary" -ForegroundColor Cyan
Write-Host "  # Then open http://localhost:8080"
Write-Host ""
