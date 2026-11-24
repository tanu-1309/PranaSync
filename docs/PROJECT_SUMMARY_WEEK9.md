# PranaSync: project summary and responsibilities (Week 9)

COP 8967 · Team 8 · PranaChain × University of Windsor, "Beyond the Record"

PranaSync is a patient health-record portal. It reads one patient's own record, shows what is changing and why it may matter, and explains it in plain words. It is **not a diagnosis tool**: it never tells anyone to start, stop or change a medicine. It runs on practice data and is **not clinically validated**.

## 1. The team and what each person owns

| Person | Role | Owns |
|---|---|---|
| **Uday Kumar Reddy Yarradoddi** | Team lead, backend and security, QA automation lead | The API and sign-in, the insight layer, all test automation and the CI gate, the one-command demo start |
| **Sneha Gunturu** | Data and database engineer, documentation lead | The data pipeline, PostgreSQL, the stored results format, and every document (README, guides, plan, limitations) |
| **Sindhu Padmaja Dudekula** | Analytics and clinical AI, validation | The method, reference ranges, heart and diabetes scores, forecasts, and the evidence that they work |
| **Gavinnolla Tanusree Reddy** | Front end, user experience and conversational AI | Every page the patient sees, and Prana, the assistant that answers questions |

The detailed file-by-file ownership is in `docs/TEAM_ROLES.md`. Each person must show their own work and their own Git commits on their own laptop.

### Files by person

**Uday**
- `src/prana/api/server.py`, `auth.py`, `src/prana/config.py`, `scripts/serve.py`, `scripts/create_users.py`
- `src/prana/insight/` (pipeline, evidence, explainer, context linker, missing data)
- QA: `tests/conftest.py`, `test_api.py`, `test_security.py`, `test_e2e.py`, `scripts/qa_audit.py`, `scripts/start_demo.py`, `.github/workflows/ci.yml`, `pytest.ini`, `Makefile`, `docs/QA_AUTOMATION.md`

**Sneha**
- `src/prana/data/` (loader, timeline, profiling, db), `src/prana/api/payload.py`, `config/column_map.yaml`, `scripts/run_pipeline.py`, `scripts/init_db.py`, `scripts/pg_local.py`
- Documents: `README.md`, `docs/RUN_GUIDE.md`, `DEMO_GUIDE.md`, `LIMITATIONS.md`, `ARCHITECTURE.md`, `PLAN_AND_DISCUSSION.md`, `AI_AND_DATABASE.md`, `TEAM_ROLES.md`, `TEAM_WORK_SPLIT.md`, `SNEHA_FUTURE_PLAN.md`
- Tests: `tests/test_loader.py`, `tests/test_db.py`

**Sindhu**
- `src/prana/analysis/` (baseline, patterns, reference), `config/scenarios.yaml`, `config/reference_ranges.yaml`, `config/recommendations.yaml`
- `src/prana/ai/forecast.py`, `risk.py`, `recommend.py`, `outlook.py`
- Validation: `scripts/validate.py`, `scripts/backtest_forecast.py`, `docs/VALIDATION.md`, `docs/REFERENCE_VALUES.md`, `results/`
- Tests: `test_analysis.py`, `test_reference.py`, `test_insight.py`, and the risk and forecast tests

**Tanusree**
- Pages: `web/index.html`, `web/js/app.js`, `ui.js`, `record.js`, `outlook.js`, `glance.js`, `hero.js`, `account.js`, `method.js`, `charts.js`, `ai.js`
- First impression: `landing.js`, `login.js`, `bg.js`, `fx.js`, `theme-init.js`; styles `web/css/app.css`, `theme.css`, `landing.css`; `web/img/`
- Conversational AI: `src/prana/ai/chat.py` (safety rules), `ai_chat.py`, `llm.py`, `rerank.py`, `web/js/chat.js`
- Tests: the chatbot tests, `tests/test_ai_first.py`, `tests/test_llm.py`, `tests/test_rerank.py`

The AI-first files (`facts.py`, `narrative.py`, `ai_chat.py`, `rerank.py`) and the extra tests were written during working sessions with an AI assistant at the team's request. Whoever presents a file must understand it and be able to explain it.

## 2. Where the project was and where it is now

| | Week 6 (previous evaluation) | Week 9 (now) |
|---|---|---|
| Plan status | 4 of 10 work packages done (about 40 %) | 7 of 10 done (about 70 %) |
| Data | Excel files | PostgreSQL 16 with all 900 patient workbooks, stored results |
| Access | First portal | REST API, sign-in, password change, guest mode, lockout |
| Wording | Rule-based text | AI-written text and chat, with checks on every number |
| Risk | Basic | 10-year heart estimate and diabetes score, with reasons |
| Interface | Long pages | Shorter pages, landing page, separate Statistical findings page |
| Tests | Unit tests | 153 passing tests (6 skipped), browser tests, cohort audit |

## 3. What changed since the last evaluation, by role

### Uday: backend, security, QA
- Sign-in with signed HttpOnly session cookies, scrypt password hashes, lockout, password change, guest mode.
- Rate limits and audit records on the chat and AI-text endpoints; a content-security-policy header with no inline scripts.
- New endpoints: `/api/narrative` (AI text) and the safe `/api/chat` flow with a fixed safety gate.
- QA automation: 153 tests, Playwright browser tests, a cohort audit over the 900 workbooks, a guard so tests never use a real key.
- Fixed a library clash that stopped the portal after an update: Starlette is now pinned (`starlette>=0.40,<0.42`) because the newest version does not work with FastAPI 0.115.

### Sneha: data, database, documentation
- Moved from Excel to PostgreSQL 16 (JSONB and COPY for fast loads, SQLite fallback for tests); loaded all 900 workbooks.
- Stored results are versioned, so a change to the analysis rebuilds them. The AI text has its own table, keyed by a hash of the patient's facts.
- Fixed login on the AI version (it had an empty database; it now uses the same PostgreSQL accounts).
- Updated the plan, README and How it works page so they all say the same thing; WP 7 re-planned after PranaChain's feedback. Wrote the data dictionary plan (`SNEHA_FUTURE_PLAN.md`).

### Sindhu: analytics, clinical AI, validation
- The method: each measure against the patient's own first 60 days; effect size of at least 0.8 SD; Mann-Kendall trend test (p below 0.05); Theil-Sen slope; change points; a pattern needs at least three signals within 150 days.
- New: 10-year heart estimate (Pooled Cohort Equations, ages 40 to 79), diabetes score (FINDRISC, shown as a range), trend watch list with damped projections that appear only when a strict rule passes.
- Checks on AI text: every decimal and every whole number above 12 must appear in the facts; banned phrases are rejected. Large decimals (50 and above) may be rounded; small ones may not.
- All 900 real workbooks were run and checked. Clinician review is still to do.

### Tanusree: front end, UX, conversational AI
- Redesigned the portal after PranaChain's feedback: four at-a-glance cards, a short overview, findings, suggestions, questions for the doctor, Outlook with risk reasons, and one **Statistical findings** page that no AI writes on.
- Public landing page with a moving, interactive background; sign-in, account and password screens.
- Prana, the chat assistant: answers come from the patient's facts and the last four turns, are checked the same way, and emergency, medicine and diagnosis questions always get a fixed careful reply and never reach the model.
- Language model setup and tests; rerank module for ordering texts with OpenRouter.

## 4. The AI design in one page

1. Code does the arithmetic and statistics only.
2. `facts.py` turns the result into compact facts.
3. `narrative.py` sends the facts to the model once, checks the reply, stores it per patient, and reuses it until the facts change.
4. `ai_chat.py` answers questions from the same facts; the fixed safety gate comes first.
5. If the model is off, busy or fails a check, the page says so. There is no template text behind it, and the statistics still work.

Full detail: `docs/AI_FIRST.md`.

## 5. Problems met and how they were solved

| Problem | Fix |
|---|---|
| Replies cut off | Set the model's reasoning to low and raised the output limit |
| Rate limits and a used-up daily quota | Failure cooldown of 60 s, no retry on 429, text stored per patient, switched model |
| Model rounded 140.9 to 141 and was rejected | Allow rounding only for decimals of 50 and above |
| Tests used a real key by accident | Automatic guard blocks real keys in tests |
| Login failed on the AI version | Pointed it at the PostgreSQL database |
| Landing styles broke the Trends chart | Scoped the styles to the landing page |
| Portal would not start after an update | Pinned Starlette; restarted PostgreSQL |
| Free OpenRouter models | Too slow, or wrote rounded numbers; documented in `AI_FIRST.md` |

## 6. Honest limits
- Practice data only. Not clinically validated. Not a diagnosis tool.
- The checks catch invented numbers and forbidden phrases; they cannot prove a sentence is medically right.
- Every AI generation sends the patient's facts to the model provider. Real patients would need consent and a provider agreement.
- The current setup uses a free OpenRouter model. It is slow and sometimes fails the number check; a stable model is needed for a reliable demo.
- The rerank module works but is not yet used by any page.

## 7. Next steps
- A dedicated AI suggestion model (planned, not built yet): a separate model call that decides, ranks and explains suggestions, each tied to evidence in the record, with its own checks and storage.
- WP 8: user testing, clinician review of the wording and ranges, and the items moved from WP 7 (adherence and habits as signals, a medication-aware baseline, "add missing data and re-run").
- Consent and a provider agreement before any real data goes to an AI service.
- Each person fills in their own next deliverable and date: Uday ____, Sneha ____, Sindhu ____, Tanusree ____.

## 8. Latest changes (this session)
- **Home is now a short summary.** The AI writes only a headline, a two-sentence overview, four cards and at most three "most important" points. Details moved to their own pages: what we found by area on **Trends**, your levels on **Labs**, outlook, risk, suggestions and questions for your doctor on **Outlook**. The AI is told this in its instructions, and the checks reject more than three points on Home.
- **One model family: NVIDIA Nemotron through OpenRouter.** Writing and chat use `nvidia/nemotron-3-ultra-550b-a55b:free`; ordering texts uses `nvidia/llama-nemotron-rerank-vl-1b-v2:free`. Gemini is removed from the settings.

## 9. Improvements by person

**Uday: backend, security, QA**
1. Add a queue that writes the AI text ahead of time for every patient, so nobody waits on a first visit.
2. Handle model failures better: show how long to wait and retry on its own.
3. Add a consent screen and remove personal details from the facts before they go to any model provider.
4. Put the real checks into CI: the cohort audit and browser tests on every pull request.
5. Add more security tests: session expiry, rate limits, and a dependency check, so a library update cannot break the portal again.
6. Measure speed and record it: how long the AI text takes and how often it fails the checks across the 900 records.

**Sneha: data, database, documentation**
1. Write the data dictionary and ER diagram from the live database (planned in `SNEHA_FUTURE_PLAN.md`).
2. One-command database setup that works on a clean computer, tested.
3. Keep a history of AI texts and which model wrote each, for traceability.
4. Add a "missing data" intake: store values a patient adds so the analysis can re-run (WP 8).
5. Keep README, plan, How it works and the zip package in step after every change.
6. Back up and restore steps for PostgreSQL in the run guide.

**Sindhu: analytics, clinical AI, validation**
1. Get a clinician to review the reference ranges and the AI wording, and record the name and date.
2. Add a medication-aware baseline so a medicine that works is not reported as a worsening trend.
3. Add adherence and habits (sleep, activity, missed doses) as signals.
4. Check the heart and diabetes scores against published calculators and report the differences.
5. Run a fairness check across age and sex groups.
6. Report how often AI text is rejected, and why, on a sample of the 900 records.

**Tanusree: front end, UX, conversational AI**
1. Run a usability test with 5 to 10 people on the shorter Home and fix what they find.
2. Build the dedicated AI suggestion model with the ranking step (the rerank model) and show each suggestion's evidence.
3. Add a "was this helpful or wrong?" button on AI text and keep the answers.
4. Add plain-language and reading-level options, a second language, and an accessibility check (contrast, keyboard, screen reader).
5. Add a one-page visit summary for clinicians that can be printed or saved as a PDF.
6. Add every new chat question to the audit with its expected answer, and show a clear "taking longer than usual" state while the slow free model works.

**Everyone**
- Each person commits their own work from their own laptop with their own name, and fills in a next deliverable with a date.

## 10. How to run it
1. Start PostgreSQL: `python scripts/pg_local.py start`
2. Copy `.env.example` to `.env` and add your own model key (never share it).
3. Start the portal: `$env:PYTHONPATH="src"; python -m uvicorn prana.api.server:app --port 8020`
4. Open http://localhost:8020. The first visit per patient can take a while while the AI writes.
5. Tests: `python -m pytest -q` and `python -m ruff check .`

This package leaves out `.env` (it holds secret keys), the local database files, and caches.
