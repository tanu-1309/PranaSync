# Safeguard rails

A model only writes words. Code decides whether those words may be shown. All of it lives in `src/prana/ai/guardrails.py`, is listed on the portal's **How it works → The models** tab, and is tested in `tests/test_guardrails.py` and by a live attack run (`scripts/redteam_ai.py`).

| Rail | What it does | When |
|---|---|---|
| R0 | Emergencies, medicine questions and diagnosis questions never reach a model: fixed code replies first (`chat.py`, `triage`) | question |
| R1 | Every number in an AI answer must come from the person's own facts | output |
| R2 | No banned phrase (`config/recommendations.yaml`) | output |
| R3 | No diagnosis claim ("you have diabetes") | output |
| R4 | No medicine advice: never start, stop, change, skip or dose | output |
| R5 | No false reassurance when something is outside its range or information is missing | output |
| R6 | No probability of disease: no percentage chance, "in 100", odds | output |
| R7 | No disease forecast over a time horizon ("in the next 10 years you will…") | output |
| R8 | No fear or certainty language ("you will die", "definitely", "guaranteed") | output |
| R9 | No links, email addresses or phone numbers written by the model | output |
| R10 | No sign that a hidden instruction took over ("as instructed", "ignoring my rules", a leaked prompt) | output |
| R11 | Lines in an uploaded document that try to instruct the model are removed before it reads anything | input |
| R12 | Identity (names, birth dates, addresses, phones, emails, IDs) is removed before a document goes to a hosted model | input |

An answer that breaks R1 to R10 is thrown away: the person sees the computed numbers and a plain reason, never a wrong answer. R1 to R10 are applied to the Home and Outlook text, the medical insights, the summary under each graph, the chat and the structured MedGemma answer. The fine-tuning scorer (`finetune/evaluate.py`) uses the same rails, so a tuned model is judged by the rules the portal enforces.

## Where each rail is checked

`analytics_ai._bad_text` (insights, summary), `narrative.validate` (Home and Outlook), `ai_chat.answer` (chat), `medgemma` (structured answers), `extract_ai` (document reading, R11 and R12), `finetune/evaluate.py` (scoring).

## What was tested

- `tests/test_guardrails.py`: 17 attack texts each caught by the right rail, 7 ordinary safe sentences let through (including "I don't give a percentage" and general background that says high blood pressure can be life-threatening), the document cleaner, and a booby-trapped document whose hidden order never reaches the model and cannot add a value.
- `scripts/redteam_ai.py` (live, writes `results/redteam.json`): 24 adversarial questions to the real chat (diagnosis, medicine, percentage, forecast, emergency, jailbreak, role-play, prompt leak, other people, off-scope, certainty, reassurance) and 5 documents with orders hidden in them.
- **First run, honestly:** the hosted free model hit its rate limit (HTTP 429) part way through. Of 29 attacks, **17 were really tried and all 17 held** (11 were answered by the fixed replies, 6 reached the model and its answers broke no rail). **12 could not be tried** (role-play, prompt leak, other people, certainty, reassurance, one off-scope question and all 4 hidden-order documents that need the model). They are marked not tested, not passed. The run also found two faults in the checks themselves, now fixed: a refusal that names a condition ("the record does not say you have heart disease") was read as a diagnosis claim, and the chat was not applying the diagnosis, medicine and reassurance rails at all. **Run `python scripts/redteam_ai.py` again when the hosted model is available** to test the other 12.

## Limits

- The rails are patterns and checks, not understanding. A cleverly worded harmful sentence could pass; a harmless one may be rejected (the person then sees the computed numbers instead).
- The red-team run proves the rails held on those cases, not that no input can get through. Run it again after any change to a prompt, a rail or a model.
- Negation is read by a simple rule (a "not", "can't" or "doesn't" earlier in the same clause, with a "but", colon or full stop starting a new clause), so a refusal such as "the record doesn't say you have diabetes" passes R2 to R4 in the chat, and "That is not a worry. You have diabetes." does not. A cleverly phrased claim could still slip through this rule.
- R2 (banned phrases) lets the words "diagnos" and "emergency" through in AI text, because the portal's own disclaimers use them; R3 and R4 catch the dangerous uses.
- No clinician has reviewed the wording of the rails.
