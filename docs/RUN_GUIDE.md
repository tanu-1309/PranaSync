# Run guide: install, run the models and the demo on your laptop

Works on Windows 10/11, macOS and Linux. Needs about 1 GB of disk space and an internet connection the first time
(to install packages). Nothing runs in the cloud and no API key is needed.

---

## 0. One-time setup (10 minutes)

### 0.1 Install Python 3.11, 3.12 or 3.13
* **Windows:** download from https://www.python.org/downloads/ → run the installer → **tick "Add python.exe to PATH"** → Install.
  Check in a new Command Prompt: `py --version` (or `python --version`) shows 3.11–3.13.
* **macOS:** download the macOS installer from python.org (or `brew install python@3.12`). Check: `python3 --version`.

### 0.2 Install Git
* Windows: https://git-scm.com/download/win (defaults are fine). macOS: run `git --version` once; it offers to install.

### 0.3 Get the code
```bash
git clone https://github.com/tanu-1309/PranaChain.git
cd PranaChain
```
(Before the code is merged into GitHub, unzip `PranaChain_checkpoint.zip` and `cd` into the folder instead.)

---

## 1. Fastest way: one command

| Windows | macOS / Linux |
|---|---|
| double-click **`demo_windows.bat`** (or run it in Command Prompt) | `bash demo_mac_linux.sh` |

It creates a private Python environment (`.venv`), installs the packages, generates 120 test workbooks, runs the
models on all of them, writes the validation report and opens the dashboard at **http://localhost:8501**.
First run 3–5 minutes, later runs about 1 minute. Stop the dashboard with **Ctrl + C**.

---

## 2. Step by step (to understand each stage, or if the one-command script fails)

Open a terminal **in the project folder** (Windows: Command Prompt or PowerShell; macOS: Terminal).

**2.1 Create and activate the environment** (activate again every time you open a new terminal)

| | Windows (Command Prompt) | Windows (PowerShell) | macOS / Linux |
|---|---|---|---|
| create | `py -3 -m venv .venv` | `py -3 -m venv .venv` | `python3 -m venv .venv` |
| activate | `.venv\Scripts\activate.bat` | `.venv\Scripts\Activate.ps1` | `source .venv/bin/activate` |

You should now see `(.venv)` at the start of the prompt.

**2.2 Install packages** — `pip install -r requirements.txt` (2–4 minutes)

**2.3 Tell Python where our code is** (every new terminal)

| Command Prompt | PowerShell | macOS / Linux |
|---|---|---|
| `set PYTHONPATH=src` | `$env:PYTHONPATH="src"` | `export PYTHONPATH=src` |

**2.4 Run the models**

| Step | Command | Takes | Output |
|---|---|---|---|
| a. make 120 test workbooks (real 11-sheet layout, planted patterns) | `python -m prana.data.generate_synthetic --n 120 --out data/synthetic` | ~20 s | `data/synthetic/*.xlsx`, `ground_truth.json` |
| b. check data quality | `python -m prana.data.profiling --data data/synthetic` | ~15 s | `results/data_profile.csv` |
| c. **run the full analysis** (clean → timeline → baseline → patterns → history link → evidence → explanation) | `python scripts/run_pipeline.py --data data/synthetic` | ~40 s | `results/summary.csv`, `results/insights/*.json`, `data/prana.db` |
| d. **validate** against the planted ground truth | `python scripts/validate.py --data data/synthetic` | ~60 s | `results/validation_report.md`, `results/metrics.json`, `results/figures/*.png` |
| e. automated tests | `python -m pytest -q` | ~10 s | `18 passed` |
| f. **dashboard** | `streamlit run dashboard/app.py` | ~5 s | open **http://localhost:8501** in your browser |

Step **c** must run before **f** for the "Only patients with a surfaced pattern" filter to work.
Open one patient directly: `http://localhost:8501/?patient=SYN0001`.

**2.5 Look at one patient's result without the dashboard** — open `results/insights/SYN0001.json`
(evidence pack + explanation for each health area).

---

## 3. Run on the real Prana Chain data

1. Open the shared Google Drive folder → right-click a folder (e.g. `PC0001_PC0100`) → **Download** → unzip.
2. Put the `.xlsx` files (sub-folders are fine) into **`data/raw/`** in the project. *Never commit this folder.*
3. Run:
   ```bash
   python -m prana.data.profiling --data data/raw --limit 20      # quick look at 20 files first
   python scripts/run_pipeline.py --data data/raw --limit 20
   streamlit run dashboard/app.py                                  # choose "Real dataset" in the sidebar
   ```
   Remove `--limit 20` to run everything (≈ 0.3 s per workbook, about 5 minutes for the 900 real files).
4. If a sheet or column is reported missing, the name differs in that file: fix it in `config/column_map.yaml` (no code change).

Real data has no labels, so `validate.py` only works on the generated data. For the real data use the checks in
`docs/VALIDATION.md` (last section).

---

## 4. If something goes wrong

| Problem | Fix |
|---|---|
| `python` / `py` is not recognized | Re-run the Python installer, tick "Add to PATH", open a **new** terminal. On macOS use `python3`. |
| PowerShell: "running scripts is disabled" when activating | Use Command Prompt instead, or run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `ModuleNotFoundError: No module named 'prana'` | You forgot step 2.3 (`PYTHONPATH`) in this terminal, or you are not in the project folder. |
| `ModuleNotFoundError: pandas` (or another package) | The environment is not active (`(.venv)` missing): activate it (2.1) and re-run `pip install -r requirements.txt`. |
| `pip install` fails on a package | `python -m pip install --upgrade pip`, then install again. Use Python 3.11–3.13 (not 3.14 beta). |
| Dashboard says "No workbooks found" | Run step 2.4a first, from the project folder. |
| Port 8501 already in use (the terminal prints another port, e.g. 8502) | open the URL the terminal prints, or stop the other dashboard first |
| Dashboard looks old after a code change | Press **R** in the browser, or stop (Ctrl+C) and start again. |
| `PermissionError` writing a file on Windows | Close the Excel file / CSV that is open in Excel, then re-run. |
| Very slow first load of a patient | Normal (~3–5 s, it analyses the workbook); later loads are cached. |

---

## 5. What each model / method does (for questions during the demo)

| Stage | Method | Where |
|---|---|---|
| Personal baseline | mean and SD of the first 60 days, per person, per signal | `analysis/baseline.py` |
| "Changed" test | shift ≥ clinical minimum **and** ≥ 0.8 baseline SD **and** Mann-Kendall trend p < 0.05 on weekly means **and** still present in the last 60 days | `analysis/baseline.py` |
| Start date | single change point on weekly means (ruptures Binseg) | `analysis/baseline.py` |
| Labs | mean of first two vs last two results + Theil-Sen slope sign | `analysis/baseline.py` |
| Pattern | ≥ 3 changed signals starting within 150 days, incl. ≥ 1 core signal | `analysis/patterns.py` |
| History link | keywords in history / notes / meds / family history, prior lab values over a flag level | `insight/context_linker.py` |
| Missing data | wanted items per area: absent, too old, or < 70 % of days | `insight/missing_data.py` |
| Explanation | template built only from the evidence pack + fixed disclaimer | `insight/explainer.py` |
| Settings for all three areas | one YAML file | `config/scenarios.yaml` |
