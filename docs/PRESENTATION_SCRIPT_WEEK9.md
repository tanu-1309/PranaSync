# Week 9 Mid Progress Evaluation: 20-minute team script (PranaSync)

**What the marks need:** show what changed since the last evaluation, run a working demo, explain how our parts fit together, and show proof in Git. Each person is checked on their own laptop with their own commits. Nobody can say "I sent it to the leader to commit".

**Order of the talk:** the main portal work first. The AI part comes last, with more time, because it is the biggest change.

**Rules**
- Each person talks only about their own work, in their own words and simple language.
- Before you start, open your commit list: `git log --author="<your name>" --oneline`.
- Say honestly: practice data only, not checked by doctors yet, never a diagnosis.

| Time | Who | Topic |
|---|---|---|
| 0:00–1:30 | Uday | What the project is and what is new |
| 1:30–4:30 | Sneha | Database and documents |
| 4:30–8:00 | Sindhu | How we find changes and estimate risk |
| 8:00–11:30 | Tanusree | The portal screens (live demo) |
| 11:30–14:00 | Uday | Login, safety, testing |
| 14:00–19:00 | Tanusree, Sindhu, Uday | The AI version |
| 19:00–20:00 | All | Next deliverables, then questions |

---

## 0:00–1:30 · Uday: opening

**Say:**
"We are Team 8. Our project is PranaSync, a patient health-record portal for PranaChain and the University of Windsor. It reads a patient's own record, shows what is changing over time, and explains it in plain words. It never diagnoses, and never tells anyone to start or stop a medicine.

At the last evaluation we had the analysis working and a first portal that read Excel files. Since then:
1. The records moved into a proper database, with all 900 patients and working login.
2. We added heart and diabetes risk estimates and a watch list for measures that are drifting.
3. After PranaChain's feedback we made the screens shorter and simpler.
4. We added automatic tests.
5. We built a second version where an AI model writes all the explanations. We will show that last.

Now each of us shows our own part."

---

## 1:30–4:30 · Sneha: database and documents

**Say:**
"Last time the portal read Excel files directly. That was slow and had no logins. Yesterday my change was merged: all 900 patient records now live in a PostgreSQL database, loaded in bulk so it is fast. The database also keeps the accounts that log in.

Each saved result is marked with a version. When we improve the analysis, old results are rebuilt, so nobody sees out-of-date results.

A problem I fixed: after switching, nobody could log in because the new version had no accounts. I connected it to the same database and all 900 accounts worked.

I also keep the project documents up to date: the design, the limits, the checks, and the guide to run it."

**Show (2 min):**
1. Open the pull request "Move database layer to PostgreSQL with COPY loading and JSONB packages" and its commit.
2. Run `python scripts/init_db.py` and show the tables.
3. Open `src/prana/data/db.py` and `docs/ARCHITECTURE.md`.

**Your files:** `src/prana/data/db.py`, `src/prana/data/loader.py`, `scripts/init_db.py`, `scripts/pg_local.py`, `docs/`.

**Next deliverable:** a data dictionary and a diagram of the database tables, in `docs/`, by **Fri 14 Nov**. After that, the table changes needed to save patient-added missing data, by **Wed 26 Nov**.

---

## 4:30–8:00 · Sindhu: finding changes and estimating risk

**Say:**
"My part is the analysis, and making sure what we show can be trusted.

For each measure, like blood pressure or sugar level, we compare recent values with the patient's own first two months. We call it a change only if it is big enough to matter. We check that the direction is a real trend and not noise. We report a pattern only when at least three signs agree within about five months, so we do not raise false alarms.

New since last time:
- A 10-year heart risk estimate. It is for ages 40 to 79 and describes groups of people like this patient, not one person's future.
- A diabetes risk score. We show a range, because some details, like waist size, are not in our data.
- A watch list. Every value outside its normal range gets a simple look-ahead of where it is heading, shown only when we are confident in it.
- The normal ranges are in one readable file, so a doctor can review them without reading code.

We ran all 900 real records through this and checked the results. Honest limit: no doctor has reviewed it yet. That is our next step."

**Show (2.5 min):**
1. Open the portal's **Statistical findings** page.
2. Open `config/reference_ranges.yaml` and `src/prana/ai/risk.py`.
3. Open `results/validation_report.md`.

**Your files:** `src/prana/analysis/`, `src/prana/ai/risk.py`, `src/prana/ai/forecast.py`, `src/prana/ai/outlook.py`, `config/reference_ranges.yaml`, `scripts/validate.py`, `scripts/backtest_forecast.py`.

**Next deliverable:** a review pack for doctors (the normal ranges, the risk formulas and sample results, one page each) by **Mon 17 Nov**. After that, analysis that takes the patient's medicines into account, by **Mon 24 Nov**.

---

## 8:00–11:30 · Tanusree: the portal screens (live demo)

**Say:**
"My part is what the patient sees. PranaChain told us the screens were too long, so I rebuilt them:
- **Home:** four small cards, a short overview, findings, suggestions, and questions to ask the doctor.
- **Outlook:** the heart and diabetes cards with the reasons behind them, and the watch list.
- **Statistical findings:** all the numbers and tests on one page.
- **How it works:** explains what the project does.
- I also made the public landing page and the sign-in, password-change and guest screens.
- The chat assistant answers questions about the record. For an emergency, a medicine dose or a diagnosis question, it always gives a fixed careful message written by our team.

A problem I solved: my landing-page styles broke the Trends chart, so I limited them to the landing page."

**Show (live, 3 min):**
1. Open the landing page, then sign in.
2. Go through **Home**, **Outlook**, **Statistical findings** and **How it works**.
3. In the chat, type "I have chest pain". The fixed emergency message appears.
4. Open `web/js/glance.js`, `web/js/outlook.js` and `web/js/chat.js`.

**Your files:** `web/js/` (`app.js`, `glance.js`, `hero.js`, `record.js`, `outlook.js`, `chat.js`, `landing.js`, `login.js`, `account.js`, `method.js`), `web/css/`, `src/prana/ai/chat.py`.

**Next deliverable:** test the screens with 5 users, write down what they found and fix the top problems, by **Wed 19 Nov**. After that, an "add missing data and re-run" screen, by **Wed 26 Nov**.

---

## 11:30–14:00 · Uday: login, safety, testing

**Say:**
"My part is the server, safety and testing.

Logging in is protected: passwords are stored scrambled so nobody can read them, an account locks after too many wrong tries, and users can change their password. There is also a guest mode for demos. The chat is limited to a few questions a minute, and we keep a record of who asked what.

How it all fits: Sneha's database feeds Sindhu's analysis, and the results go through the server to Tanusree's screens.

Testing: 152 automatic tests pass. They check the analysis, the login and the screens, so a change that breaks something is caught straight away. I also ran a check over all 900 records."

**Show (2 min):**
1. Start `pytest -q` before your turn and show it finishing with 152 passed.
2. Open `src/prana/api/auth.py` and `docs/QA_AUTOMATION.md`.
3. Show the passing checks on GitHub.

**Your files:** `src/prana/api/auth.py`, `src/prana/api/server.py`, `src/prana/api/payload.py`, `tests/`, `scripts/qa_audit.py`, `scripts/start_demo.py`, `.github/workflows/ci.yml`.

**Next deliverable:** everyone's work merged into one shared repository, with the automatic tests running on every commit, by **Fri 14 Nov**. After that, the final handoff package (run guide, demo guide, test report), by **Fri 28 Nov**.

---

## 14:00–19:00 · The AI version

### Tanusree (about 2 min): what we built and how it works
**Say:**
"PranaChain asked for explanations that read naturally. In the first version, our own rules wrote the sentences from templates. So we built a second version, in a separate folder called `PranaSync_AI`, so the first version stays safe.

The idea is simple. Our code still does the maths. Then it makes a short list of facts about the patient, like 'blood pressure 142, normal is under 130, going up for 4 months'. We send only that list to an AI model, and the model writes everything the patient reads: the overview, the findings, the suggestions, the questions for the doctor, the explanation of the risk estimates, and the chat answers. The text is saved, so we do not ask the AI again unless the facts change.

The page tells the patient when text was written by AI. The numbers and tests stay on their own page, 'Statistical findings', and no AI writes there."

**Show (live, 2 min):**
1. Open **Home** and point at the "Written by AI" label.
2. Ask the chat "how am I doing?". An answer appears in a few seconds.
3. Type "I have chest pain" again. The fixed emergency message appears, not an AI answer.
4. Open `web/js/ai.js` and `src/prana/ai/ai_chat.py`.

### Sindhu (about 1.5 min): keeping the AI safe
**Say:**
"An AI can make things up, so we check it before anything is shown. Every number it writes must be in the facts we gave it. If it invents a number, the text is not shown. We also block words like 'you have diabetes' and any advice to change a medicine. And questions about emergencies, medicines or diagnosis never go to the AI at all. They get the fixed careful message from our team.

If the AI is off, slow or fails a check, the page says so, shows no made-up text, and the Statistical findings page still works.

Honest limit: these checks catch invented numbers and forbidden words. They cannot tell if a sentence is medically right. That is why doctor review is our next step."

**Show:** run `pytest tests/test_ai_first.py -q`, which shows a made-up number being rejected. Open `src/prana/ai/facts.py` and `src/prana/ai/narrative.py`.

### Uday (about 1.5 min): what we tried and the limits
**Say:**
"We tested several free AI models. Google's Gemini works well: the full page takes about 9 seconds and a chat answer about 4. The other free models were too slow or gave broken answers, and a model on our own laptop timed out. We found this by testing, and it is written in `docs/AI_FIRST.md`.

Two limits to be clear about. First, every time the AI writes, the patient's facts are sent to the AI company. That is fine for practice data, but real patients would need their consent and an agreement with the provider. Second, this is not clinically validated."

**AI files:** `web/js/ai.js`, `src/prana/ai/facts.py`, `src/prana/ai/narrative.py`, `src/prana/ai/ai_chat.py`, `src/prana/ai/llm.py`, `tests/test_ai_first.py`, `docs/AI_FIRST.md`.

---

## 19:00–20:00 · All: what comes next

Each person says their one next deliverable and date, in one sentence:
- **Sneha:** data dictionary and table diagram, Fri 14 Nov.
- **Sindhu:** review pack for doctors, Mon 17 Nov.
- **Tanusree:** user testing with 5 users and fixes, Wed 19 Nov.
- **Uday:** one shared repository with automatic tests on every commit, Fri 14 Nov.

Uday closes: "Still to do as a team: test with real patients and doctors, have a doctor review the wording and ranges, add medication-taking habits as signals, make the analysis aware of medicines, and let people add missing data and re-run. Thank you. We can take questions, and each of us can show our own commits."

---

## Future deliverables (full list, in simple words)

| # | Who | What we will deliver | How we will show it is done | Date |
|---|---|---|---|---|
| 1 | Sneha | A data dictionary and a diagram of the database tables | Two documents in `docs/`, reviewed by the team | Fri 14 Nov |
| 2 | Uday | All our work in one shared repository, with the automatic tests running on every commit | The repository on GitHub with a green test check | Fri 14 Nov |
| 3 | Sindhu | A review pack for doctors: normal ranges, risk formulas and sample results | A short document sent to a doctor or PranaChain contact | Mon 17 Nov |
| 4 | Tanusree | Test the screens with 5 users, then fix the top problems | A short report of what users said, plus the fixed screens | Wed 19 Nov |
| 5 | Sindhu | Analysis that takes the patient's medicines into account | A demo where the same value is explained differently with and without a medicine, and passing tests | Mon 24 Nov |
| 6 | Sneha | Saving data the patient adds themselves (missing information) | New tables and a loader, with tests | Wed 26 Nov |
| 7 | Tanusree | An "add missing data and re-run" screen | A live demo: the patient adds a value and sees the results update | Wed 26 Nov |
| 8 | Sindhu | Medication-taking habits (adherence) and lifestyle habits as extra signals, plus a fairness check across age and sex groups | A results page and a short fairness note | Wed 26 Nov |
| 9 | Uday | The final handoff package: run guide, demo guide and test report | Documents in `docs/` and a clean run on a fresh laptop | Fri 28 Nov |
| 10 | All | Final demo and a clear list of what is and is not clinically checked | The final presentation | After 28 Nov |

Items 5 to 8 depend on items 1 and 2 being finished first. A fourth health area is possible only if time is left, so we are not promising it.

Each person can say their own row in one sentence: "By [date] I will deliver [what], and you can see it done by [proof]."

---

## Likely questions

| Question | Who answers |
|---|---|
| Why did you change the screens? | Tanusree: PranaChain said they were too long. |
| Is the data real? | Sneha: practice data. Real data would need consent. |
| Has a doctor checked it? | Sindhu: no. Doctor review is the next step. |
| How do you stop the AI making things up? | Sindhu: every number is checked against the facts, banned words are blocked, and emergencies get a fixed message. |
| What if the AI is down? | Tanusree: the page says so, shows no made-up text, and the Statistical findings page still works. |
| Show me your commits. | Everyone, on their own laptop. |

## Before you present
- [ ] Each person has their own commits and can run `git log --author` on their own laptop.
- [ ] PostgreSQL and the portal are running, and you have opened the patient once so the AI text is ready (the first visit takes up to a minute).
- [ ] Screenshots are saved in case the free AI limit runs out during the demo.
