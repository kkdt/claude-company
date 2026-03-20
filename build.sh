#!/usr/bin/env bash
# build.sh — Build a distributable package for Claude Company (Linux/Unix)
#
# Output:
#   dist/
#   └── claude-company/
#       ├── claude-company      (single executable)
#       └── data/
#           ├── employees.json
#           ├── projects.json
#           └── staffing.json

set -euo pipefail

# ── Helpers ───────────────────────────────────────────────────────────────────
CYAN='\033[0;36m'; GREEN='\033[0;32m'; RED='\033[0;31m'; BOLD='\033[1m'; RESET='\033[0m'
info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
die()     { echo -e "${RED}[ERROR]${RESET} $*" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="${SCRIPT_DIR}/dist/claude-company"

echo -e "${BOLD}"
echo "╔══════════════════════════════════════════╗"
echo "║      Claude Company  —  Build            ║"
echo "╚══════════════════════════════════════════╝"
echo -e "${RESET}"

# ── Virtual environment ───────────────────────────────────────────────────────
VENV_DIR="${SCRIPT_DIR}/venv"
if [[ ! -d "${VENV_DIR}" ]]; then
    info "No venv found — creating one..."
    python3 -m venv "${VENV_DIR}"
fi

source "${VENV_DIR}/bin/activate"

# ── Install / upgrade build dependencies ─────────────────────────────────────
info "Installing dependencies..."
if [[ -f "${SCRIPT_DIR}/pip.conf" ]]; then
    PIP_CONFIG_FILE="${SCRIPT_DIR}/pip.conf" pip install --quiet -r "${SCRIPT_DIR}/requirements.txt"
    PIP_CONFIG_FILE="${SCRIPT_DIR}/pip.conf" pip install --quiet pyinstaller
else
    pip install --quiet -r "${SCRIPT_DIR}/requirements.txt"
    pip install --quiet pyinstaller
fi
success "Dependencies ready."

# ── Clean previous build artifacts ───────────────────────────────────────────
info "Cleaning previous build artifacts..."
rm -rf "${SCRIPT_DIR}/build" "${PACKAGE_DIR}"
success "Clean."

# ── PyInstaller ───────────────────────────────────────────────────────────────
info "Running PyInstaller..."
pyinstaller \
    --onefile \
    --strip \
    --name claude-company \
    --add-data "${SCRIPT_DIR}/templates:templates" \
    --distpath "${SCRIPT_DIR}/dist/claude-company" \
    --workpath "${SCRIPT_DIR}/build" \
    --specpath "${SCRIPT_DIR}" \
    "${SCRIPT_DIR}/app.py"

success "Binary built: ${PACKAGE_DIR}/claude-company"

# ── Seed data directory ───────────────────────────────────────────────────────
info "Creating data directory..."
mkdir -p "${PACKAGE_DIR}/data"

for json_file in employees.json projects.json staffing.json; do
    target="${PACKAGE_DIR}/data/${json_file}"
    if [[ ! -f "${target}" ]]; then
        echo "[]" > "${target}"
    fi
done
success "data/ directory ready."

# ── Summary ───────────────────────────────────────────────────────────────────
BINARY="${PACKAGE_DIR}/claude-company"
SIZE="$(du -sh "${BINARY}" | cut -f1)"

echo
echo -e "${GREEN}${BOLD}Build complete!${RESET}"
echo "──────────────────────────────────────────"
echo -e "  Package : ${CYAN}${PACKAGE_DIR}${RESET}"
echo -e "  Binary  : ${CYAN}${BINARY}${RESET}  (${SIZE})"
echo
echo -e "${BOLD}Package contents:${RESET}"
find "${PACKAGE_DIR}" | sed 's|'"${SCRIPT_DIR}/dist/"'||' | sort | \
    awk 'NR==1{print "  "$0; next} {printf "  %-s\n", $0}'
echo
echo -e "${BOLD}To run:${RESET}"
echo -e "  export CHALLENGE_WORD=your-secret"
echo -e "  ${CYAN}${BINARY}${RESET}"
echo -e "  # Then open http://localhost:8080"
echo
echo -e "${BOLD}To distribute:${RESET}"
echo -e "  tar -czf claude-company-linux-x86_64.tar.gz -C ${SCRIPT_DIR}/dist claude-company"
echo
