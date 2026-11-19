# The AI-first version of PranaSync

This folder is a separate copy of the project. The original folders are untouched.

## The idea
Every word a patient reads is written by an AI model from their record. Code does only the arithmetic and the statistical tests, and its results live in **one** place: the **Statistical findings** page. Nothing is written from a rule template any more.

| Part of the portal | Who produces it |
|---|---|
| Headline, overview, clinician summary on Home | AI |
| The four "at a glance" cards (title, big figure, sentence) | AI (colour comes from the computed risk band) |
| "What we found", levels and outlook text, suggestions, questions for the doctor | AI |
| Heart and diabetes risk explanations, trend sentences on Outlook | AI |
| "What would help" page | AI (the raw list from the analysis is shown beneath it) |
| Prana chat answers | AI, with one fixed safety gate (below) |
| Risk numbers, trend charts, projections, reference ranges | Code (published formulas and arithmetic) |
| **Statistical findings page** | Code only: baseline comparison, Mann-Kendall trend test, change-point detection, reference ranges. No AI. |

## How it works
1. `src/prana/ai/facts.py` turns the computed record into compact facts (about 2,500 tokens): measures against their ranges, trend directions and projections, pattern results, medicines, history, missing information, and the two risk estimates with their factors.
2. `src/prana/ai/narrative.py` sends the facts to the model once and asks for one JSON document containing all the text. The result is stored per patient (table `narratives`) and reused until the facts change, so the model is called once per record, not once per page view.
3. `GET /api/narrative` returns it. The browser shows the computed numbers immediately, with a shimmer and a banner, while the AI text is written.
4. `src/prana/ai/ai_chat.py` answers chat questions from the same facts, with the last four turns for context.

## What is checked before any AI text is shown
- **Numbers:** every decimal, and every whole number above 12, must appear in the facts. An invented number is rejected.
- **No diagnosis or medicine instruction:** the banned-phrase list applies to every string.
- **Complete structure:** missing sections are rejected.
- Rejected or failed generations are not stored and are not retried for 60 seconds, to protect a free quota.

## The one fixed part: the safety gate
Emergency, medicine/dose and diagnosis questions get the fixed careful reply written by the team (`chat.triage`), not an AI answer. A model should not be the only thing between a patient and an emergency message. Everything else goes to the AI.

## When the AI is not available
There is no template to fall back on. The page shows a clear notice ("AI text is not available right now", with a Try again button and the reason: not switched on, rate limit, busy, or failed the checks) and the computed numbers and the Statistical findings page keep working.

## What the checks cannot do (honest limits)
- They catch invented numbers and forbidden phrases. They cannot prove a sentence is medically right. A model can still describe a number the wrong way ("steady" for something that is not). Nothing here is clinically validated.
- Text is generated once and stored, so it can be out of date if the model is changed. Bump `VERSION` in `narrative.py` to rewrite everything.
- Every generation sends the full set of facts to the model provider. Fine for practice data; real patients need consent and a provider agreement.
- It needs a capable, fast model. Tested with the real pipeline:
  - **Google Gemini `gemini-3-flash-preview` (free key): works.** The whole document took about 9 seconds, was valid JSON and passed every check; a chat answer took about 4 seconds. Set `PRANA_LLM_REASONING=low` so the model does not spend its output budget on hidden thinking (without it the reply was cut off). Gemini's free quota is per model per day: `gemini-3.5-flash` was used up (429) while `gemini-3-flash-preview` still worked.
  - **OpenRouter free models: not good enough right now.** The Gemma models were rate-limited upstream (429), `nemotron-3-ultra` took about 5 minutes and wrote a rounded number, and `nemotron-3.5-super-vl` took 100 seconds and returned invalid JSON.
  - **Local `llama3.2` on a CPU: too slow.** It timed out after 4 minutes.
- Large values may be written rounded (140.9 as 141); small values such as an HbA1c of 6.32 may not.

## Run it
1. Copy your settings: `copy ..\PranaChain_checkpoint\.env .env` (the key stays on your computer; use `PRANA_LLM_MODEL=gemini-3.5-flash` or a paid model, see `docs/LLM_SETUP.md`).
2. Start the portal: `$env:PYTHONPATH="src"; python -m uvicorn prana.api.server:app --port 8020`
3. Open http://localhost:8020. The first visit takes up to a minute while the AI writes; later visits are instant.

## See also
A second, medical model (MedGemma), a model router, a medical knowledge base and the Analytics & Intelligence page were added later: [MEDGEMMA.md](MEDGEMMA.md), [ANALYTICS_PAGE.md](ANALYTICS_PAGE.md), [KNOWLEDGE_BASE.md](KNOWLEDGE_BASE.md), [MEDGEMMA_DELIVERY_REPORT.md](MEDGEMMA_DELIVERY_REPORT.md).
