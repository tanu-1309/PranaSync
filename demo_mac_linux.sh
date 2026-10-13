#!/usr/bin/env bash
# One-command demo for macOS / Linux:   bash demo_mac_linux.sh
# First run: creates .venv and installs packages (~2-4 min). Later runs: ~1 min, then opens the dashboard.
set -e
cd "$(dirname "$0")"
PY=python3
command -v $PY >/dev/null 2>&1 || PY=python
if [ ! -d .venv ]; then
  echo "== creating virtual environment"
  $PY -m venv .venv
fi
source .venv/bin/activate
echo "== installing packages (skipped quickly if already installed)"
pip install -q -r requirements.txt
export PYTHONPATH=src
if [ ! -f data/synthetic/ground_truth.json ]; then
  echo "== generating 120 test workbooks"
  python -m prana.data.generate_synthetic --n 120 --out data/synthetic
fi
echo "== analysing all workbooks"
python scripts/run_pipeline.py --data data/synthetic
echo "== validating against planted ground truth"
python scripts/validate.py --data data/synthetic > /dev/null
echo "   report: results/validation_report.md"
echo "== starting dashboard on http://localhost:8501  (Ctrl+C to stop)"
( sleep 6; open http://localhost:8501 2>/dev/null || xdg-open http://localhost:8501 2>/dev/null ) &
streamlit run dashboard/app.py
