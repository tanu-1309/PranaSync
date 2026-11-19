# Delivery report: dual-model upgrade and Analytics & Intelligence page

Project: PranaSync_AI (the AI-first version, port 8020). The other folders were not touched. Not clinically validated, not privacy-approved, not regulator-assessed.

## 1. Original architecture
FastAPI 0.115 on Starlette 0.41 (pinned), SQLAlchemy 2.0 Core, PostgreSQL 16 (SQLite fallback); a statistical engine (personal baseline, Mann-Kendall, Theil-Sen, ruptures change points, multi-signal patterns within 150 days, reference ranges, Pooled Cohort Equations, FINDRISC-style score, OLS forecasts); one language model (Nemotron through OpenRouter) writing the portal text from compact facts, with number and phrase checks and a fixed safety gate; a plain ES-module front end. 900 patient workbooks (11 sheets each), 5,070,446 timeline rows.

## 2. Final architecture
Patient data → data processing → statistical engine → evidence and facts → **model router** → **Nemotron** (general) or **MedGemma** (medical) → **medical knowledge retrieval** → **safety and validation** → **Analytics & Intelligence page**. The same ten parts are drawn, with live state, on the page itself.

## 3 to 6. Model, hosting, reason, cost
- **MedGemma version selected:** `google/medgemma-1.5-4b-it` (the configured default). **Not deployed.**
- **Cloud hosting provider:** none provisioned. Recommended first host: Hugging Face Inference Endpoints on one L4 GPU, Private, scale to zero. I created nothing and spent nothing.
- **Why this model:** the input is a small text JSON, so the 4B text path is enough; it is instruction-tuned and has a long context. The 27B models need far larger GPUs.
- **Estimated cost (arithmetic from listed prices, not a quote):** an L4 is listed at $0.7 to $0.8 an hour, about $510 to $585 a month always on; with scale-to-zero you pay only while it runs, at least the idle timeout (default 1 hour) per session.

## 7. Files created (23, about 3,700 lines)
- Back end, `src/prana/ai/`: `medgemma.py`, `schemas.py`, `model_router.py`, `knowledge.py`, `medical_explain.py`, `assessment_store.py`
- Back end, `src/prana/api/`: `analytics.py`, `analytics_routes.py`
- Front end: `web/js/analytics.js`, `web/css/analytics.css`
- Config: `config/knowledge_sources.yaml`, `config/knowledge_manifest.example.yaml`
- Scripts: `scripts/check_medgemma.py`, `scripts/ingest_knowledge.py`, `scripts/visual_regression.py`
- Tests: `tests/test_medgemma.py`, `test_model_router.py`, `test_knowledge.py`, `test_medical_workflows.py`, `test_analytics.py`, `test_security_phase9.py`, `test_e2e_analytics.py`, `test_assessment_store_pg.py`
- Docs: `docs/MEDGEMMA.md`, `ANALYTICS_PAGE.md`, `KNOWLEDGE_BASE.md`, this report

## 8. Files modified
- `web/js/app.js`: four lines (import, menu entry, route, title).
- `src/prana/api/server.py`: one import and the router include.
- `tests/conftest.py`: the guard that blocks real keys in tests now also covers the new settings.
- `tests/test_e2e.py`: the new page added to the list of pages visited.
- `.env.example` (comments only), `requirements.txt` (one optional line), `README.md` and `docs/AI_FIRST.md` (links). `.env` was not touched.

## 9. Dependencies added
No new required dependency. Pydantic and NumPy were already installed through FastAPI and pandas. Optional: Pillow, only for `scripts/visual_regression.py`.

## 10. Environment variables
`PRANA_MEDGEMMA_ENABLED`, `_URL`, `_KEY`, `_MODEL`, `_VERSION`, `_PATH`, `_CONNECT_TIMEOUT`, `_TIMEOUT`, `_RETRIES`, `_MAX_TOKENS`, `_SCALE_UP_TIMEOUT`; `PRANA_PRIMARY_MODEL`, `PRANA_MEDICAL_MODEL`, `PRANA_MODEL_COMPARISON_ENABLED`, `PRANA_CLOUD_AI_PATIENTS`, `PRANA_MEDICAL_POSSIBLE_EXPLANATIONS`; `PRANA_RERANK_*`; `PRANA_EMBED_URL/KEY/MODEL`. Meanings and defaults: `docs/MEDGEMMA.md`.

## 11. Database changes
Three new tables, created on first use: `ai_assessments` (one row per patient, task and provider; cache key covers model, version, facts, knowledge and settings), `knowledge_sources`, `knowledge_passages`. No existing table or row was altered; `narratives` is untouched. Checked on your PostgreSQL in a scratch schema that was dropped afterwards (patients, records and users still 900 each).

## 12. API changes
Five new routes: `GET /api/analytics`, `GET /api/analytics/model/{nemotron|medgemma}`, `POST /api/analytics/ask`, `GET /api/analytics/compare`, `GET /api/analytics/report`. All existing routes are unchanged.

## 13 to 17. The page, in short
Details in `docs/ANALYTICS_PAGE.md`. Statistics displayed: overview counts, baselines, Mann-Kendall and Theil-Sen trends, change points, multi-signal patterns, reference comparisons, both risk scores with inputs and limits, forecasts with intervals, missing data and coverage. AI routing: general to Nemotron, medical to MedGemma, comparison only when switched on. Knowledge retrieval: built, empty, keyword or hybrid. The architecture is drawn on the same page with each part's files checked to exist.

## 18. Security and privacy safeguards
Patient taken from the session only; per-patient approval list before anything is sent (default: the practice record); fixed safety replies before any model; numbers, wording and references checked; no keys in files, logs or the browser (tested); audit log records topics, not questions; https required for model addresses; rate limits, cooldowns and one generation at a time.

## 19. Visual regression
The Phase 1 version and the current version were run side by side with the AI off and compared pixel by pixel at desktop and phone width. 23 of 26 pages match; the three that differ (Home on desktop, the landing page on desktop and phone, 0.11 to 0.38 % of pixels) differ only in the hero areas that have animated canvas backgrounds. Run again any time: `scripts/visual_regression.py`.

## 20 and 21. Tests
| | Passed | Skipped |
|---|---|---|
| Before this work | 153 | 6 |
| Now, default run | 265 | 16 (browser and PostgreSQL tests) |
| Now, everything on (`RUN_E2E=1` and `PRANA_TEST_PG_URL`) | **281** | 0 |

All 153 original tests and the 6 original browser tests still pass. Lint is clean. New: 122 tests across 8 files. They use stand-in servers, so no key, internet or cost is needed. The live API was timed on all 900 records (median 47 ms).

## 22. Known limitations
- MedGemma has never been run against a real endpoint; real answers will probably trip the checks more often, and the real model's JSON compliance is unknown.
- Hugging Face's OpenAI-style route, Vertex AI's price and API format, and the regions are unverified. Vertex may need an adapter.
- The knowledge base is empty and, without an embeddings endpoint, is keyword search.
- The checks catch invented numbers and common unsafe wording, not medical errors. Possible explanations are switched off.
- The Nemotron panel reuses the existing text (its generation time was not recorded), and the free Nemotron model is slow and sometimes fails the number check.
- The data's origin (real, synthetic, de-identified) is not documented. The existing Nemotron path already sends each viewed patient's facts to OpenRouter.
- A page-rendering race that already existed in the app (a page sometimes renders twice) was not changed.
- Browser checks were done in Edge on Windows with the practice record; pages for records with detected patterns were tested in the backend only.

## 23 to 25. Install and start (Windows PowerShell)
```powershell
pip install -r requirements.txt
python scripts/pg_local.py start                                  # PostgreSQL (first run creates the database)
$env:PYTHONPATH="src"; python -m uvicorn prana.api.server:app --port 8020    # backend; it also serves the front end
```
There is no separate front-end step and no build. Open http://127.0.0.1:8020 (use `127.0.0.1`; `localhost` can be slow on Windows). Tests: `python -m pytest -q`; with the browser and PostgreSQL tests: `$env:RUN_E2E=1; $env:PRANA_TEST_PG_URL="<your database url>"; python -m pytest -q`. For the browser tests install Playwright and a browser (`playwright install chromium`, or use Edge).

## 26. Cloud deployment
See `docs/MEDGEMMA.md`: accept the terms, create a token, create the endpoint, set the `PRANA_MEDGEMMA_*` values in `.env`, run `python scripts/check_medgemma.py --live`, restart, press Generate on the page.

## 27. Remaining manual steps
1. Confirm with PranaChain where the 900 workbooks come from and whether external model use is allowed. Set `PRANA_CLOUD_AI_PATIENTS` accordingly.
2. Rotate the OpenRouter and Gemini keys that were pasted in chat. Add your keys to `.env` yourself.
3. Accept the MedGemma terms, create the endpoint and token, and run the live check. Approve any cost first.
4. Choose approved documents, confirm their licences, and add them to the knowledge base.
5. Have a clinician review the AI wording and the safety checks before switching on possible explanations or any real use.
6. Decide on consent, a provider agreement and a PHIPA and Health Canada assessment before real patients.
7. Run the browser tests and the visual regression on your own machine.

## Update after review: a simpler page with a clear split between the two models
The first version of the page was too busy and repeated things shown elsewhere. It was rebuilt (see `docs/ANALYTICS_PAGE.md`):
- **Four parts instead of eight:** Summary and graphs, Medical insights, Statistical details (folded) and Architecture (folded). The vitals, lab and timeline charts, the repeated report and the repeated tiles were removed from this page; they stay on their own pages.
- **NVIDIA Nemotron** writes the plain-language summary and one explanation under each of four graphs, from the numbers the graphs show.
- **Google MedGemma** reads the patient's data and gives ranked insights. Each shows the model's steps, the statistics behind them, a **computed evidence strength (0 to 100)**, the **model's confidence level** (never higher than the evidence supports), and **how medical information helps** (the model's general knowledge, labelled as such, plus approved passages as cited sources when the knowledge base has them).
- If MedGemma is not connected, **Generate with Nemotron instead** runs the same feature on Nemotron and labels the result as Nemotron.
- **Pages appearing twice** was a bug in the app's re-draw (`route()` in `web/js/app.js`): a slower, older draw could add a second copy. Only the newest draw now finishes; browser tests check six pages.
- **A bug found by running the real model:** the dose check flagged a lab unit ("115.7 mg/dL") as a medicine dose, which would have rejected many correct answers. Fixed, with a test.
- Files: new `src/prana/ai/analytics_ai.py`, `tests/test_analytics_ai.py`; routes `/api/analytics/summary` and `/api/analytics/insights` replace the per-model route. Tests: 289 passed, 21 skipped by default.
