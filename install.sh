#!/usr/bin/env bash
# Mirai Installer — installs Python deps, Node.js, builds the gateway, and onboards.
# Usage: curl -fsSL https://raw.githubusercontent.com/adityagoyal009/Mirai/main/install.sh | bash
#   or:  cd Mirai && bash install.sh

set -euo pipefail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
info()  { printf '\033[1;34m[MIRAI]\033[0m  %s\n' "$*"; }
warn()  { printf '\033[1;33m[WARN]\033[0m   %s\n' "$*"; }
error() { printf '\033[1;31m[ERROR]\033[0m  %s\n' "$*"; exit 1; }
ok()    { printf '\033[1;32m[OK]\033[0m     %s\n' "$*"; }

command_exists() { command -v "$1" &>/dev/null; }

MIN_NODE_MAJOR=22
MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=10

# ---------------------------------------------------------------------------
# 0. Locate Mirai root
# ---------------------------------------------------------------------------
locate_mirai_root() {
  # If install.sh lives inside the repo, use its directory
  if [[ -f "${BASH_SOURCE[0]}" ]]; then
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [[ -f "$script_dir/cortex/mirai_cortex.py" ]]; then
      MIRAI_ROOT="$script_dir"
      return
    fi
  fi

  # Check current directory
  if [[ -f "./cortex/mirai_cortex.py" ]]; then
    MIRAI_ROOT="$(pwd)"
    return
  fi

  # Clone from GitHub
  info "Mirai source not found — cloning from GitHub..."
  local target="${HOME}/Mirai"
  if [[ -d "$target/cortex" ]]; then
    info "Found existing clone at $target"
    MIRAI_ROOT="$target"
    return
  fi
  git clone https://github.com/adityagoyal009/Mirai.git "$target"
  MIRAI_ROOT="$target"
}

# ---------------------------------------------------------------------------
# 1. Python
# ---------------------------------------------------------------------------
check_python() {
  local py=""
  for candidate in python3 python; do
    if command_exists "$candidate"; then
      py="$candidate"
      break
    fi
  done

  if [[ -z "$py" ]]; then
    error "Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+ is required but not found. Install Python first."
  fi

  local version
  version=$($py -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
  local major minor
  major=$(echo "$version" | cut -d. -f1)
  minor=$(echo "$version" | cut -d. -f2)

  if (( major < MIN_PYTHON_MAJOR )) || { (( major == MIN_PYTHON_MAJOR )) && (( minor < MIN_PYTHON_MINOR )); }; then
    error "Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+ required (found $version)."
  fi

  PYTHON="$py"
  ok "Python $version"
}

install_pip() {
  if $PYTHON -m pip --version &>/dev/null; then
    ok "pip available"
    return
  fi

  info "pip not found — installing..."
  if command_exists apt-get; then
    sudo apt-get update -qq && sudo apt-get install -y -qq python3-pip python3-venv
  elif command_exists dnf; then
    sudo dnf install -y python3-pip
  elif command_exists brew; then
    # macOS: pip comes with Python from Homebrew
    true
  else
    curl -fsSL https://bootstrap.pypa.io/get-pip.py | $PYTHON
  fi
  ok "pip installed"
}

install_python_deps() {
  info "Installing Python dependencies..."

  local pip_args=()
  # Use --break-system-packages on externally managed Python (Debian/Ubuntu 24.04+)
  if $PYTHON -m pip install --help 2>&1 | grep -q 'break-system-packages'; then
    pip_args+=(--break-system-packages)
  fi

  $PYTHON -m pip install "${pip_args[@]}" --quiet \
    playwright \
    chromadb \
    requests \
    flask \
    flask-cors \
    openai \
    python-dotenv \
    mem0ai \
    crawl4ai \
    e2b-code-interpreter \
    crewai

  ok "Python dependencies installed"
}

install_playwright_browsers() {
  info "Installing Playwright Chromium..."
  $PYTHON -m playwright install --with-deps chromium 2>&1 | tail -3
  ok "Playwright Chromium installed"
}

# ---------------------------------------------------------------------------
# 2. Node.js
# ---------------------------------------------------------------------------
ensure_nvm_loaded() {
  if [[ -z "${NVM_DIR:-}" ]]; then
    export NVM_DIR="$HOME/.nvm"
  fi
  if [[ -s "$NVM_DIR/nvm.sh" ]]; then
    \. "$NVM_DIR/nvm.sh"
  fi
}

install_nodejs() {
  ensure_nvm_loaded

  if command_exists node; then
    local node_major
    node_major=$(node --version | sed 's/v//' | cut -d. -f1)
    if (( node_major >= MIN_NODE_MAJOR )); then
      ok "Node.js $(node --version)"
      return
    fi
    warn "Node.js $(node --version) is below v${MIN_NODE_MAJOR} — upgrading..."
  else
    info "Node.js not found — installing via nvm..."
  fi

  # Install nvm if not present
  if ! command_exists nvm; then
    curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.4/install.sh | bash
    ensure_nvm_loaded
  fi

  nvm install $MIN_NODE_MAJOR
  nvm use $MIN_NODE_MAJOR
  ok "Node.js $(node --version)"

  # Install pnpm (required by gateway build scripts)
  if ! command_exists pnpm; then
    info "Installing pnpm..."
    npm install -g pnpm
  fi
  ok "pnpm $(pnpm --version)"
}

# ---------------------------------------------------------------------------
# 3. System dependencies (Playwright libs)
# ---------------------------------------------------------------------------
install_system_deps() {
  # Only needed on Debian/Ubuntu — Playwright install --with-deps handles most of it
  if command_exists apt-get; then
    info "Installing system libraries..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq \
      git build-essential curl \
      libglib2.0-0 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
      libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
      libxfixes3 libxrandr2 libgbm1 2>/dev/null || true
    ok "System libraries installed"
  fi
}

# ---------------------------------------------------------------------------
# 4. Build the gateway
# ---------------------------------------------------------------------------
build_gateway() {
  info "Building Mirai gateway..."
  cd "$MIRAI_ROOT/gateway"

  ensure_nvm_loaded
  pnpm install 2>&1 | tail -3
  pnpm build 2>&1 | tail -3

  # Link globally so `mirai` command works from anywhere
  info "Linking 'mirai' command globally..."
  npm link 2>&1 | tail -3

  cd "$MIRAI_ROOT"
  ok "Gateway built — 'mirai' command available globally"
}

# ---------------------------------------------------------------------------
# 5. Verify
# ---------------------------------------------------------------------------
verify() {
  info "Verifying installation..."

  local errors=0

  # Python imports
  if $PYTHON -c "import requests, flask, openai, chromadb" 2>/dev/null; then
    ok "Python packages"
  else
    warn "Some Python packages failed to import"
    errors=$((errors + 1))
  fi

  # Gateway entry point
  if [[ -f "$MIRAI_ROOT/gateway/mirai.mjs" ]]; then
    ok "Gateway entry point"
  else
    warn "gateway/mirai.mjs not found"
    errors=$((errors + 1))
  fi

  # Gateway build output
  if [[ -f "$MIRAI_ROOT/gateway/dist/entry.js" ]] || [[ -f "$MIRAI_ROOT/gateway/dist/entry.mjs" ]]; then
    ok "Gateway build output"
  else
    warn "Gateway not built (dist/entry.js missing)"
    errors=$((errors + 1))
  fi

  # Node.js
  if command_exists node; then
    ok "Node.js $(node --version)"
  else
    warn "Node.js not found"
    errors=$((errors + 1))
  fi

  return $errors
}

# ---------------------------------------------------------------------------
# 6. Onboard (interactive)
# ---------------------------------------------------------------------------
run_onboard() {
  if [[ -f "$MIRAI_ROOT/gateway/dist/entry.js" ]] || [[ -f "$MIRAI_ROOT/gateway/dist/entry.mjs" ]]; then
    info "Running Mirai onboard..."
    if [ -t 0 ]; then
      node "$MIRAI_ROOT/gateway/mirai.mjs" onboard
    else
      info "Non-interactive shell — skipping onboard. Run manually:"
      echo "  cd $MIRAI_ROOT/gateway && node mirai.mjs onboard"
    fi
  fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
  echo ""
  echo "  ╔══════════════════════════════════════╗"
  echo "  ║        未来 Mirai Installer          ║"
  echo "  ╚══════════════════════════════════════╝"
  echo ""

  locate_mirai_root
  info "Mirai root: $MIRAI_ROOT"

  install_system_deps
  check_python
  install_pip
  install_nodejs
  install_python_deps
  install_playwright_browsers
  build_gateway

  echo ""
  echo "  ──────────────────────────────────────"

  if verify; then
    echo ""
    ok "Mirai installed successfully!"
    echo ""
    echo "  To start Mirai:"
    echo "    cd $MIRAI_ROOT"
    echo "    $PYTHON cortex/mirai_cortex.py"
    echo ""
  else
    echo ""
    warn "Installed with warnings — check output above."
    echo ""
  fi

  run_onboard
}

main "$@"
