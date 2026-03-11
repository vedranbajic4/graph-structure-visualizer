#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
# run.sh — Graph Structure Visualizer — Ubuntu/Linux Runner
# ═══════════════════════════════════════════════════════════
#
# Activates the virtual environment and starts either the
# Django or Flask development server.
#
# Usage:
#   ./run.sh              (defaults to Django)
#   ./run.sh django       (Django on port 8000)
#   ./run.sh flask        (Flask  on port 5001)
#   ./run.sh test         (run pytest test suite)
#   ./run.sh reinstall    (reinstall all components)
#
# ═══════════════════════════════════════════════════════════

set -e

# ── Colors ───────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

info()    { echo -e "${GREEN}[INFO]${NC}  $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; }
header()  { echo -e "${CYAN}$1${NC}"; }

# ── Resolve paths ────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
VENV_DIR="$PROJECT_ROOT/venv"

# ── Check venv exists ───────────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    error "Virtual environment not found at $VENV_DIR"
    error "Run  ./setup.sh  first to create the environment."
    exit 1
fi

# ── Activate venv ───────────────────────────────────────
source "$VENV_DIR/bin/activate"

# ── Parse argument ──────────────────────────────────────
MODE="${1:-django}"
MODE=$(echo "$MODE" | tr '[:upper:]' '[:lower:]')

case "$MODE" in

    # ────────────────────────────────────────────────────
    django)
        header ""
        header "═══════════════════════════════════════════"
        header "  Starting Django Development Server"
        header "  http://127.0.0.1:8000/"
        header "═══════════════════════════════════════════"
        header ""

        cd "$PROJECT_ROOT/graph_django_app"

        # Run migrations silently in case of first run
        python manage.py migrate --run-syncdb 2>/dev/null || true

        info "Server starting on http://127.0.0.1:8000/"
        info "Press Ctrl+C to stop."
        echo ""

        python manage.py runserver 0.0.0.0:8000
        ;;

    # ────────────────────────────────────────────────────
    flask)
        header ""
        header "═══════════════════════════════════════════"
        header "  Starting Flask Development Server"
        header "  http://127.0.0.1:5001/"
        header "═══════════════════════════════════════════"
        header ""

        cd "$PROJECT_ROOT/graph_flask_app"

        info "Server starting on http://127.0.0.1:5001/"
        info "Press Ctrl+C to stop."
        echo ""

        python app.py
        ;;

    # ────────────────────────────────────────────────────
    test|tests)
        header ""
        header "═══════════════════════════════════════════"
        header "  Running Test Suite"
        header "═══════════════════════════════════════════"
        header ""

        cd "$PROJECT_ROOT"
        pytest tests/ -v --tb=short
        ;;

    # ────────────────────────────────────────────────────
    reinstall)
        header ""
        header "═══════════════════════════════════════════"
        header "  Reinstalling All Components"
        header "═══════════════════════════════════════════"
        header ""

        info "Uninstalling old packages..."
        pip uninstall -y graph-visualizer-api graph-visualizer-core \
            data-source-plugin-json data-source-plugin-xml \
            data-source-plugin-rdf-turtle \
            simple-visualizer block-visualizer 2>/dev/null || true

        # Clean build artifacts
        info "Cleaning build artifacts..."
        find "$PROJECT_ROOT" -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
        find "$PROJECT_ROOT" -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
        find "$PROJECT_ROOT" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

        info "Reinstalling all components..."
        pip install -e "$PROJECT_ROOT/api"
        pip install -e "$PROJECT_ROOT/core"
        pip install -e "$PROJECT_ROOT/data_source_plugin_json"
        pip install -e "$PROJECT_ROOT/data_source_plugin_xml"
        pip install -e "$PROJECT_ROOT/data_source_plugin_rdf"
        pip install -e "$PROJECT_ROOT/simple_visualizer"
        pip install -e "$PROJECT_ROOT/block_visualizer"

        info ""
        info "Reinstallation complete!"
        info "Installed packages:"
        pip list --format=columns | grep -iE "graph-visualizer|data-source|simple-visualizer|block-visualizer"
        ;;

    # ────────────────────────────────────────────────────
    *)
        echo ""
        echo "Usage: ./run.sh [django|flask|test|reinstall]"
        echo ""
        echo "  django      Start Django development server (port 8000) [default]"
        echo "  flask       Start Flask development server  (port 5001)"
        echo "  test        Run the pytest test suite"
        echo "  reinstall   Uninstall & reinstall all project components"
        echo ""
        exit 1
        ;;
esac
