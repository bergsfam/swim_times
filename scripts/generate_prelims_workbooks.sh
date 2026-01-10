#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root_dir"

python3 scripts/generate_event_workbooks.py \
  --phase prelims \
  --output-dir excel_outputs/state_prelims
