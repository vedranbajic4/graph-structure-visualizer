#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
# setup.sh — Graph Structure Visualizer — Ubuntu/Linux Setup
# ═══════════════════════════════════════════════════════════
#
# Creates a virtual environment, installs all third-party
# dependencies, and installs every project component
# (API, Core/Platform, all Data Source plugins, both
# Visualizer plugins) in development mode.
#
# Usage:
#   chmod +x setup.sh
#   ./setup.sh
#
# After setup completes, use  ./run.sh  to start the server.
# ═══════════════════════════════════════════════════════════

set -e  # Exit immediately on error

# ── Colors for output ────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

info()    { echo -e "${GREEN}[INFO]${NC}  $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; }

# ── Resolve project root (directory containing this script) ──
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
VENV_DIR="$PROJECT_ROOT/venv"

info "Project root: $PROJECT_ROOT"

# ── 1. Check Python is installed ────────────────────────────
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    error "Python is not installed. Please install Python 3.8+ first."
    error "  Ubuntu/Debian:  sudo apt install python3 python3-venv python3-pip"
    exit 1
fi

PY_VERSION=$($PYTHON --version 2>&1)
info "Using $PY_VERSION"

# ── 2. Ensure python3-venv is available ─────────────────────
if ! $PYTHON -m venv --help &>/dev/null; then
    warn "python3-venv is not installed. Attempting to install..."
    sudo apt update && sudo apt install -y python3-venv
fi

# ── 3. Create virtual environment ──────────────────────────
if [ -d "$VENV_DIR" ]; then
    warn "Virtual environment already exists at $VENV_DIR"
    read -p "  Recreate it? [y/N]: " RECREATE
    if [[ "$RECREATE" =~ ^[Yy]$ ]]; then
        info "Removing old virtual environment..."
        rm -rf "$VENV_DIR"
        info "Creating new virtual environment..."
        $PYTHON -m venv "$VENV_DIR"
    fi
else
    info "Creating virtual environment at $VENV_DIR ..."
    $PYTHON -m venv "$VENV_DIR"
fi

# ── 4. Activate virtual environment ────────────────────────
info "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# ── 5. Upgrade pip & setuptools ────────────────────────────
info "Upgrading pip and setuptools..."
pip install --upgrade pip setuptools wheel

# ── 6. Install third-party dependencies ────────────────────
info "Installing third-party dependencies from requirements.txt ..."
pip install -r "$PROJECT_ROOT/requirements.txt"

# ── 7. Install project components (development mode) ───────
# Order matters: API first, then Core, then plugins.

info "Installing API library..."
pip install -e "$PROJECT_ROOT/api"

info "Installing Core platform..."
pip install -e "$PROJECT_ROOT/core"

info "Installing JSON Data Source plugin..."
pip install -e "$PROJECT_ROOT/data_source_plugin_json"

info "Installing XML Data Source plugin..."
pip install -e "$PROJECT_ROOT/data_source_plugin_xml"

info "Installing RDF Turtle Data Source plugin..."
pip install -e "$PROJECT_ROOT/data_source_plugin_rdf"

info "Installing Simple Visualizer plugin..."
pip install -e "$PROJECT_ROOT/simple_visualizer"

info "Installing Block Visualizer plugin..."
pip install -e "$PROJECT_ROOT/block_visualizer"

# ── 8. Run Django migrations ───────────────────────────────
info "Running Django migrations..."
cd "$PROJECT_ROOT/graph_django_app"
python manage.py migrate --run-syncdb 2>/dev/null || true
cd "$PROJECT_ROOT"

# ── 9. Verify installation ────────────────────────────────
info ""
info "═══════════════════════════════════════════════════"
info "  Setup complete!"
info "═══════════════════════════════════════════════════"
info ""
info "Installed packages:"
pip list --format=columns | grep -iE "graph-visualizer|data-source|simple-visualizer|block-visualizer"
info ""
info "To start the application, run:"
info "  ./run.sh django     (Django server on port 8000)"
info "  ./run.sh flask      (Flask server on port 5001)"
info ""
info "To run tests:"
info "  source venv/bin/activate"
info "  pytest tests/ -v"
info ""
