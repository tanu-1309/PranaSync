"""Start the PranaChain Insight interface.

    python scripts/serve.py                 ->  http://localhost:8000
    python scripts/serve.py --port 9000 --no-browser

Patients sign in with the accounts made by scripts/create_users.py; each sees only their own record,
analysed live from their workbook in data/raw (or data/synthetic when raw is empty).
"""
from __future__ import annotations

import argparse
import sys
import threading
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import uvicorn  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    if not a.no_browser:
        threading.Timer(1.5, lambda: webbrowser.open(f"http://{a.host}:{a.port}")).start()
    uvicorn.run("prana.api.server:app", host=a.host, port=a.port, log_level="warning")
