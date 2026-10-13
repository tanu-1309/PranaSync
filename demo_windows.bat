@echo off
REM One-command demo for Windows: double-click this file, or run  demo_windows.bat  in Command Prompt.
REM First run: creates .venv and installs packages (~2-4 min). Later runs: ~1 min, then opens the dashboard.
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (set PY=py -3) else (set PY=python)

if not exist .venv (
  echo == creating virtual environment
  %PY% -m venv .venv || goto :error
)
call .venv\Scripts\activate.bat || goto :error

echo == installing packages (skipped quickly if already installed)
pip install -q -r requirements.txt || goto :error

set PYTHONPATH=src
if not exist data\synthetic\ground_truth.json (
  echo == generating 120 test workbooks
  python -m prana.data.generate_synthetic --n 120 --out data/synthetic || goto :error
)
echo == analysing all workbooks
python scripts\run_pipeline.py --data data/synthetic || goto :error
echo == validating against planted ground truth
python scripts\validate.py --data data/synthetic >nul || goto :error
echo    report: results\validation_report.md
echo == starting dashboard on http://localhost:8501  (Ctrl+C to stop)
start "" cmd /c "timeout /t 6 >nul & start http://localhost:8501"
streamlit run dashboard\app.py
goto :eof

:error
echo.
echo Something failed above. See docs\RUN_GUIDE.md, section "If something goes wrong".
pause
