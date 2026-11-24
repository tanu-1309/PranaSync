# The Analytics & Intelligence page

Open it from **More → Analytics & Intelligence** (`#/analytics`). It is one short page with two AI jobs, each done by a different model and labelled with that model's name.

| Part | Model | What it does |
|---|---|---|
| **Summary and graphs** | **NVIDIA Nemotron** | Writes a plain-language summary of the analysis and one short explanation under each of four graphs |
| **Medical insights** | **Google MedGemma** | Reads the patient's data and gives 3 to 5 ranked insights. Each shows what made it say so, how confident the analysis is, and how medical information helps |
| **Statistical details** | none | The tables behind every number, folded away in one place |
| **System architecture** | none | The ten parts of the system with their state, folded away |

A strip of five numbers sits on top. Nothing here is drawn twice: the vitals, labs and timeline charts stay on their own pages. The comparison of the two models appears only when `PRANA_MODEL_COMPARISON_ENABLED` is on.

**No model runs just because the page was opened.** The page asks for stored results first; a model is called only when you press its button.

## The four graphs (each with a Nemotron line)
1. **How far each measure moved from your own baseline** (effect sizes against the 0.8 threshold).
2. **Where a trend is heading** (weekly averages and the projection with its range, only for trends that passed the strict rule).
3. **How complete the data is** (share of days with a reading).
4. **Results outside or near the edge of their usual range.**

Nemotron sees only the numbers these graphs show, with counts supplied so it never has to count. Every number it writes must be one of them, or the text is rejected and not shown.

## The medical insights
Each insight card shows:
- **The statement** and the model's **confidence level** (low, moderate, high) with its reason.
- **Evidence strength, 0 to 100, computed by code.** A transparent rule of thumb, not a probability, shown with its inputs:
  - for a **change over time**: 40% size of the change (twice the 0.8 threshold counts fully), 35% strength of the Mann-Kendall trend test, 25% completeness of the data;
  - for a **reading against its usual range**: 50% how far outside it is (outside 1.0, near the edge 0.6, inside 0) and 50% how many readings there are (5 or more counts fully).
  - An insight's strength is the average over the measures it names. A measure with neither a baseline and trend nor a usual range is "not scored".
- **The model's confidence can never be higher than the evidence supports:** under 40 means at most low, under 70 at most moderate. When code lowers it, the card says so.
- **What made it say this:** the model's steps, then a table of the numbers behind them taken from the statistics (latest value, usual range, baseline to recent, trend and p-value, strength).
- **How medical information helps:** the model's explanation of what the measure means, labelled as its general knowledge (guideline cut-offs there come from the model's memory and are not checked), plus any approved passages from the knowledge base as cited sources. If none exist the card says so.
- **A next step** (always a conversation with the care team, never a medicine change).

Every number outside that explanation must be in the record (the method's own 30, 60, 90 and 150-day counts are also allowed). Stating a dose that is already in the record is not advice; advising a dose is. An insight that names something not in the record is dropped. A diagnosis claim, medicine advice, false reassurance or an invented number rejects the whole answer (one correction retry, then a safe error).

**If MedGemma is not connected** the page says so and offers **Generate with Nemotron instead**. That runs the same feature on Nemotron and the result is labelled as Nemotron, never as MedGemma.

## API
All routes need a signed-in session. The patient comes from the session cookie, never from a parameter. Model routes are limited to 6 requests a minute per patient.

| Route | Does |
|---|---|
| `GET /api/analytics` | Statistics, model status and architecture (about 50 KB) |
| `GET /api/analytics/summary` | Nemotron's summary and graph explanations. `?cached_only=1` never calls a model |
| `GET /api/analytics/insights` | MedGemma's insights. `?cached_only=1` never calls a model; `?fallback=1` lets Nemotron answer, labelled, if MedGemma is not connected |
| `POST /api/analytics/ask` | A medical question about the signed-in patient's own record (up to 500 characters). The fixed safety gate runs first |
| `GET /api/analytics/compare` | Both models side by side (needs comparison mode on) |
| `GET /api/analytics/report` | A consolidated report from stored results only |

Results are stored per patient, model, version and facts (table `ai_assessments`), one generation at a time, with a 60-second cooldown after a failure. Only patients on `PRANA_CLOUD_AI_PATIENTS` are ever sent to a model (default: the practice record). Set it to `*` only after the data's origin and permission are confirmed.

## Files
`src/prana/ai/analytics_ai.py` (the two AI jobs, the strength score, the checks), `src/prana/api/analytics.py` (statistics, architecture, report), `src/prana/api/analytics_routes.py`, `web/js/analytics.js`, `web/css/analytics.css` (every rule scoped under `.analytics`).

## A fix for pages appearing twice
The app redraws the current page several times while it starts (each time the AI text changes). A slower, older draw could finish after a newer one and add a second copy, so pages and charts could appear twice. `route()` in `web/js/app.js` now lets only the newest draw finish. Browser tests check that no page is drawn twice.

## Troubleshooting
| You see | Fix |
|---|---|
| "Nemotron is switched off" | `PRANA_LLM=1` and a key are needed in `.env` |
| The summary or insights say they did not pass the safety checks | The model used a number that is not in the data, a banned phrase or an unsafe claim. Nothing was shown. Wait a minute and press the button again |
| "not approved for use with an external AI model" | The record is not on `PRANA_CLOUD_AI_PATIENTS` |
| "MedGemma is not connected" | See `docs/MEDGEMMA.md` |
| A blank page after an update | Open the browser console. A syntax error in `analytics.js` stops the whole app's script load |

## Checks
```bash
python -m pytest -q                       # unit and API tests
RUN_E2E=1 python -m pytest -q             # plus the browser tests (PowerShell: $env:RUN_E2E=1)
```
