#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python3 run.py
python3 run.py --cells defaults,duckdb
python3 redis_default.py
python3 prefix.py
python3 fetch_sources.py
python3 summarize.py
python3 make_report.py
python3 chart.py
