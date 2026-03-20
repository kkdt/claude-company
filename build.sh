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

# ── Git version / tag detection ───────────────────────────────────────────────
GIT_TAG=""
if command -v git >/dev/null 2>&1 && git -C "${SCRIPT_DIR}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    GIT_TAG="$(git -C "${SCRIPT_DIR}" tag --points-at HEAD 2>/dev/null | head -n1)"
fi

if [[ -n "${GIT_TAG}" ]]; then
    VERSION="${GIT_TAG#v}"
    info "Git tag detected: ${VERSION}"
else
    VERSION=""
    info "No Git tag on current commit — building without version suffix."
fi

# Folder and archive names include version when a tag is present
# e.g.  claude-company-1.2.0  /  claude-company-1.2.0-linux-x86_64.tar.gz
if [[ -n "${VERSION}" ]]; then
    PACKAGE_NAME="claude-company-${VERSION}"
else
    PACKAGE_NAME="claude-company"
fi

PACKAGE_DIR="${SCRIPT_DIR}/dist/${PACKAGE_NAME}"

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
rm -rf "${SCRIPT_DIR}/build" "${SCRIPT_DIR}/dist/${PACKAGE_NAME}"
success "Clean."

# ── PyInstaller ───────────────────────────────────────────────────────────────
info "Running PyInstaller..."
pyinstaller \
    --onefile \
    --strip \
    --name claude-company \
    --add-data "${SCRIPT_DIR}/templates:templates" \
    --distpath "${SCRIPT_DIR}/dist/${PACKAGE_NAME}" \
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

# ── Tar archive ───────────────────────────────────────────────────────────────
ARCH="$(uname -m)"
TARBALL="${SCRIPT_DIR}/dist/${PACKAGE_NAME}-linux-${ARCH}.tar.gz"

info "Creating tar archive..."
tar -czf "${TARBALL}" -C "${SCRIPT_DIR}/dist" "${PACKAGE_NAME}"
success "Archive created: ${TARBALL}  ($(du -sh "${TARBALL}" | cut -f1))"

# ── Summary ───────────────────────────────────────────────────────────────────
BINARY="${PACKAGE_DIR}/claude-company"
SIZE="$(du -sh "${BINARY}" | cut -f1)"

echo
echo -e "${GREEN}${BOLD}Build complete!${RESET}"
echo "──────────────────────────────────────────"
echo -e "  Package : ${CYAN}${PACKAGE_DIR}${RESET}"
echo -e "  Binary  : ${CYAN}${BINARY}${RESET}  (${SIZE})"
echo -e "  Archive : ${CYAN}${TARBALL}${RESET}"
echo
echo -e "${BOLD}Package contents:${RESET}"
find "${PACKAGE_DIR}" | sed "s|${SCRIPT_DIR}/dist/||" | sort | \
    awk 'NR==1{print "  "$0; next} {printf "  %-s\n", $0}'
echo
echo -e "${BOLD}To run:${RESET}"
echo -e "  export CHALLENGE_WORD=your-secret"
echo -e "  ${CYAN}${BINARY}${RESET}"
echo -e "  # Then open http://localhost:8080"
echo
