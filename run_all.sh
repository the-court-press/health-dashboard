#!/usr/bin/env bash
# Rebuild index.html, dashboard.html and chronographs-health.html from src/ + data.json. Run build.py first if you have a new WHOOP pull.
set -euo pipefail
cd "$(dirname "$0")"
python3 src/assemble.py
python3 src/assemble_chrono.py
python3 src/assemble_index.py
python3 build_dashboard.py   # inlines data.json into dashboard.html, then builds chronographs-health.html
