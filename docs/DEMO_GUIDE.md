# Short demo guide (≈ 8 minutes)

## The night before
* Two laptops run the demo (presenter + backup): `demo_windows.bat` or `bash demo_mac_linux.sh` (see `RUN_GUIDE.md`).
* Keep the dashboard running. Open these browser tabs, each loaded once (first load ~5 s):
  1. `http://localhost:8501/?patient=SYN0001` — diabetes-risk pattern linked to history
  2. `http://localhost:8501/?patient=SYN0009` — same pattern, recent HbA1c missing → system asks for it
  3. `http://localhost:8501/?patient=SYN0111` — only blood pressure rises → **no** pattern (not a high/low alert)
  4. `http://localhost:8501/?patient=SYN0040` — PCOS pattern (cycles get longer + weight + sleep + testosterone)
  5. `results/validation_report.md` open in VS Code preview (or the slides)
* Optional (Sneha): run on 10 real workbooks (RUN_GUIDE §3) and keep one real patient open in a 6th tab.
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
