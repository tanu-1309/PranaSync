# Git guide for the team, with dates

Written Tue 24 Nov 2026. The repository is https://github.com/tanu-1309/PranaSync. Everyone commits **their own files from their own GitHub account**. Nobody has committed or pushed the new work yet.

The dates below are a **proposal**: one pull request a day, working days only, with the day after for review, then one merge sitting. If your week is different, run `python scripts/git_guide.py --start YYYY-MM-DD` and the guide is rewritten.

## The week at a glance

| Date | Who | What |
|---|---|---|
| Wed 25 Nov 2026 | Uday | Open pull request 1 `feature/data-foundation`; Sindhu reviews |
| Thu 26 Nov 2026 | Sindhu | Open pull request 2 `feature/risk-and-ai`; Sneha reviews |
| Fri 27 Nov 2026 | Uday | Open pull request 3 `feature/portal-api`; Tanusree reviews |
| Mon 30 Nov 2026 | Tanusree | Open pull request 4 `feature/portal-ui`; Uday reviews |
| Tue 01 Dec 2026 | Sneha | Open pull request 5 `docs/data-and-knowledge`; Tanusree reviews |
| Fri 27 Nov 2026 (end of day) | Uday + the reviewers | **Merge pull requests 1, 2 and 3 together**, in order, then everyone runs the sync routine |
| Wed 02 Dec 2026 | Uday, Tanusree | Merge pull requests 4 and 5 |
| Thu 03 Dec 2026 | everyone | Final sync, run the tests once, **Uday tags `round2-complete`** |

Pull requests 1 to 3 depend on each other (the API imports the risk and AI code, which import the database helpers), so the automatic checks can be red until pull request 3 is merged.

## Where the repository stands today

- Branch you are on in this folder: `feature/ai-wording`
- Paths with uncommitted changes: 174
- Latest commits (date | author | message):

```
2026-11-10 | Gavinnolla Tanusree Reddy | Restore missing project files so main passes CI
2026-11-09 | Snehachowdary56 | Merge pull request #10 from tanu-1309/feature/postgres-db
2026-11-09 | SnehaChowdary56 | Move database layer to PostgreSQL with COPY loading and JSONB packages
2026-10-21 | Gavinnolla Tanusree Reddy | Merge insight, analysis, validation-script and portal-tests-docs work into main
2026-10-27 | SINDHU PADMAJA | Merge pull request #9 from tanu-1309/feature/analysis
2026-10-27 | SINDHU PADMAJA | Merge pull request #8 from tanu-1309/feature/validation-script
2026-10-27 | SINDHU PADMAJA | Merge pull request #7 from tanu-1309/feature/portal-tests-docs
2026-10-27 | Uday Kumar Reddy | Merge pull request #6 from tanu-1309/feature/portal-api
2026-10-27 | Uday Kumar Reddy | Merge pull request #5 from tanu-1309/feature/data-pipeline
2026-10-27 | Uday Kumar Reddy | Merge pull request #4 from tanu-1309/docs/validation
2026-10-27 | Tanu Sree Reddy Gavinnolla | Merge pull request #3 from tanu-1309/docs/results-and-team
2026-10-27 | Tanu Sree Reddy Gavinnolla | Merge pull request #2 from tanu-1309/feature/dashboard-ci
```

## Everyone, once (setup)

```bash
git clone https://github.com/tanu-1309/PranaSync.git      # skip if you already have the folder
cd PranaSync
git config user.name "Your Name"                            # so the commit shows YOUR name
git config user.email "the-email-of-your-github-account"
git config pull.rebase true                                 # keeps history straight when you pull
```

## Everyone, every working morning (keeps your copy up to date)

| Date | Command | What it does |
|---|---|---|
| Wed 25 Nov 2026 | `git fetch --all --prune && git switch main && git pull --ff-only` | brings in everything merged since yesterday; stops if your main has stray changes |
| Thu 26 Nov 2026 | `git fetch --all --prune && git switch main && git pull --ff-only` | brings in everything merged since yesterday; stops if your main has stray changes |
| Fri 27 Nov 2026 | `git fetch --all --prune && git switch main && git pull --ff-only` | brings in everything merged since yesterday; stops if your main has stray changes |
| Mon 30 Nov 2026 | `git fetch --all --prune && git switch main && git pull --ff-only` | brings in everything merged since yesterday; stops if your main has stray changes |
| Tue 01 Dec 2026 | `git fetch --all --prune && git switch main && git pull --ff-only` | brings in everything merged since yesterday; stops if your main has stray changes |
| Wed 02 Dec 2026 | `git fetch --all --prune && git switch main && git pull --ff-only` | brings in everything merged since yesterday; stops if your main has stray changes |
| Thu 03 Dec 2026 | `git fetch --all --prune && git switch main && git pull --ff-only` | brings in everything merged since yesterday; stops if your main has stray changes |

Before you push anything, on your branch: `git fetch origin && git rebase origin/main` (if it stops on a conflict, see Troubleshooting).

Every Friday: `git log --since="7 days ago" --date=short --format="%ad %an %s"` shows what the team did this week.

## Each person's steps

Each person's full step-by-step guide is below, and the same text is inside their bundle in `exports/team_bundles_round2/`.

# Uday Kumar Reddy Yarradoddi: your Git steps, with dates

Follow these in order. Every step says the day it is meant for (Wed 25 Nov 2026 to Thu 03 Dec 2026). Read the files in your bundle before you commit: the commit carries your name.

## Pull request 1: `feature/data-foundation` (8 files, 2 commits)

**Step 1 (Wed 25 Nov 2026): Sync with main**

```bash
git fetch --all --prune
git switch main
git pull --ff-only
```

Your main matches GitHub. If `git pull` complains about local changes, stop and ask: do not discard anything.

**Step 2 (Wed 25 Nov 2026): Make your branch**

```bash
git switch -c feature/data-foundation
```

A branch keeps your work apart until it is reviewed.

**Step 3 (Wed 25 Nov 2026): Unpack your bundle**

Extract `Uday_round2.zip` over the project folder (choose **replace** if asked). In PowerShell: `Expand-Archive -Path <path to the zip> -DestinationPath . -Force`

Your files land at their real paths. Nothing else changes.

**Step 4 (Wed 25 Nov 2026): Check only your files changed**

```bash
git status --short
```

You should see only files from your bundle. If you see `.env`, `data/credentials_*.csv`, `data/.docstore_key` or a `*.log`, **do not add them**.

**Step 5 (Wed 25 Nov 2026): Run the tests and the lint**

```bash
PYTHONPATH=src python -m pytest -q
python -m ruff check src scripts tests finetune
```

On Windows PowerShell: `$env:PYTHONPATH = "src"` first. Red tests before pull request 3 is merged can be expected for some parts; tell the team which ones fail.

**Step 6 (Wed 25 Nov 2026): Commit 1 of 2: Add the document store, profiles, and the database helpers for uploads**

```bash
git add "src/prana/data/db.py"
git add "src/prana/data/docstore.py"
git commit -m "Add the document store, profiles, and the database helpers for uploads" -m "A separate sealed JSON document store (AES-256-GCM, a key per person), the profiles table, and the helpers for reviewing and replacing the values read from a document." -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

2 files. Check with `git show --stat HEAD` that it holds what you expect.

**Step 7 (Wed 25 Nov 2026): Commit 2 of 2: Set up the project: dependencies, lint, CI and ignore rules**

```bash
git add ".env.example"
git add ".github/workflows/tests.yml"
git add ".gitignore"
git add "requirements.txt"
git add "ruff.toml"
git add "scripts/team_commits.py"
git commit -m "Set up the project: dependencies, lint, CI and ignore rules" -m "Adds cryptography, OCR and PDF libraries, the lint settings, a CI workflow that runs the tests on every push, and ignore rules for keys, uploads and password sheets." -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

6 files. Check with `git show --stat HEAD` that it holds what you expect.

**Step 8 (Wed 25 Nov 2026): Push and open the pull request**

```bash
git push -u origin feature/data-foundation
```

On GitHub press **Compare & pull request**, base `main`, add **Sindhu** as reviewer, and paste the commit titles as the description.

**Step 9 (Fri 27 Nov 2026): After it is merged**

```bash
git switch main
git pull --ff-only
git branch -d feature/data-foundation
```

Your branch has done its job. The merge sitting is described at the top of this guide.

## Pull request 3: `feature/portal-api` (15 files, 2 commits)

**Step 10 (Fri 27 Nov 2026): Sync with main**

```bash
git fetch --all --prune
git switch main
git pull --ff-only
```

Your main matches GitHub. If `git pull` complains about local changes, stop and ask: do not discard anything.

**Step 11 (Fri 27 Nov 2026): Make your branch**

```bash
git switch -c feature/portal-api
```

A branch keeps your work apart until it is reviewed.

**Step 12 (Fri 27 Nov 2026): Unpack your bundle**

Extract `Uday_round2.zip` over the project folder (choose **replace** if asked). In PowerShell: `Expand-Archive -Path <path to the zip> -DestinationPath . -Force`

Your files land at their real paths. Nothing else changes.

**Step 13 (Fri 27 Nov 2026): Check only your files changed**

```bash
git status --short
```

You should see only files from your bundle. If you see `.env`, `data/credentials_*.csv`, `data/.docstore_key` or a `*.log`, **do not add them**.

**Step 14 (Fri 27 Nov 2026): Run the tests and the lint**

```bash
PYTHONPATH=src python -m pytest -q
python -m ruff check src scripts tests finetune
```

On Windows PowerShell: `$env:PYTHONPATH = "src"` first. Red tests before pull request 3 is merged can be expected for some parts; tell the team which ones fail.

**Step 15 (Fri 27 Nov 2026): Commit 1 of 2: Add the portal API: register, upload, review, profile, export, clinical data and administrator reads**

```bash
git add "src/prana/api/account_routes.py"
git add "src/prana/api/analytics.py"
git add "src/prana/api/analytics_routes.py"
git add "src/prana/api/risk_routes.py"
git add "src/prana/api/server.py"
git commit -m "Add the portal API: register, upload, review, profile, export, clinical data and administrator reads" -m "Routes for uploading and reviewing documents, editing personal details, downloading a person's data, the clinical view's data and read-only administrator access with an audit trail." -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

5 files. Check with `git show --stat HEAD` that it holds what you expect.

**Step 16 (Fri 27 Nov 2026): Commit 2 of 2: Test the portal API, the document store and the browser flows**

```bash
git add "tests/conftest.py"
git add "tests/test_account.py"
git add "tests/test_analytics.py"
git add "tests/test_api.py"
git add "tests/test_document_store.py"
git add "tests/test_e2e.py"
git add "tests/test_e2e_analytics.py"
git add "tests/test_medical_workflows.py"
git add "tests/test_risk_documents.py"
git add "tests/test_security_phase9.py"
git commit -m "Test the portal API, the document store and the browser flows" -m "API, security, document store, review and account tests, and rewritten browser tests for the five-place portal (they run with RUN_E2E=1)." -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

10 files. Check with `git show --stat HEAD` that it holds what you expect.

**Step 17 (Fri 27 Nov 2026): Push and open the pull request**

```bash
git push -u origin feature/portal-api
```

On GitHub press **Compare & pull request**, base `main`, add **Tanusree** as reviewer, and paste the commit titles as the description.

**Step 18 (Fri 27 Nov 2026): After it is merged**

```bash
git switch main
git pull --ff-only
git branch -d feature/portal-api
```

Your branch has done its job. The merge sitting is described at the top of this guide.

## You also review

- **Tue 01 Dec 2026**: pull request 4 `feature/portal-ui` by Tanusree. On GitHub open **Files changed**, read it, run it if you can (`git fetch origin feature/portal-ui && git switch feature/portal-ui`, then the tests), leave comments, and press **Approve**. Uday presses **Merge** at the merge sitting.

## Thu 03 Dec 2026: final sync (everyone)

```bash
git fetch --all --prune
git switch main
git pull --ff-only
PYTHONPATH=src python -m pytest -q
```

Uday only, once everything is merged and the tests pass:

```bash
git tag -a round2-complete -m "Risk model, uploads, document store, clinical view, safeguard rails"
git push origin round2-complete
```

---

# Sindhu Padmaja Dudekula: your Git steps, with dates

Follow these in order. Every step says the day it is meant for (Wed 25 Nov 2026 to Thu 03 Dec 2026). Read the files in your bundle before you commit: the commit carries your name.

## Pull request 2: `feature/risk-and-ai` (60 files, 4 commits)

**Step 1 (Thu 26 Nov 2026): Sync with main**

```bash
git fetch --all --prune
git switch main
git pull --ff-only
```

Your main matches GitHub. If `git pull` complains about local changes, stop and ask: do not discard anything.

**Step 2 (Thu 26 Nov 2026): Make your branch**

```bash
git switch -c feature/risk-and-ai
```

A branch keeps your work apart until it is reviewed.

**Step 3 (Thu 26 Nov 2026): Unpack your bundle**

Extract `Sindhu_round2.zip` over the project folder (choose **replace** if asked). In PowerShell: `Expand-Archive -Path <path to the zip> -DestinationPath . -Force`

Your files land at their real paths. Nothing else changes.

**Step 4 (Thu 26 Nov 2026): Check only your files changed**

```bash
git status --short
```

You should see only files from your bundle. If you see `.env`, `data/credentials_*.csv`, `data/.docstore_key` or a `*.log`, **do not add them**.

**Step 5 (Thu 26 Nov 2026): Run the tests and the lint**

```bash
PYTHONPATH=src python -m pytest -q
python -m ruff check src scripts tests finetune
```

On Windows PowerShell: `$env:PYTHONPATH = "src"` first. Red tests before pull request 3 is merged can be expected for some parts; tell the team which ones fail.

**Step 6 (Thu 26 Nov 2026): Commit 1 of 4: Add the explainable three-area risk model and its training data**

```bash
git add "data/risk/training_table.csv"
git add "models/risk_model.json"
git add "scripts/build_risk_table.py"
git add "scripts/train_risk_model.py"
git add "src/prana/risk/features.py"
git add "src/prana/risk/model.py"
git add "src/prana/risk/params.py"
git add "src/prana/risk/review.py"
git add "src/prana/risk/service.py"
git commit -m "Add the explainable three-area risk model and its training data" -m "Parameters, features, a per-area gradient-boosted model with exact per-value reasons, the service that merges documents into one picture, and the 900-record training table and trained model." -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

9 files. Check with `git show --stat HEAD` that it holds what you expect.

**Step 7 (Thu 26 Nov 2026): Commit 2 of 4: Read uploaded documents: pattern reader, OCR for photos and scans, optional AI second reader**

```bash
git add "results/extraction_eval.json"
git add "scripts/eval_extraction.py"
git add "src/prana/risk/extract.py"
git add "src/prana/risk/extract_ai.py"
git add "src/prana/risk/ocr.py"
git add "tests/test_extract_ai.py"
git add "tests/test_extract_polish.py"
git add "tests/test_ocr.py"
git add "tests/test_range_before_result.py"
git commit -m "Read uploaded documents: pattern reader, OCR for photos and scans, optional AI second reader" -m "Units converted, ranges not mistaken for results, decimal commas, and an on-device OCR path. The Nemotron second reader only adds values it can prove from a real line, with identity removed first." -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

9 files. Check with `git show --stat HEAD` that it holds what you expect.

**Step 8 (Thu 26 Nov 2026): Commit 3 of 4: Add the medical-insight pipeline, knowledge retrieval and the safeguard rails**

```bash
git add "src/prana/ai/*.py"
git add "scripts/redteam_ai.py"
git add "scripts/check_medgemma.py"
git add "scripts/pregenerate_ai.py"
git add "scripts/export_ai_results.py"
git add "results/redteam.json"
git add "tests/test_ai.py"
git add "tests/test_ai_first.py"
git add "tests/test_analytics_ai.py"
git add "tests/test_guardrails.py"
git add "tests/test_knowledge.py"
git add "tests/test_llm.py"
git add "tests/test_medgemma.py"
git add "tests/test_model_router.py"
git add "tests/test_rerank.py"
git add "tests/test_assessment_store_pg.py"
git add "tests/test_shots.py"
git commit -m "Add the medical-insight pipeline, knowledge retrieval and the safeguard rails" -m "MedGemma insights with highlight marks, the approved-document knowledge base, a router between models, and thirteen numbered safeguard rails applied to every AI path, with a red-team script." -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

31 files. Check with `git show --stat HEAD` that it holds what you expect.

**Step 9 (Thu 26 Nov 2026): Commit 4 of 4: Add the fine-tuning dataset, scoring, and training recipe**

```bash
git add "finetune/PranaSync_MedGemma_Colab.ipynb"
git add "finetune/README.md"
git add "finetune/build_dataset.py"
git add "finetune/data/dataset_card.json"
git add "finetune/data/pranasync_sft_train.jsonl"
git add "finetune/data/pranasync_sft_val.jsonl"
git add "finetune/eval_prompting.py"
git add "finetune/evaluate.py"
git add "finetune/requirements-finetune.txt"
git add "finetune/train_lora.py"
git add "tests/test_finetune_dataset.py"
git commit -m "Add the fine-tuning dataset, scoring, and training recipe" -m "2,082 training and 224 validation examples built from our own data and rules, a scorer that applies the portal's rails, a LoRA recipe and a Colab notebook. Nothing is fine-tuned yet: no GPU." -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

11 files. Check with `git show --stat HEAD` that it holds what you expect.

**Step 10 (Thu 26 Nov 2026): Push and open the pull request**

```bash
git push -u origin feature/risk-and-ai
```

On GitHub press **Compare & pull request**, base `main`, add **Sneha** as reviewer, and paste the commit titles as the description.

**Step 11 (Fri 27 Nov 2026): After it is merged**

```bash
git switch main
git pull --ff-only
git branch -d feature/risk-and-ai
```

Your branch has done its job. The merge sitting is described at the top of this guide.

## You also review

- **Thu 26 Nov 2026**: pull request 1 `feature/data-foundation` by Uday. On GitHub open **Files changed**, read it, run it if you can (`git fetch origin feature/data-foundation && git switch feature/data-foundation`, then the tests), leave comments, and press **Approve**. Uday presses **Merge** at the merge sitting.

## Thu 03 Dec 2026: final sync (everyone)

```bash
git fetch --all --prune
git switch main
git pull --ff-only
PYTHONPATH=src python -m pytest -q
```

Uday only, once everything is merged and the tests pass:

```bash
git tag -a round2-complete -m "Risk model, uploads, document store, clinical view, safeguard rails"
git push origin round2-complete
```

---

# Gavinnolla Tanusree Reddy: your Git steps, with dates

Follow these in order. Every step says the day it is meant for (Wed 25 Nov 2026 to Thu 03 Dec 2026). Read the files in your bundle before you commit: the commit carries your name.

## Pull request 4: `feature/portal-ui` (29 files, 3 commits)

**Step 1 (Mon 30 Nov 2026): Sync with main**

```bash
git fetch --all --prune
git switch main
git pull --ff-only
```

Your main matches GitHub. If `git pull` complains about local changes, stop and ask: do not discard anything.

**Step 2 (Mon 30 Nov 2026): Make your branch**

```bash
git switch -c feature/portal-ui
```

A branch keeps your work apart until it is reviewed.

**Step 3 (Mon 30 Nov 2026): Unpack your bundle**

Extract `Tanusree_round2.zip` over the project folder (choose **replace** if asked). In PowerShell: `Expand-Archive -Path <path to the zip> -DestinationPath . -Force`

Your files land at their real paths. Nothing else changes.

**Step 4 (Mon 30 Nov 2026): Check only your files changed**

```bash
git status --short
```

You should see only files from your bundle. If you see `.env`, `data/credentials_*.csv`, `data/.docstore_key` or a `*.log`, **do not add them**.

**Step 5 (Mon 30 Nov 2026): Run the tests and the lint**

```bash
PYTHONPATH=src python -m pytest -q
python -m ruff check src scripts tests finetune
```

On Windows PowerShell: `$env:PYTHONPATH = "src"` first. Red tests before pull request 3 is merged can be expected for some parts; tell the team which ones fail.

**Step 6 (Mon 30 Nov 2026): Commit 1 of 3: Rebuild the portal into five places with tabs**

```bash
git add "web/css/home.css"
git add "web/css/hubs.css"
git add "web/css/theme.css"
git add "web/index.html"
git add "web/js/app.js"
git add "web/js/glance.js"
git add "web/js/hero.js"
git add "web/js/homeparts.js"
git add "web/js/hubs.js"
git add "web/js/outlook.js"
git add "web/js/record.js"
git add "web/js/ui.js"
git commit -m "Rebuild the portal into five places with tabs" -m "Home, Trends and labs, Analytics and outlook, How it works and Account; old addresses still open the right tab, with back links that name where you came from." -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

12 files. Check with `git show --stat HEAD` that it holds what you expect.

**Step 7 (Mon 30 Nov 2026): Commit 2 of 3: Add upload, review, account, clinical view and the architecture and models pages**

```bash
git add "web/css/risk.css"
git add "web/js/account.js"
git add "web/js/admin.js"
git add "web/js/architecture.js"
git add "web/js/clinical.js"
git add "web/js/landing.js"
git add "web/js/login.js"
git add "web/js/method.js"
git add "web/js/models.js"
git add "web/js/register.js"
git add "web/js/review.js"
git add "web/js/risk.js"
git commit -m "Add upload, review, account, clinical view and the architecture and models pages" -m "Register and upload, a review page to correct each value, an editable Account, the clinical view, flow diagrams, the models page and the administrator viewer." -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

12 files. Check with `git show --stat HEAD` that it holds what you expect.

**Step 8 (Mon 30 Nov 2026): Commit 3 of 3: Highlight key values and words, and tidy the analytics and chat pages**

```bash
git add "web/css/analytics.css"
git add "web/js/ai.js"
git add "web/js/analytics.js"
git add "web/js/chat.js"
git add "web/js/highlight.js"
git commit -m "Highlight key values and words, and tidy the analytics and chat pages" -m "A safe highlighter for values, measures and direction words; a redesigned insight card; the chat and AI status updates." -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

5 files. Check with `git show --stat HEAD` that it holds what you expect.

**Step 9 (Mon 30 Nov 2026): Push and open the pull request**

```bash
git push -u origin feature/portal-ui
```

On GitHub press **Compare & pull request**, base `main`, add **Uday** as reviewer, and paste the commit titles as the description.

**Step 10 (Wed 02 Dec 2026): After it is merged**

```bash
git switch main
git pull --ff-only
git branch -d feature/portal-ui
```

Your branch has done its job. The merge sitting is described at the top of this guide.

## You also review

- **Sat 28 Nov 2026**: pull request 3 `feature/portal-api` by Uday. On GitHub open **Files changed**, read it, run it if you can (`git fetch origin feature/portal-api && git switch feature/portal-api`, then the tests), leave comments, and press **Approve**. Uday presses **Merge** at the merge sitting.

- **Wed 02 Dec 2026**: pull request 5 `docs/data-and-knowledge` by Sneha. On GitHub open **Files changed**, read it, run it if you can (`git fetch origin docs/data-and-knowledge && git switch docs/data-and-knowledge`, then the tests), leave comments, and press **Approve**. Uday presses **Merge** at the merge sitting.

## Thu 03 Dec 2026: final sync (everyone)

```bash
git fetch --all --prune
git switch main
git pull --ff-only
PYTHONPATH=src python -m pytest -q
```

Uday only, once everything is merged and the tests pass:

```bash
git tag -a round2-complete -m "Risk model, uploads, document store, clinical view, safeguard rails"
git push origin round2-complete
```

---

# Sneha Gunturu: your Git steps, with dates

Follow these in order. Every step says the day it is meant for (Wed 25 Nov 2026 to Thu 03 Dec 2026). Read the files in your bundle before you commit: the commit carries your name.

## Pull request 5: `docs/data-and-knowledge` (52 files, 3 commits)

**Step 1 (Tue 01 Dec 2026): Sync with main**

```bash
git fetch --all --prune
git switch main
git pull --ff-only
```

Your main matches GitHub. If `git pull` complains about local changes, stop and ask: do not discard anything.

**Step 2 (Tue 01 Dec 2026): Make your branch**

```bash
git switch -c docs/data-and-knowledge
```

A branch keeps your work apart until it is reviewed.

**Step 3 (Tue 01 Dec 2026): Unpack your bundle**

Extract `Sneha_round2.zip` over the project folder (choose **replace** if asked). In PowerShell: `Expand-Archive -Path <path to the zip> -DestinationPath . -Force`

Your files land at their real paths. Nothing else changes.

**Step 4 (Tue 01 Dec 2026): Check only your files changed**

```bash
git status --short
```

You should see only files from your bundle. If you see `.env`, `data/credentials_*.csv`, `data/.docstore_key` or a `*.log`, **do not add them**.

**Step 5 (Tue 01 Dec 2026): Run the tests and the lint**

```bash
PYTHONPATH=src python -m pytest -q
python -m ruff check src scripts tests finetune
```

On Windows PowerShell: `$env:PYTHONPATH = "src"` first. Red tests before pull request 3 is merged can be expected for some parts; tell the team which ones fail.

**Step 6 (Tue 01 Dec 2026): Commit 1 of 3: Add the knowledge base sources and the helpers that fetch and ingest them**

```bash
git add "config/knowledge_manifest.example.yaml"
git add "config/knowledge_sources.yaml"
git add "data/knowledge/manifest.yaml"
git add "scripts/fetch_medical_sources.py"
git add "scripts/fetch_who_factsheets.py"
git add "scripts/ingest_knowledge.py"
git commit -m "Add the knowledge base sources and the helpers that fetch and ingest them" -m "23 approved WHO and MedlinePlus sources with licences and approvers recorded, and the scripts to fetch and ingest them." -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

6 files. Check with `git show --stat HEAD` that it holds what you expect.

**Step 7 (Tue 01 Dec 2026): Commit 2 of 3: Add made-up sample documents and the data dictionary generator**

```bash
git add "sample_documents/*"
git add "scripts/make_sample_documents.py"
git add "scripts/make_data_dictionary.py"
git add "scripts/visual_regression.py"
git add "docs/DATA_DICTIONARY.md"
git commit -m "Add made-up sample documents and the data dictionary generator" -m "Thirteen sample reports (PDF, Word, Excel, CSV, a photo and a scan) with a README, and a script that writes the data dictionary from the code." -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

18 files. Check with `git show --stat HEAD` that it holds what you expect.

**Step 8 (Tue 01 Dec 2026): Commit 3 of 3: Document the architecture, the safeguard rails, the gaps and the team tasks**

```bash
git add "docs/*"
git add "README.md"
git add "START_HERE.md"
git commit -m "Document the architecture, the safeguard rails, the gaps and the team tasks" -m "Site structure, the upload and OCR flow, the rails, what is still lacking, pitch questions, team tasks, the run guide and the earlier project documents." -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

28 files. Check with `git show --stat HEAD` that it holds what you expect.

**Step 9 (Tue 01 Dec 2026): Push and open the pull request**

```bash
git push -u origin docs/data-and-knowledge
```

On GitHub press **Compare & pull request**, base `main`, add **Tanusree** as reviewer, and paste the commit titles as the description.

**Step 10 (Wed 02 Dec 2026): After it is merged**

```bash
git switch main
git pull --ff-only
git branch -d docs/data-and-knowledge
```

Your branch has done its job. The merge sitting is described at the top of this guide.

## You also review

- **Fri 27 Nov 2026**: pull request 2 `feature/risk-and-ai` by Sindhu. On GitHub open **Files changed**, read it, run it if you can (`git fetch origin feature/risk-and-ai && git switch feature/risk-and-ai`, then the tests), leave comments, and press **Approve**. Uday presses **Merge** at the merge sitting.

## Thu 03 Dec 2026: final sync (everyone)

```bash
git fetch --all --prune
git switch main
git pull --ff-only
PYTHONPATH=src python -m pytest -q
```

Uday only, once everything is merged and the tests pass:

```bash
git tag -a round2-complete -m "Risk model, uploads, document store, clinical view, safeguard rails"
git push origin round2-complete
```

---

## Troubleshooting (everyone)

| Problem | What to do |
|---|---|
| `git push` is rejected | `git fetch origin && git rebase origin/main`, then `git push --force-with-lease` (only on your own branch). Never force-push `main`. |
| A rebase stops on a conflict | Open the files git lists, keep the right lines, remove the `<<<<` `====` `>>>>` marks, then `git add <file>` and `git rebase --continue`. To give up: `git rebase --abort`. |
| You added the wrong file | Before you push: `git reset --soft HEAD~1` (undoes the last commit, keeps your files staged), unstage with `git restore --staged <file>`, commit again. |
| You committed a password or key | **Do not push.** `git reset --soft HEAD~1`, remove it, commit again. If it was already pushed: change that password or key now, and tell Uday. |
| Git shows `data/raw/.gitkeep` deleted | `git restore data/raw/.gitkeep` |
| Your changes look wrong after a pull | `git status` and `git log --oneline -5` first. Ask before using `git reset --hard`: it throws work away. |
| You are on the wrong branch | `git branch --show-current`; to move your uncommitted work: `git stash`, `git switch <right branch>`, `git stash pop`. |

## What never goes in git

`.env`, `data/.docstore_key`, `data/.session_secret`, `data/credentials_*.csv` (plain-text passwords), the databases and uploaded files (`data/*.db`, `data/uploads/`), `results/*.log`, and `exports/`. `.gitignore` already blocks most of these; check `git status` before every commit.
