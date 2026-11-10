# Team roles and who owns what (final phase)

Every file has exactly one owner. The owner writes its tests, can explain it line by line, and pushes it. QA automation is its own role, with its own files and deliverables.

## The four roles

| Person | Role | In one sentence |
|---|---|---|
| **Uday Kumar Reddy Yarradoddi** | Team lead, backend and security, **QA automation lead** | Keeps the system safe and proves it works, automatically, every time. |
| **Sneha Gunturu** | Data and database engineer, documentation lead | Gets clean data into PostgreSQL, and keeps the written record (README, guides, demo material) true and complete. |
| **Sindhu Padmaja Dudekula** | Analytics and clinical AI, validation | The method, the reference ranges, the risk scores and forecasts, and the evidence that they work. |
| **Gavinnolla Tanusree Reddy** | Front end, user experience and conversational AI | Everything the patient sees and touches, including Prana, the assistant that answers their questions. |

## Files by owner

### Uday: backend, security and QA automation
| Area | Files |
|---|---|
| API and sign-in | `src/prana/api/server.py`, `src/prana/api/auth.py`, `src/prana/config.py`, `scripts/serve.py`, `scripts/create_users.py` |
| Insight layer | `src/prana/insight/` (pipeline, evidence, explainer, context linker, missing data) |
| **QA automation** | `tests/conftest.py`, `tests/test_api.py`, `tests/test_security.py`, `tests/test_e2e.py`, `scripts/qa_audit.py`, `.github/workflows/ci.yml`, `pytest.ini`, `Makefile`, `docs/QA_AUTOMATION.md` |

### Sneha: data, database and documentation
| Area | Files |
|---|---|
| Data pipeline | `src/prana/data/` (loader, timeline, profiling, generate_synthetic), `config/column_map.yaml`, `scripts/run_pipeline.py` |
| PostgreSQL | `src/prana/data/db.py`, `scripts/init_db.py`, `scripts/pg_local.py`, `src/prana/api/payload.py` |
| **Documentation** | `README.md`, `docs/RUN_GUIDE.md`, `docs/DEMO_GUIDE.md`, `docs/LIMITATIONS.md`, `docs/ARCHITECTURE.md`, `docs/PLAN_AND_DISCUSSION.md`, `docs/AI_AND_DATABASE.md`, `docs/TEAM_ROLES.md`, `docs/TEAM_WORK_SPLIT.md`, `docs/TEAM_GITHUB_PLAN.md`, the demo scripts (`demo_windows.bat`, `demo_mac_linux.sh`), the demo video and the slides |
| Tests | `tests/test_loader.py`, `tests/test_db.py` |

### Sindhu: analytics, clinical AI and validation
| Area | Files |
|---|---|
| Method | `src/prana/analysis/` (baseline, patterns, reference), `config/scenarios.yaml`, `config/reference_ranges.yaml` |
| Predictions | `src/prana/ai/forecast.py`, `src/prana/ai/risk.py`, `src/prana/ai/recommend.py`, `src/prana/ai/outlook.py`, `config/recommendations.yaml` |
| Validation | `scripts/validate.py`, `scripts/backtest_forecast.py`, `docs/VALIDATION.md`, `docs/REFERENCE_VALUES.md` |
| Tests | `tests/test_analysis.py`, `tests/test_reference.py`, `tests/test_insight.py`, forecast, risk and suggestion tests in `tests/test_ai.py` |

### Tanusree: front end, UX and conversational AI
| Area | Files |
|---|---|
| Pages | `web/index.html`, `web/js/app.js`, `ui.js`, `record.js`, `outlook.js`, `glance.js`, `hero.js`, `account.js`, `method.js`, `charts.js` |
| First impression | `web/js/landing.js`, `login.js`, `bg.js`, `fx.js`, `theme-init.js` |
| Look and feel | `web/css/app.css`, `theme.css`, `landing.css`, `web/img/` |
| **Conversational AI (Prana)** | `src/prana/ai/chat.py` (safety rules, question routing, answers built from the patient's own record), `src/prana/ai/llm.py` (optional language model: question matching and rewording), `web/js/chat.js` (the chat panel) |
| Tests | the chatbot tests in `tests/test_ai.py` (safety, predictive questions, "what changed", language-model checks) |
| User research | The usability test with 3 to 5 people: script, tasks, results table, fixes |

## QA automation: who does what
| Task | Owner |
|---|---|
| Keep the test framework, the CI gate, the cohort audit and the browser tests working and fast | Uday |
| Keep `scripts/start_demo.py` (the one-command demo start and check) working; run it the night before and an hour before every demo | Uday |
| Write unit tests for the files you own (a bug gets a test before the fix) | Each owner |
| Add every new chatbot question to the audit's question list and its expected answer | Tanusree, checked by Uday |
| Add every new risk score or rule to the audit and to a worked-example test | Sindhu |
| Add every new page or button to the browser tests | Tanusree |
| Keep `docs/QA_AUTOMATION.md` and the run guide in step with the checks that exist | Sneha |
| Run the release checklist before each demo and report the numbers | Uday |

## What each person delivers before the final meeting
| Person | Deliverables |
|---|---|
| **Uday** | 1. Browser tests running in CI. 2. Test report numbers for the slides (`results/qa_report.json`). 3. Security hardening list done or documented (HTTPS setting, secrets, lockout). 4. Release checklist rehearsed. |
| **Sneha** | 1. README, run guide, demo guide, limitations and architecture brought up to date with the final system. 2. One-command database setup that works on a clean computer, tested. 3. Schema diagram in the docs. 4. The demo video and slides, with the numbers taken from the QA reports. 5. The blockers and risks log updated with this phase's real problems. |
| **Sindhu** | 1. Heart and diabetes scores checked against the published calculators. 2. Clinician review of `recommendations.yaml` and the chatbot's refusal wording. 3. Updated validation and forecast numbers. 4. The "what the scores do not include" slide. |
| **Tanusree** | 1. The language model tested once with a real key, and the result written down. 2. Prana's answers checked against the audit for every new partner question. 3. Usability test with 3 to 5 people (script, tasks, results table, fixes). 4. Phone and second-browser check of every page. 5. The rehearsed live demo order. |

## Working rules
- One branch and one pull request per task, reviewed by someone else.
- Commit often, with your own name and the real date. Do not squash everyone's work into one commit.
- `make qa` (or the commands in `docs/QA_AUTOMATION.md`) must pass before you open a pull request.
- If you change something you do not own, ask the owner and put them on the review.

## Contributions at a glance

Counted from the files each person owns (no file is owned twice). "Lines" includes code, configuration and documents.

| Person | Files | Lines | Of which documents | Tests they own |
|---|---|---|---|---|
| Uday | 22 | 1,688 | 1 | 35 (API, security, browser, launcher) |
| Sneha | 25 | 2,112 | 10 | 7 (loader, database) |
| Sindhu | 18 | 2,104 | 2 | about 31 (analysis, reference, insight, forecast, risk, suggestions) |
| Tanusree | 23 | 3,541 | 1 | about 23 (chatbot, language model) |

The front end is the largest body of code, so Tanusree's line count is highest. Uday carries the QA framework and the security work, and Sneha carries the written record and the data foundation, so those shares are heavier than their line counts show.

### Uday: what the project gets from his part
- **Safe access:** one account per patient with scrypt-hashed passwords, a signed session, lockout after 5 wrong attempts, 20-minute idle sign-out, password change, and a read-only guest mode. The patient is always taken from the session, never from the request.
- **A hardened server:** security headers, a strict content-security policy, compression, rate limiting on the chatbot, an audit log that never records passwords or message text.
- **The insight layer:** turns the statistical findings into evidence, explanations, links to the patient's history, and a list of missing data.
- **QA automation:** unit and API tests, security tests, 6 browser tests, a 900-patient audit (27,000 chat answers) that blocks any change that breaks a safety rule, the CI gate, and `scripts/start_demo.py` for demo day.
- **Can explain:** how the session and lockout work, why the server never trusts an ID from the browser, what each level of testing proves, and how a bad change gets blocked.

### Sneha: what the project gets from her part
- **Data foundation:** loads and cleans 900 messy workbooks, counts every fix instead of hiding it, and builds one timeline per patient.
- **PostgreSQL:** six tables, about 5.07 million timeline rows loaded with COPY, each patient's portal package stored as JSONB with a version number, plus `init_db.py` and a private local PostgreSQL helper.
- **The written record:** README, run guide, demo guide, limitations, architecture, plan, the AI-and-database notes, the demo scripts, the demo video and slides, and the blockers log.
- **Can explain:** the cleaning rules, why data loads with COPY, what each table holds, how an old stored record is rebuilt, and how to bring the whole system up on a clean computer.

### Sindhu: what the project gets from her part
- **The method:** each measurement compared with the patient's own first 60 days, five change tests, and a rule that a pattern needs at least 3 related signals moving together.
- **Reference ranges:** where each level sits against published guidelines, including levels that are steady but outside the usual range.
- **Predictions:** a 10-year heart-attack-or-stroke estimate (Pooled Cohort Equations) with each factor's share, a type 2 diabetes score (FINDRISC), a trend line for every measure outside its range, and a forecast only when a trend is strong.
- **Suggestions:** rule-and-template recommendations with a banned-phrase check.
- **Validation:** the validation report, the forecast back-test on patients never used for tuning, and the honest limits.
- **Can explain:** why a pattern needs company, how the heart and diabetes scores work and what they leave out, why the first forecast was worse than "nothing changes" and how it was fixed, and what the validation does and does not prove.

### Tanusree: what the project gets from her part
- **Everything the patient sees:** the landing page, sign-in, the Home page with the at-a-glance cards, Trends, Labs, Medicines, Outlook, the account page, the moving heartbeat background, and the plain-language and clinician views.
- **Prana, the assistant:** safety rules first, question routing, answers built only from the patient's record, the heart and diabetes risk answers with their factors, and the chat panel.
- **The optional language model:** matches oddly worded questions to our fixed questions, shows "I read your question as…", works with Ollama on your own computer or a hosted key, and keeps rewording off by default.
- **User research:** the usability test with 3 to 5 people.
- **Can explain:** why the chatbot cannot invent a number, the order of the safety checks, how the language model is limited and checked, and why the interface shows a summary first.
