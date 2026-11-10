> **Current split:** see [`TEAM_ROLES.md`](TEAM_ROLES.md) (roles for the final phase, including QA automation). The text below is the earlier checkpoint split, kept for the commit history.

# Dividing the work equally (4 people)

Every file in the project is owned by exactly one person, and the four shares are within a few percent of each other by lines of code. The owner is the person who pushes the file and must be able to explain it. The order below keeps `python -m pytest -q` green after every merge (checked by replaying the merges in order).

## Shares

| Person | Area | Files | Lines |
|---|---|---|---|
| Sneha Gunturu | Data pipeline, accounts and portal API, validation doc | 15 | 1,371 |
| Gavinnolla Tanusree Reddy | Repo set-up, checkpoint dashboard and CI, portal pages and charts, results | 29 | 1,388 |
| Sindhu Padmaja Dudekula | Analysis, reference-value layer, validation script, reference and portal tests | 11 | 1,326 |
| Uday Kumar Reddy Yarradoddi | Insight layer and pipeline, portal page shell and sign-in, plan and limits docs | 19 | 1,372 |

Images and JSON are counted as files but not as lines.

## Merge order

| # | Who | Branch | What | Reviewer |
|---|---|---|---|---|
| 1 | Tanusree | `chore/repo-setup` | Repo set-up | Uday |
| 2 | Sneha | `feature/data-pipeline` | Data pipeline | Sindhu |
| 3 | Sindhu | `feature/analysis` | Analysis and reference values | Sneha |
| 4 | Uday | `feature/insight` | Insight layer and pipeline | Tanusree |
| 5 | Tanusree | `feature/dashboard-ci` | Checkpoint dashboard and CI | Sneha |
| 6 | Sindhu | `feature/validation-script` | Validation script | Uday |
| 7 | Sneha | `docs/validation` | Validation document | Sindhu |
| 8 | Uday | `docs/plan-and-limits` | Plan, limits and demo guide | Tanusree |
| 9 | Tanusree | `docs/results-and-team` | Results and team plan | Uday |
| 10 | Uday | `feature/portal-shell` | Portal page shell and sign-in screen | Tanusree |
| 11 | Sneha | `feature/portal-api` | Accounts and portal API | Uday |
| 12 | Tanusree | `feature/portal-views` | Portal pages and charts | Uday |
| 13 | Sindhu | `feature/portal-tests-docs` | Portal and reference tests and docs | Sneha |

PRs 1-9 are the checkpoint; 10-13 are the patient portal and the reference-value layer. If the checkpoint PRs (1-6 in `TEAM_GITHUB_PLAN.md`) are already merged on GitHub, start at PR 10.

## Who owns which files

### Sneha Gunturu

**PR 2, Data pipeline**
* Add column map for the 11-sheet patient workbook: `config/column_map.yaml`
* Add workbook loader with cleaning and plausibility checks: `src/prana/data/__init__.py`, `src/prana/data/loader.py`
* Build the unified patient timeline: `src/prana/data/timeline.py`
* Add database storage and data profiling: `src/prana/data/db.py`, `src/prana/data/profiling.py`
* Add synthetic workbook generator with planted patterns: `src/prana/data/generate_synthetic.py`
* Add loader tests and shared fixtures: `tests/conftest.py`, `tests/test_loader.py`

**PR 7, Validation document**
* Document how to read the validation numbers: `docs/VALIDATION.md`

**PR 11, Accounts and portal API**
* Add patient accounts with hashed passwords, lockout and session versioning: `src/prana/api/__init__.py`, `src/prana/api/auth.py`
* Add account creation script with random passwords: `scripts/create_users.py`
* Add portal API: login, logout and the patient's own record: `src/prana/api/server.py`
* Add portal launcher: `scripts/serve.py`

### Gavinnolla Tanusree Reddy

**PR 1, Repo set-up**
* Add package skeleton and shared config helper: `src/prana/__init__.py`, `src/prana/config.py`
* Add dependencies, pytest settings and git hygiene files: `requirements.txt`, `pytest.ini`, `.gitignore`, `.gitattributes`, `.env.example`
* Add Makefile shortcuts and the run guide: `Makefile`, `docs/RUN_GUIDE.md`

**PR 5, Checkpoint dashboard and CI**
* (The Streamlit checkpoint dashboard was later removed; the patient portal in `web/` replaced it.)
* Add CI workflow: `.github/workflows/ci.yml`
* Add one-command demo scripts: `demo_windows.bat`, `demo_mac_linux.sh`
* Add dashboard screenshots: `docs/screenshots/01_patient_timeline.png`, `docs/screenshots/02_evidence.png`, `docs/screenshots/03_missing_data.png`, `docs/screenshots/04_pcos_timeline.png`

**PR 9, Results and team plan**
* Add validation report, metrics and figures: `results/validation_report.md`, `results/metrics.json`, `results/figures/false_alarms.png`, `results/figures/onset_lag.png`, `results/figures/precision_recall_vs_threshold.png`
* Add team workflow and work split: `docs/TEAM_GITHUB_PLAN.md`, `docs/TEAM_WORK_SPLIT.md`

**PR 12, Portal pages and charts**
* Add chart components: year map, timelines and lab cards: `web/js/charts.js`
* Add record pages: overview, reference levels, medications and more: `web/js/record.js`
* Add How it works and The evidence pages: `web/js/method.js`
* Update README for the patient portal: `README.md`

### Sindhu Padmaja Dudekula

**PR 3, Analysis and reference values**
* Add scenario configuration for the three health areas: `config/scenarios.yaml`
* Add personal baseline, trend test and change point: `src/prana/analysis/__init__.py`, `src/prana/analysis/baseline.py`
* Add the multi-signal pattern rule: `src/prana/analysis/patterns.py`
* Add reference-value layer with sourced clinical ranges: `src/prana/analysis/reference.py`, `config/reference_ranges.yaml`
* Add analysis tests: `tests/test_analysis.py`

**PR 6, Validation script**
* Add validation against planted ground truth: `scripts/validate.py`

**PR 13, Portal and reference tests and docs**
* Add reference-layer tests: `tests/test_reference.py`
* Add portal API tests: `tests/test_api.py`
* Document reference values and planned AI suggestions: `docs/REFERENCE_VALUES.md`

### Uday Kumar Reddy Yarradoddi

**PR 4, Insight layer and pipeline**
* Add history and context linking: `src/prana/insight/__init__.py`, `src/prana/insight/context_linker.py`
* Add missing-data requests: `src/prana/insight/missing_data.py`
* Add evidence pack and template explanations: `src/prana/insight/evidence.py`, `src/prana/insight/explainer.py`
* Add end-to-end pipeline and batch runner: `src/prana/insight/pipeline.py`, `scripts/run_pipeline.py`
* Add insight tests and the architecture document: `tests/test_insight.py`, `docs/ARCHITECTURE.md`

**PR 8, Plan, limits and demo guide**
* Add project plan and discussion: `docs/PLAN_AND_DISCUSSION.md`
* Document limitations: `docs/LIMITATIONS.md`
* Add demo walkthrough: `docs/DEMO_GUIDE.md`

**PR 10, Portal page shell and sign-in screen**
* Add portal page, design tokens and the PranaSync logo: `web/index.html`, `web/css/app.css`, `web/img/logo.png`, `web/img/favicon.png`
* Add DOM helpers, status vocabulary and API client: `web/js/ui.js`
* Add sign-in screen: `web/js/login.js`
* Add portal shell, routing and idle sign-out: `web/js/app.js`

## How to commit

1. Each person has a ready-made folder in `team_bundles/<Name>/` with their files at the right paths and a `PUSH_INSTRUCTIONS.md` that lists the exact `git add` and `git commit` lines.
2. **Use a fresh clone of the PranaChain repository.** The folder this project was built in is not its own repository: git there points at your home directory, and `git add .` would try to stage everything in it.
3. One logical commit per piece (3-6 per PR), each with a message saying what it does, never one big commit. Commit when you actually finish each piece.
4. Push the branch, open a pull request, the named reviewer merges. Pull `main` before starting your next branch.

## About dates
Commits carry the time they are really made, and GitHub also records when each push and pull request happened. Please do not set earlier dates by hand: the history is evidence of when the work was done, and instructors and the client rely on it. Small, well-described commits made over your real working sessions already read as steady progress. If the repository was set up late, say so plainly in the report (for example, "history consolidated on <date>"); that is honest and acceptable.
