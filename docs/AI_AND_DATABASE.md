# Database, projections, suggestions and the assistant

## PostgreSQL
- `DATABASE_URL` (environment or git-ignored `.env`) selects the database. Without it the app uses SQLite so tests and CI need no server.
- `python scripts/pg_local.py start` starts a private PostgreSQL 16 on 127.0.0.1:5433 (from the `pgserver` package), creates the `pranasync` role and database, and writes `.env`. Any PostgreSQL 14+ works by setting `DATABASE_URL` yourself.
- `python scripts/init_db.py` loads all workbooks (about 2.5 minutes for 900 patients): `patients`, `timeline` (about 5 million rows, loaded with COPY), `findings`, `records` (the portal package as JSONB), plus `users`. `audit_log` records sign-ins and chat topics, never passwords or message text.
- A stored record carries `PAYLOAD_VERSION`; when the shape changes, old records are rebuilt on demand.

## Projections (`src/prana/ai/forecast.py`)
Weekly means of the last 16 weeks, straight-line fit, damped by 25%, 95% range widened by 25%. A series is projected only when the trend is strong and lasting (Mann-Kendall p < 0.001 and a 90-day change of at least half the detector's minimum). Labs are not projected.
`python scripts/backtest_forecast.py` scores this on patients never used to choose the settings (results in `results/forecast_backtest.json`). Measured: error 0.52x "nothing changes", better in 85% of cases, 94% inside the range, but only about 1 series in 80 qualifies. A naive trend line was worse than "nothing changes", which is why the gate exists.

## Suggestions (`src/prana/ai/recommend.py`, `config/recommendations.yaml`)
Rules over the analysed data fill fixed wording templates. Groups: worth raising, keep an eye on, information that would help, general guidance. Banned phrases (diagnosis, "stop taking", dose changes...) are checked by tests and were checked on all 7,362 suggestions across 895 patients.

## Assistant (`src/prana/ai/chat.py`, `POST /api/chat`)
Safety triage first (emergencies, medicine/dose questions, diagnosis requests get a fixed reply), then intent routing and answers assembled from the signed-in patient's own package. It cannot invent numbers. Rate limited (20 a minute), audited by topic only. It is rule-based; no language model is involved.

## Heart risk (`src/prana/ai/risk.py`) — added after the 3rd Open Office Hours
- The partner asked the chatbot to answer "what are the chances of me getting a heart attack?" with the reasons. The number comes from the published 2013 ACC/AHA Pooled Cohort Equations (10-year chance of a first heart attack or stroke, ages 40 to 79), not from a language model. A test checks our implementation against the paper's worked example for women (2.1%).
- The explanation is "what if" arithmetic: each factor's bar is how many percentage points the estimate would drop if only that factor were at a healthy level. Age and sex are listed as fixed.
- The workbooks do not contain smoking status or race. We assume a non-smoker and use the "white or other" equations, and every answer says so. Outside ages 40 to 79 no percentage is given; the answer lists heart-related measures outside their usual range instead.
- Still to do: have Sindhu check results against ACC's online calculator and a clinician review the wording. The male-equation example gave 5.4%, one tenth above the figure we recall for the paper, so confirm it before quoting it.

## Optional language model (`src/prana/ai/llm.py`)
Off by default. With `PRANA_LLM=1` and `ANTHROPIC_API_KEY` set, the model may reword an answer the rules already built. It never computes anything. Its reply is discarded in favour of the original if any number changed or appeared, a banned phrase appeared, or it grew much longer. Safety replies are never sent to it.

## Accounts
`POST /api/password` changes a patient's password (current password required, at least 10 characters). The device that changed it stays signed in; every other session ends. `POST /api/guest` opens a read-only sample record (`GUEST_ID`, default PC0159) with no account; guests cannot change passwords.

## Predictive questions (added after feedback that "it is not only about heart attacks")
- **Risk scores** (`risk.py`): heart attack or stroke (Pooled Cohort Equations) and type 2 diabetes (FINDRISC, the Finnish Diabetes Risk Score). The diabetes score is shown as a range because waist size and vegetable intake are not in the workbooks.
- **Watch list** (`outlook.py`): every measure outside its usual range gets its own trend line, direction and, only when the trend is strong and lasting, a projection with a range and a "what drove this" note.
- **Chatbot** (`chat.py`): any "chance / risk / will my ... / am I going to ..." question about the heart, stroke, diabetes, blood pressure, cholesterol, kidneys or weight is answered from these. Conditions we cannot score (for example cancer) get an honest "I can't estimate that". Diagnosis questions ("do I have ...") and emergencies still get the fixed safe replies.
- **Language model** (`llm.py`, optional): used to (1) pick the closest of our fixed questions when the rules do not understand the wording, and (2) reword an answer in simpler language. It never produces a number. A language model is not a validated predictor of health risk, so the numbers come from the published scores and the trend statistics, and every reworded answer is checked against the original.
