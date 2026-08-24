#!/usr/bin/env bash
# scripts/smoke_e2e.sh — Linux/macOS 入口，行为同 smoke_e2e.py
set -e
cd "$(dirname "$0")/.."
python3 scripts/smoke_e2e.py
