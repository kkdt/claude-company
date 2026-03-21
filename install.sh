#!/usr/bin/env bash
# install.sh — Claude Company installer for Linux/Unix

set -euo pipefail

# ── Colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; }
die()     { error "$*"; exit 1; }

# ── Banner ───────────────────────────────────────────────────────────────────
echo -e "${BOLD}"
echo "╔══════════════════════════════════════════╗"
echo "║        Claude Company  —  Installer      ║"
echo "╚══════════════════════════════════════════╝"
echo -e "${RESET}"

# ── Source directory (where this script lives) ───────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Prompt helpers ───────────────────────────────────────────────────────────
prompt_with_default() {
    local prompt="$1"
    local default="$2"
    local value
    echo -ne "${BOLD}${prompt}${RESET} [${default}]: " >&2
    read -r value
    echo "${value:-$default}"
}

confirm() {
    local prompt="$1"
    local answer
    echo -ne "${BOLD}${prompt}${RESET} [y/N]: "
    read -r answer
    [[ "${answer,,}" == "y" || "${answer,,}" == "yes" ]]
}

# ── Gather installation paths ────────────────────────────────────────────────
echo -e "${BOLD}Installation Paths${RESET}"
echo "──────────────────────────────────────────"
echo -e "Press ${BOLD}Enter${RESET} to accept each default, or type a custom path."
echo

INSTALL_DIR="$(prompt_with_default "Installation directory" "${HOME}/claude-company")"
DATA_DIR="$(prompt_with_default "Data directory" "${HOME}/claude-company/data")"

# Expand any ~ that the user may have typed
INSTALL_DIR="${INSTALL_DIR/#\~/$HOME}"
DATA_DIR="${DATA_DIR/#\~/$HOME}"

echo
echo -e "${BOLD}Security${RESET}"
echo "──────────────────────────────────────────"
echo -e "The challenge word is required to log in to the application."
echo
while true; do
    echo -ne "${BOLD}Challenge word${RESET}: " >&2
    read -rs CHALLENGE_WORD
    echo >&2
    if [[ -z "${CHALLENGE_WORD}" ]]; then
        echo -e "${YELLOW}Challenge word cannot be empty.${RESET}" >&2
        continue
    fi
    echo -ne "${BOLD}Confirm challenge word${RESET}: " >&2
    read -rs CHALLENGE_WORD_CONFIRM
    echo >&2
    if [[ "${CHALLENGE_WORD}" != "${CHALLENGE_WORD_CONFIRM}" ]]; then
        echo -e "${YELLOW}Challenge words do not match. Try again.${RESET}" >&2
        continue
    fi
    break
done

echo
echo -e "${BOLD}Summary${RESET}"
echo "──────────────────────────────────────────"
echo -e "  Install directory : ${CYAN}${INSTALL_DIR}${RESET}"
echo -e "  Data directory    : ${CYAN}${DATA_DIR}${RESET}"
echo -e "  Challenge word    : ${CYAN}(set) — saved to ${INSTALL_DIR}/.challenge_word${RESET}"
echo

confirm "Proceed with installation?" || { echo "Aborted."; exit 0; }
echo

# ── Pre-flight checks ────────────────────────────────────────────────────────
info "Checking prerequisites..."

command -v python3 >/dev/null 2>&1 || die "python3 is required but not found. Please install Python 3.9+."

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [[ "$PYTHON_MAJOR" -lt 3 ]] || { [[ "$PYTHON_MAJOR" -eq 3 ]] && [[ "$PYTHON_MINOR" -lt 9 ]]; }; then
    die "Python 3.9+ is required (found ${PYTHON_VERSION})."
fi
success "Python ${PYTHON_VERSION} found."

# Check venv availability (pip is bundled inside the venv via ensurepip)
python3 -m venv --help >/dev/null 2>&1 || die "venv module is not available. Install python3-venv."
success "venv is available."

# ── Create directories ───────────────────────────────────────────────────────
info "Creating directories..."
mkdir -p "${INSTALL_DIR}"
mkdir -p "${DATA_DIR}"
success "Directories created."

# ── Save challenge word ───────────────────────────────────────────────────────
CHALLENGE_WORD_FILE="${INSTALL_DIR}/.challenge_word"
info "Saving challenge word..."
echo "${CHALLENGE_WORD}" > "${CHALLENGE_WORD_FILE}"
chmod 600 "${CHALLENGE_WORD_FILE}"
success "Challenge word saved to ${CHALLENGE_WORD_FILE}."

# ── Copy application files ───────────────────────────────────────────────────
info "Copying application files..."

cp "${SCRIPT_DIR}/app.py"          "${INSTALL_DIR}/app.py"
cp "${SCRIPT_DIR}/requirements.txt" "${INSTALL_DIR}/requirements.txt"

# Copy templates and static directories
cp -r "${SCRIPT_DIR}/templates"    "${INSTALL_DIR}/templates"
cp -r "${SCRIPT_DIR}/static"       "${INSTALL_DIR}/static"

# Copy sample CSV files if present (useful for first run)
for csv_file in employees.csv projects.csv; do
    if [[ -f "${SCRIPT_DIR}/${csv_file}" ]]; then
        cp "${SCRIPT_DIR}/${csv_file}" "${INSTALL_DIR}/${csv_file}"
    fi
done

# Copy pip configuration if present
if [[ -f "${SCRIPT_DIR}/pip.conf" ]]; then
    cp "${SCRIPT_DIR}/pip.conf" "${INSTALL_DIR}/pip.conf"
fi

success "Application files copied."

# ── Link data directory ───────────────────────────────────────────────────────
# app.py resolves data paths relative to its own location (os.path.dirname(__file__)).
# We create a symlink at $INSTALL_DIR/data -> $DATA_DIR so a custom data path works
# transparently without modifying app.py.
INSTALL_DATA_LINK="${INSTALL_DIR}/data"

if [[ "${DATA_DIR}" != "${INSTALL_DATA_LINK}" ]]; then
    info "Linking ${INSTALL_DATA_LINK} -> ${DATA_DIR}..."
    # Remove an existing link or directory (only if empty)
    if [[ -L "${INSTALL_DATA_LINK}" ]]; then
        rm "${INSTALL_DATA_LINK}"
    elif [[ -d "${INSTALL_DATA_LINK}" ]]; then
        rmdir "${INSTALL_DATA_LINK}" 2>/dev/null \
            || die "Non-empty directory exists at ${INSTALL_DATA_LINK}. Please remove it manually."
    fi
    ln -s "${DATA_DIR}" "${INSTALL_DATA_LINK}"
    success "Data symlink created."
else
    mkdir -p "${INSTALL_DATA_LINK}"
    success "Data directory is co-located with install directory."
fi

# ── Seed empty JSON data files if they don't already exist ───────────────────
info "Initialising data files..."
for json_file in employees.json projects.json staffing.json; do
    target="${DATA_DIR}/${json_file}"
    if [[ ! -f "${target}" ]]; then
        echo "[]" > "${target}"
        info "  Created empty ${json_file}"
    else
        info "  Skipped ${json_file} (already exists)"
    fi
done
success "Data files ready."

# ── Virtual environment & dependencies ───────────────────────────────────────
VENV_DIR="${INSTALL_DIR}/venv"
info "Creating virtual environment at ${VENV_DIR}..."
python3 -m venv "${VENV_DIR}"
success "Virtual environment created."

info "Installing Python dependencies..."
PIP_CMD="${VENV_DIR}/bin/pip"

# Use local pip.conf if present (mirrors / index overrides)
if [[ -f "${INSTALL_DIR}/pip.conf" ]]; then
    PIP_CONFIG_FILE="${INSTALL_DIR}/pip.conf" "${PIP_CMD}" install --quiet -r "${INSTALL_DIR}/requirements.txt"
else
    "${PIP_CMD}" install --quiet -r "${INSTALL_DIR}/requirements.txt"
fi
success "Dependencies installed."

# ── Write launcher script ─────────────────────────────────────────────────────
LAUNCHER="${INSTALL_DIR}/claude-company.sh"
info "Writing launcher script..."

cat > "${LAUNCHER}" <<'LAUNCHER_EOF'
#!/usr/bin/env bash
# claude-company.sh — start the Claude Company web application

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="${SCRIPT_DIR}/venv/bin/python"

# Load challenge word from saved file, falling back to env var
CHALLENGE_WORD_FILE="${SCRIPT_DIR}/.challenge_word"
if [[ -f "${CHALLENGE_WORD_FILE}" ]]; then
    export CHALLENGE_WORD="$(cat "${CHALLENGE_WORD_FILE}")"
elif [[ -z "${CHALLENGE_WORD:-}" ]]; then
    echo "[WARN] CHALLENGE_WORD is not set. Only PUBLIC functionality will be available."
fi

exec "${VENV_PYTHON}" "${SCRIPT_DIR}/app.py" "$@"
LAUNCHER_EOF

chmod +x "${LAUNCHER}"
success "Launcher script written."

# ── Optional systemd user service ────────────────────────────────────────────
SYSTEMD_AVAILABLE=false
if command -v systemctl >/dev/null 2>&1 && [[ -d "${HOME}/.config/systemd/user" || -d /run/systemd/system ]]; then
    SYSTEMD_AVAILABLE=true
fi

if $SYSTEMD_AVAILABLE && confirm "Install systemd user service (auto-start on login)?"; then
    SERVICE_DIR="${HOME}/.config/systemd/user"
    mkdir -p "${SERVICE_DIR}"

    cat > "${SERVICE_DIR}/claude-company.service" <<SERVICE_EOF
[Unit]
Description=Claude Company Web Application
After=network.target

[Service]
Type=simple
WorkingDirectory=${INSTALL_DIR}
ExecStart=${LAUNCHER}
Restart=on-failure
RestartSec=5
Environment=CHALLENGE_WORD=

[Install]
WantedBy=default.target
SERVICE_EOF

    systemctl --user daemon-reload
    systemctl --user enable claude-company.service 2>/dev/null || true
    success "systemd user service installed (claude-company.service)."
    warn "Edit ${SERVICE_DIR}/claude-company.service to set CHALLENGE_WORD before starting."
    echo -e "  Start : ${CYAN}systemctl --user start claude-company${RESET}"
    echo -e "  Stop  : ${CYAN}systemctl --user stop  claude-company${RESET}"
    echo -e "  Logs  : ${CYAN}journalctl --user -u claude-company -f${RESET}"
fi

# ── Done ─────────────────────────────────────────────────────────────────────
echo
echo -e "${GREEN}${BOLD}Installation complete!${RESET}"
echo "──────────────────────────────────────────"
echo -e "  Install directory : ${CYAN}${INSTALL_DIR}${RESET}"
echo -e "  Data directory    : ${CYAN}${DATA_DIR}${RESET}"
echo -e "  Launcher          : ${CYAN}${LAUNCHER}${RESET}"
echo
echo -e "${BOLD}To start the application:${RESET}"
echo -e "  ${CYAN}${LAUNCHER}${RESET}"
warn "The challenge word is a local, plain-text, hidden file. Please note its location and the keep it safe."
echo
echo -e "Then open ${CYAN}http://localhost:8080${RESET} in your browser."
echo
