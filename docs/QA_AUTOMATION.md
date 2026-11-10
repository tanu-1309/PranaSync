# QA automation

Quality is checked automatically at four levels. Anyone can run all of it with one command: `make qa` (macOS/Linux) or the commands in the table (Windows). CI runs the same checks on every push and pull request, and a failure blocks the merge.

| Level | What it proves | Where | Run it | Speed |
|---|---|---|---|---|
| 1. Lint | No unused code, no syntax slips | `ruff` | `ruff check .` | 1 s |
| 2. Unit and API tests | Each part behaves; sign-in, lockout, password change, guest mode, risk scores, forecasts, suggestions, chat safety | `tests/test_*.py` | `python -m pytest -q` | ~30 s |
| 3. Security tests | Headers (CSP, nosniff, frame deny), HttpOnly cookie, compression, no inline scripts, only password hashes stored, the session decides who you are, odd input handled | `tests/test_security.py` | `python -m pytest tests/test_security.py -q` | 5 s |
| 4. Cohort QA audit | Every stored patient package is complete; no banned phrase in any suggestion or answer; chat never crashes; emergency, medicine and diagnosis questions always get the safe reply; every predictive question is answered | `scripts/qa_audit.py` | `python scripts/qa_audit.py` | 5 s for 900 patients and 27,000 answers |
| 5. Browser end-to-end tests | A real browser: landing page, sample record, all pages open, charts hover, chatbot risk answer and refusals, sign-in, password change, sign-out, wrong password, phone-width layout, no JavaScript errors | `tests/test_e2e.py` | `RUN_E2E=1 python -m pytest tests/test_e2e.py -q` | ~20 s |

## Rules the team follows
1. **Every bug gets a test first.** Reproduce it as a failing test, fix it, keep the test. (Example: the chat starter "Did anything change for me?" answered "I'm not sure" for every patient; it now has a test for every kind of patient.)
2. **Safety questions are regression-tested forever.** The cohort audit asserts that "I have chest pain", "Should I stop my medicine?" and "Do I have diabetes?" get the fixed safe replies for all 900 patients.
3. **No merge on red.** Lint, tests, the cohort audit and the browser tests must pass.
4. **Each owner writes tests for their own files;** the QA lead owns the framework, the CI gate, the audit and the browser tests (see `TEAM_ROLES.md`).
5. **Numbers that go in front of the judges come from these reports**, not from memory: `results/qa_report.json`, `results/metrics.json`, `results/forecast_backtest.json`.

## Latest results (this checkout)
- Unit, API, security and language-model tests: 119 passed; browser tests: 6 passed (6 skipped unless `RUN_E2E=1`).
- Cohort audit: 900 patients, 27,000 chat answers and about 7,400 suggestions checked, 0 failures. Chat answers take under a millisecond.
- Heart risk is scored for 477 of 900 patients (the published formula covers ages 40 to 79 only) and diabetes risk for 854.

## Not yet automated (honest gaps)
- Real-device and Safari/Firefox testing, and keyboard-only and screen-reader checks (do by hand once before the final).
- The optional language model with a real API key (needs a key; the checks around it are tested, the live call is not).
- Clinical correctness of the risk scores (needs a clinician or the published calculators; tests only check our code against one published worked example).
- Load testing (the prototype is a single server).

## Release checklist (run before the demo)
1. `ruff check .` then `python -m pytest -q` are green.
2. `python scripts/init_db.py` then `python scripts/qa_audit.py` prints `RESULT: PASS`.
3. `RUN_E2E=1 python -m pytest tests/test_e2e.py -q` is green.
4. Open the portal in a normal window, sign in with a real account, click every menu item once, ask the chatbot three questions, change a password and sign out.
5. Start PostgreSQL (`python scripts/pg_local.py start`) and the server before the audience arrives.
