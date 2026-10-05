# Shortcuts for macOS/Linux (Windows: use the commands in docs/RUN_GUIDE.md)
export PYTHONPATH := src
DATA ?= data/synthetic

install:   ; pip install -r requirements.txt
synthetic: ; python -m prana.data.generate_synthetic --n 120 --out data/synthetic
profile:   ; python -m prana.data.profiling --data $(DATA)
run:       ; python scripts/run_pipeline.py --data $(DATA)
validate:  ; python scripts/validate.py --data data/synthetic
test:      ; python -m pytest -q
ui:        ; python scripts/serve.py
users:     ; python scripts/create_users.py
dashboard: ; streamlit run dashboard/app.py
demo: synthetic run validate dashboard
