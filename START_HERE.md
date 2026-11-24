# PranaSync: start here

A patient health-record portal (University of Windsor x PranaChain, Team 8). Non-diagnostic: it describes a person's own data and never gives a percentage chance of disease.

## Run it (Windows PowerShell, Python 3.12)

```powershell
pip install -r requirements.txt
pip install rapidocr-onnxruntime pypdfium2          # optional: read photos and scans
copy .env.example .env                               # then fill in your own keys (the real .env is NOT in this zip)
$env:PYTHONPATH = "src"
python scripts/serve.py --port 8020                  # open http://127.0.0.1:8020 and press "Try the sample record"
```

Without a `.env` the portal still runs on SQLite with the language models off (the statistics, risk classes, uploads, review and clinical view all work; the AI-written text does not).
To sign in as a new person, press **Create account**, then **Upload documents** and use the files in `sample_documents/` (read `sample_documents/README.txt` first).

## What is in the zip

| Folder | What |
|---|---|
| `src/prana/` | the server, the risk model, the document reader, the document store |
| `web/` | the portal pages (plain JavaScript, no build step) |
| `models/`, `data/risk/` | the trained risk model and the 900 practice records it learned from |
| `data/knowledge/` | the approved WHO and MedlinePlus documents |
| `sample_documents/` | made-up reports to upload (PDF, Word, Excel, CSV, a photo, a scan) |
| `finetune/` | the fine-tuning dataset, scoring and training script (not run: needs a GPU) |
| `tests/`, `scripts/`, `.github/` | 348+ tests, helper scripts, a CI file |
| `docs/` | everything written down, including `PranaSync_Pitch_Deck.pptx`, `TEAM_TASKS.md`, `WHAT_IS_STILL_LACKING.md`, `DATA_DICTIONARY.md`, `ARCHITECTURE_UPLOAD.md`, `SITE_STRUCTURE.md`, `RUN_GUIDE.md` |

## Passwords

`data/credentials_ISSUE_ONCE.csv` is included: it lists each patient ID with a temporary password in plain text. Hand each one out once, then **delete the file**, and never share this zip beyond the team with it inside.

## Deliberately left out

`.env` (keys and passwords), `data/.docstore_key` and `data/.session_secret` (they are made on first run), the databases and uploaded files from testing, caches, and the old Week 9 zip.
Your document store key is created the first time someone uploads. Back up `data/.docstore_key` if you keep any documents: losing it makes them unreadable.

## Honest status

Built and tested, but **no clinician has reviewed the risk model, the wording or the documents**, the model learned from practice records (recorded diagnoses, not outcomes), nothing has been fine-tuned, and photo reading is tested only on clean pictures. See `docs/WHAT_IS_STILL_LACKING.md`.
