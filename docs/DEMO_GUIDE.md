# Short demo guide (≈ 8 minutes)

## The night before
* Two laptops run the demo (presenter + backup): `demo_windows.bat` or `bash demo_mac_linux.sh` (see `RUN_GUIDE.md`).
* **Easiest:** run `python scripts/start_demo.py`. It starts PostgreSQL if it is stopped, finds a free port, starts the portal, checks the database, the model server, the sample record and the chatbot's safe reply, and opens the browser. Run `python scripts/start_demo.py --check` the night before and again an hour before. If any line says [FAIL], fix that first.
* Keep the patient portal running (`http://localhost:8000`, or the port the terminal prints). If you use PostgreSQL, start it first: `python scripts/pg_local.py start`. Open these browser tabs, each loaded once:
  1. The landing page, then **Try the sample record** (the sample patient is set by the `GUEST_ID` environment variable)
  2. The sample record's **Outlook** page (risks, a trend for each measure outside its range)
  3. A signed-in real patient (credentials from your issued sheet), to show per-patient sign-in
  4. `results/validation_report.md` and `results/qa_report.json` open in a viewer (or the slides)
* To tell a different story, restart the portal with another sample patient: `GUEST_ID=SYN0001` (diabetes-risk pattern linked to history), `SYN0009` (same pattern, recent HbA1c missing, so the system asks for it), `SYN0111` (only blood pressure rises, so **no** pattern), `SYN0040` (PCOS pattern: cycles get longer plus weight, sleep and testosterone).
* Optional (Sneha): run on 10 real workbooks (RUN_GUIDE §3) and keep one real patient open in a tab.
* Browser zoom 125 %, notifications off, Wi-Fi not needed.

## Running order
| Min | Who | Show | Key sentence |
|---|---|---|---|
| 0:00 | Uday | Slides: cover, problem, progress (40 %) | "We notice several signals changing together and connect them to the history. We never diagnose." |
| 1:30 | Sindhu | Slide: how it works | "Each signal is compared with the person's own first 60 days; a change must be big, beyond normal noise, a real trend and still present." |
| 2:15 | Sneha | Slide: real data · Data quality tab | "Built on the real 11-sheet layout; every cleaning fix is counted." |
| 3:00 | Sindhu | **Tab 1 → Timeline** | Weight up, steps and sleep down from March; blood pressure stays in its grey band, so it is not part of the pattern. |
| 4:00 | Uday | Tab 1 → Evidence & explanation | Every number comes from the evidence table; it links to "Borderline glycemic markers"; disclaimer always there. |
| 4:45 | Uday | **Tab 2 → Missing data** | "It still analyses what exists and asks for a recent HbA1c." |
| 5:15 | Tanusree | **Tab 3** | "Only BP rose: a threshold alert would fire, we do not call one signal a pattern." |
| 5:45 | Tanusree | Slides: results, scorecard | 0.98 vs 0.41 precision; 0 % vs 80 % false alarms. Planted data, so it proves the pipeline, not clinical accuracy. |
| 6:45 | all | Slides: pros & cons, plan | What works, what doesn't, what we propose to change, the remaining 60 %. |
| 7:45 | Uday | Slide: decisions | Ask the three questions. |

## If the laptop fails
Stay on the slides: the demo slides are screenshots of the same screens. Say "here is the same screen from our run".

## Likely questions and short answers
* **Why not machine learning / deep learning?** Every flag must be explainable with the data behind it, and we have one year per person; simple statistics we can justify beat a black box here.
* **Why not a risk score?** Prana Chain asked us not to: with this data a confidence number would not be trustworthy.
* **How do you know it works on real data?** Real data has no labels. We measure accuracy on planted patterns and, on the real files, run plausibility checks (week 6 plan).
* **What if the first 60 days were already unusual?** Known limit; we plan a "most stable 60 days" baseline option.
* **Where is the AI/LLM?** In this checkpoint the wording is a template. An LLM that only rewords the evidence, with checks on its output, is planned for week 7.
