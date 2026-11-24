# PranaSync: live demo script for the whole team (about 13 minutes)

Team 8. Uday Kumar Reddy Yarradoddi (lead, backend, security, QA) · Sneha Gunturu (data, database, documentation) · Sindhu Padmaja Dudekula (analytics, clinical AI, validation) · Gavinnolla Tanusree Reddy (front end, UX, conversational AI)

Rule for everyone: say only what you built, and say the limits out loud. Every claim below was checked in the project. Nothing is clinically validated.

## 0. Before you start (Uday, 15 minutes earlier)

Run these once, in this order, and keep the windows open. After a PC restart, everything below is stopped.

```powershell
cd PranaChain_checkpoint\PranaChain_checkpoint; python scripts/pg_local.py start    # the database
ollama serve                                                                       # MedGemma runs here (a second terminal)
cd ..\PranaSync_AI
$env:PYTHONPATH="src"; python -m uvicorn prana.api.server:app --port 8020          # the portal
python scripts/pregenerate_ai.py --ids PC0159,PC0001                                # AI text written ahead of time
```

Checklist (tick each one):
- [ ] `http://127.0.0.1:8020/api/health` shows `"database":"postgresql"`. Use `127.0.0.1`, not `localhost` (it is slow on Windows).
- [ ] `python scripts/check_medgemma.py` shows `"configured": true`.
- [ ] The pre-generation printed `ok` four times (it says "already stored" if done before).
- [ ] Open the portal in one browser window at the landing page. Do not click **Generate** on any patient you did not pre-generate: MedGemma takes 3 to 12 minutes on this computer, which has no GPU.
- [ ] The sign-in for PC0001 uses the password in `data/credentials_ISSUE_ONCE.csv` (in the original folder; it is not kept in the repository). Everyone can also use **Try the sample record** with no sign-in.
- [ ] Screen: browser at 100% zoom, light theme, one tab. Put the architecture diagram (`docs/ARCHITECTURE.md`) and the test output in a second window.

## Timing

| Time | Who | Part |
|---|---|---|
| 0:00–1:30 | Uday | What PranaSync is and what changed |
| 1:30–4:00 | Sneha | The data and the database |
| 4:00–7:00 | Sindhu | How the analysis finds a pattern |
| 7:00–11:00 | Tanusree | The portal and the Analytics page, live |
| 11:00–12:30 | Uday | Safety, tests and the honest limits |
| 12:30–13:00 | All | Next steps and questions |

---

## 0:00–1:30 · Uday: open (screen: landing page)

"PranaSync is a patient health-record portal built for PranaChain and the University of Windsor challenge, Beyond the Record. It reads one patient's own record, shows what is changing and why it may matter, and explains it in plain words. It never diagnoses and never tells anyone to start, stop or change a medicine.

Since the last evaluation we moved from Excel files to a PostgreSQL database with 900 patients, we added sign-in, risk estimates, a redesigned interface, AI-written text, and a new Analytics page where two different AI models do two different jobs. I will start the portal, and each of us will show our own part."

Click **Try the sample record**. The portal opens on Home.

## 1:30–4:00 · Sneha: data and database (screen: Data quality page, then Home)

Open **More → Data quality**.

"Each patient is one Excel workbook with 11 sheets: profile, history, medicines, labs, daily vitals, daily wearable data, habits, symptoms, notes, medicine adherence and women's health. There are 900 workbooks. I loaded them all into PostgreSQL: 900 patients, 900 accounts and about 5 million timeline rows. Every cleaning step is counted on this page rather than hidden: sheets found, blank cells, impossible values removed, duplicate days merged.

Real data has gaps. This record has some blank cells, and we show them as missing, never as zero. The analysis results are stored per patient, so the portal does not re-read Excel on every visit; I measured fetching a record at about 3 milliseconds and building the Analytics data at about 18 milliseconds.

The AI text is stored in its own tables with the model name, model version and a fingerprint of the facts it was written from. A Nemotron result can never be shown as a MedGemma result, and a new model or new facts triggers a fresh generation.

Limit: where these 900 workbooks come from, whether real, synthetic or de-identified, is not recorded in the project. We need to confirm it with PranaChain before any real use."

## 4:00–7:00 · Sindhu: the analysis (screen: Home, then Trends, then More → Statistical findings)

"Our analysis is statistics, not a black box. Each measure is compared with the patient's own first 60 days, not with the population. A change counts only if it is large enough, a trend test agrees, and the daily data is complete enough. A pattern is reported only when at least three related signals start changing within 150 days. That keeps false alarms low.

The tests are Mann-Kendall for trends, the Theil-Sen slope, and change-point detection. On top of that we show where each result sits against published reference ranges, a 10-year heart estimate using the Pooled Cohort Equations, and a diabetes score using FINDRISC. Forecasts appear only when a trend is very strong and lasting.

On our synthetic test set with planted patterns the method finds them without false alarms. On the real workbooks there are no labels, so that is a plausibility check only, and almost no record triggers a pattern. This record has none, and the page says so instead of inventing one.

This page, Statistical findings, shows those numbers with no AI at all. Limit: the thresholds were set from clinical common sense and the synthetic data. They need review by a clinician."

## 7:00–11:00 · Tanusree: the portal and the Analytics page (screen: live)

Show **Home**: "Home is a short summary. The four cards and the headline are written by an AI model from the record's facts. Details live on their own pages: what we found on Trends, levels on Labs, outlook and suggestions on Outlook."

Open **Outlook**: "Heart and diabetes estimates with their reasons, and a watch list for any measure outside its range."

Open **Chat with Prana** and type: `I have chest pain`. "Emergency, medicine and diagnosis questions get a fixed, careful reply written by us. They never reach an AI model."

Open **More → Analytics & Intelligence**. Say: "This page has two AI jobs, and each is labelled with the model that did it."

1. **Summary and graphs (NVIDIA Nemotron).** Point at the four graphs. "Under each graph Nemotron explains it in plain words. It sees only the numbers the graph shows, and every number it writes must be one of them or the text is rejected."
2. **Medical insights (Google MedGemma).** Scroll to the first insight card. "MedGemma runs on this computer, so patient data does not leave it. Each insight shows three things:"
   - "**Evidence strength, from 0 to 100, computed by our code** from the statistics. It is a rule of thumb, not a probability, and the inputs are shown."
   - "**The model's confidence** (low, moderate or high). Code can lower it if the statistics do not support it, and the card says when that happened."
   - "**What made it say this:** the model's steps, then the numbers behind them. And **how medical information helps:** what the measure means medically, labelled as the model's general knowledge. We have not loaded any approved medical documents yet, so no source is cited, and the card says that."
3. Open **Ask a medical question** and type: `Should I stop my medicine?` "Fixed reply, no model."
4. Open **Statistical details** and **System Architecture** (both folded). "The architecture shows ten parts with their real state: MedGemma on, the knowledge base empty."

Limit to say: "MedGemma here is a small 4-billion-parameter model on a CPU. A first insight takes minutes, so we wrote them ahead of time. It sometimes names evidence that is not in the record, and then we drop the insight."

## 11:00–12:30 · Uday: safety, tests, limits (screen: terminal with tests)

"Safety is code first, models second. Emergency, medicine and diagnosis questions use fixed replies. Every number an AI writes must come from the record. Diagnosis claims, medicine advice and false reassurance are rejected. Missing information is always listed, never treated as normal, and only code can set urgent care.

For testing we run about 300 automated tests, plus browser tests, a database test and a screenshot comparison. They use stand-in models, so nobody pays for a model call during testing. We also found real bugs by running the real model: a lab unit like mg/dL was mistaken for a medicine dose, and a page could draw twice. Both are fixed with tests.

The honest limits: nothing here is clinically validated, privacy-approved or regulator-assessed. The AI checks catch invented numbers and common unsafe wording, not medical mistakes. The data's origin is unconfirmed. Possible explanations from the model are switched off until a clinician reviews the wording."

## 12:30–13:00 · All: next steps (one line each, with a date you agree before the demo)

- Sneha: data dictionary and ER diagram, [date]
- Sindhu: clinician review of the reference ranges and AI wording, [date]
- Tanusree: usability test with real users, [date]
- Uday: approved documents loaded into the knowledge base and a faster model setup, [date]

## If something goes wrong

| Problem | What to do |
|---|---|
| The portal does not load | Check `http://127.0.0.1:8020/api/health`. If nothing answers, rerun the three start commands in section 0. |
| The Analytics page shows "not generated" | You are on a patient that was not pre-generated. Say so, switch to PC0159 (the sample record) or PC0001, or show the page's states and move on. Do not wait for it. |
| "MedGemma is not connected" | Ollama is not running. Start `ollama serve`, reload. If it still fails, say the insight panel is slow on this computer and show the stored one. |
| An AI text "did not pass the safety checks" | That is the check working. Say so, then press the button once more after a minute, or move on. |
| Browser shows a blank page | Press F5. If it stays blank, open the console and read the error before continuing. |
| A teammate is asked about someone else's part | "That is [name]'s part, they will answer." |

## Questions you will probably get

| Question | Answer (by) |
|---|---|
| Is this a diagnosis tool? | No. It describes the patient's own data, never diagnoses, never advises on medicines. (Uday) |
| How do you know the AI text is safe? | Fixed replies for dangerous questions, every number checked against the record, unsafe wording rejected, a person has not yet reviewed it. (Uday) |
| Where does the data come from? | Not recorded in the project. We will confirm with PranaChain. (Sneha) |
| What does the confidence number mean? | A computed evidence strength from the statistics, shown with its inputs, plus the model's own level capped by it. Not a probability. (Sindhu) |
| Why two models? | Nemotron writes text and explains the graphs. MedGemma, a medical model, reads the data for insights. They are labelled, and one failing never affects the other. (Tanusree) |
| Does patient data leave the computer? | MedGemma runs locally, so no. Nemotron runs on OpenRouter and gets only graph numbers for the summary, which the project owner approved. (Uday) |
| Why is it slow? | The computer has no GPU. We pre-generate and store the results. (Uday) |
| Show me your commits. | Everyone opens `git log --author="<your name>"` on their own laptop. (All) |

## Reminder for the evaluation

Each person shows their own work and their own Git commits on their own laptop. You cannot say you sent code to the lead to commit.
