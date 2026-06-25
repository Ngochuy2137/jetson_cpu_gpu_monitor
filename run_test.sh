#!/usr/bin/env bash
# Quick validation: GPU stress + 15s monitor at 10 Hz.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

python3 -m pip install -q -r requirements.txt

echo "=== Starting GPU stress in background ==="
python3 gpu_stress.py &
STRESS_PID=$!
cleanup() {
  kill "$STRESS_PID" 2>/dev/null || true
  wait "$STRESS_PID" 2>/dev/null || true
}
trap cleanup EXIT

sleep 2

echo "=== Running monitor for 15s at 10 Hz ==="
python3 monitor.py --hz 10 --threshold 80 --duration 15

echo "=== Done ==="
