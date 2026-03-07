#!/bin/bash
# ============================================================
# Run the VIPL Email Agent locally against prod resources.
# ============================================================
# Usage:
#   ./scripts/run_local.sh          # Full agent (scheduler + health server)
#   ./scripts/run_local.sh --once   # Single poll cycle
#   ./scripts/run_local.sh --eod    # Trigger EOD report
#   ./scripts/run_local.sh --sla    # Run SLA check
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load .env if present
if [ -f "$PROJECT_DIR/.env" ]; then
    echo "Loading .env..."
    set -a
    source "$PROJECT_DIR/.env"
    set +a
else
    echo "ERROR: .env file not found. Copy .env.example to .env and fill in values."
    exit 1
fi

# Verify SA key exists (main.py falls back to ./service-account.json)
SA_KEY="service-account.json"
if [ ! -f "$PROJECT_DIR/$SA_KEY" ]; then
    echo "ERROR: Service account key not found at $PROJECT_DIR/$SA_KEY"
    echo "Place your service-account.json in the project root."
    exit 1
fi

cd "$PROJECT_DIR"
python main.py "$@"
