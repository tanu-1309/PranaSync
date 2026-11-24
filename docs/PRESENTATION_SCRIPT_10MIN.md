# PranaSync: 10-minute script with live demo

For `PranaSync_Client_Presentation.pptx` (20 slides, 5 per person). Each person gets **2 minutes 30 seconds**: about 1 minute 30 seconds of slides and 1 minute of live demo. Speak the plain text; lines in *italics* are actions.

| Time | Presenter | Slides | Demo |
|---|---|---|---|
| 0:00 – 2:30 | Uday | 1–5 | Safe replies in the chat |
| 2:30 – 5:00 | Tanusree | 6–10 | Home, then the Analytics page |
| 5:00 – 7:30 | Sindhu | 11–15 | An insight card with confidence and a WHO source |
| 7:30 – 10:00 | Sneha | 16–20 | Data quality page and results that open instantly |

## Before you start (Uday, 5 minutes earlier)

1. Start PostgreSQL, then `ollama serve`, then the portal: `$env:PYTHONPATH="src"; python -m uvicorn prana.api.server:app --port 8020` (see `RUN_GUIDE.md`).
2. Open **http://127.0.0.1:8020** (use 127.0.0.1, not localhost) and click **Try the sample record**. Keep this tab open beside the slides.
3. Open the Analytics page once and wait for the summary and insights to appear. The results are stored, so it will be instant for everyone after that.
4. Do not click "Rewrite the summary" during the demo: it calls the free model and can be rate limited.
5. If the page will not load, say so and show the screenshots in the slides. Do not retry live more than once.

---

## Block 1: Uday (slides 1–5, then demo)

**Slide 1.** Good morning. We are Team 8, and this is PranaSync, a patient health-record portal. It reads one person's own record and explains what is changing. It never diagnoses and never advises on medicines. We are four presenters, five slides each, with a short live demo in each part.

**Slide 2.** After your feedback, five things changed. The portal is simpler to read. AI writes the explanations. There is a new Analytics page. Safety comes first. And we tested it and we are honest about the limits.

**Slide 3.** You told us the interface was too long and too wordy. So Home is now a short summary, and every fact appears in one place only. Each result shows its numbers, its usual range and what is missing. Risk answers show their inputs and assumptions.

**Slide 4.** Here is how it fits together. Code does every number. A router sends each task to one of two AI models, and the result is labelled with the model's name. Approved documents and safety checks come last, and nothing reaches the screen unless it passes them.

**Slide 5.** Safety did not change, it got stronger. Dangerous questions get a fixed reply written by us. Every number an AI writes must exist in the record. Only our code can say "seek urgent care", never a model.

**Demo (about 1 minute).**
- *Open the chat (Ask Prana) and type:* `I have chest pain`.
- "This never reaches a model. It is a fixed reply that points to the emergency number."
- *Type:* `Which medicine should I take?`
- "Again a fixed reply: ask a pharmacist or doctor. The portal explains the person's data, nothing more."
- "Now Tanusree will show you what the person sees."

---

## Block 2: Tanusree (slides 6–10, then demo)

**Slide 6.** This is the new Home page. It opens with a short summary and the top points. The headline is written by an AI model from the record's facts, the numbers are calculated by code, and the page always says an AI wrote it. Details moved to their own pages.

**Slide 7.** We use two models with two clear jobs. NVIDIA Nemotron explains: it writes the summary and one line under each graph. Google MedGemma interprets: it reads the data and gives ranked medical insights. If one fails, we say so under its name. We never quietly answer with the other.

**Slide 8.** The Analytics page has four parts: the summary and graphs, the medical insights, the statistical details, and the system architecture, which are folded away. Results are stored, so the page never waits for a model.

**Slide 9.** Each graph is now bigger and has a plain-language explanation that uses only the numbers in that graph. The effect-size chart shows how far each measure moved from the person's own baseline. The forecast shows only strong, lasting trends.

**Slide 10.** There is no free hosted MedGemma, so it runs on our own computer. That is free and keeps patient data here. The cost is speed, minutes per patient, so we write the results ahead of time.

**Demo (about 1 minute).**
- *Go to Home:* "A short summary and one number, nothing else."
- *Open Analytics:* "Five counts at the top, then the summary written by Nemotron, and the label shows which model."
- *Scroll to one graph:* "One graph, one sentence under it that says what to look at."
- *Type in the ask box:* `What changed in my blood pressure?` (only if the answer loaded fine in rehearsal).
- "Sindhu will now show how we trust the insights."

---

## Block 3: Sindhu (slides 11–15, then demo)

**Slide 11.** The statistics stay in code. No AI writes anything on the Statistical findings page. We compare each measure with the person's own first 60 days, test the trend, find change points and compare readings with reference ranges.

**Slide 12.** Risk estimates come with their reasons: the inputs, the assumptions, what is missing, and a statement that estimates are for groups of people, not predictions for one person.

**Slide 13.** Each medical insight shows what the model said, what led to it, how confident the analysis is, and how medical information helps. It ends with a next step: talk to the care team.

**Slide 14.** There are two separate confidence numbers. Evidence strength, from 0 to 100, is calculated by code. For a change over time it is 40% size of change, 35% strength of trend, 25% how complete the data is. The model's own level, low, moderate or high, can never go above what the evidence supports.

**Slide 15.** The AI can only cite documents we approved. We loaded five public World Health Organization fact sheets, 66 passages. A check confirms any quote really exists in the source. Be clear on limits: no clinician has reviewed them, the licence is non-commercial, and cholesterol, vitamin D and sleep are not covered yet.

**Demo (about 1 minute).**
- *Scroll to the first insight card on Analytics.*
- "The statement at the top. The evidence strength bar is a number from our code."
- "Here is what led to it: the steps and the actual values."
- "Here, how medical information helps, and the citation, a WHO fact sheet with the date."
- *Open the Statistical findings page briefly:* "No AI text here, only the statistics."
- "Sneha will cover how we tested it and the data underneath."

---

## Block 4: Sneha (slides 16–20, then demo)

**Slide 16.** Running the real models found bugs. Pages could draw twice. A lab unit was mistaken for a medicine dose. The method's own day counts were rejected as invented numbers. The small model slipped on its format. Each is fixed and has a test.

**Slide 17.** About 300 automated tests pass, up from 153 before this work. We also drive the real page in a browser, check that no keys appear in files or logs, and compare screenshots. Of 26 existing pages, 23 match; the three that differ have animated backgrounds.

**Slide 18.** The data: 900 patient records, 11 sheets each, 5.07 million measurements, in PostgreSQL. A record opens in about 3 milliseconds and an analytics page in about 47. Every cleaning step is counted, never hidden.

**Slide 19.** Next steps: user testing with patients and clinicians, a clinician review of the wording and ranges, consent and provider agreements before any real patient use, more approved documents for cholesterol, vitamin D and sleep, and a faster setup for the medical model.

**Slide 20.** To close: PranaSync describes a person's own data and does not diagnose. Statistics come from code, AI text is labelled with the model that wrote it, and nothing here is clinically validated yet. Thank you, we are happy to take questions.

**Demo (about 1 minute, give this before slide 19 if time allows).**
- *Open the Data quality page:* "900 records, 11 of 11 sheets found, every cleaning step counted."
- *Go back to Analytics:* "The summary and insights opened instantly because they were written ahead of time."
- *Show the terminal running* `python scripts/pregenerate_ai.py --all` *(optional):* "This writes results for every patient. It is resumable, and about 65 hours for all 900 on this computer without a graphics card."
- "That is the demo. Back to the slides."

---

## Likely questions (anyone can answer)

| Question | Answer |
|---|---|
| Is this clinically validated? | No. No clinician has reviewed it. It explains a person's own data and never diagnoses. |
| Does patient data leave the computer? | MedGemma runs locally, so no. Nemotron's text is sent to OpenRouter; that was approved for the project. |
| Can the AI invent numbers? | Every number an AI writes must be in the record or the graph data, or the text is rejected and not shown. |
| Why are the confidence numbers not from the model? | A model is not a reliable judge of its own certainty, so code computes them and the model is capped by them. |
| What if a model is down? | The page says which model failed. It never silently uses the other. |
| What about cholesterol, vitamin D and sleep? | Our five WHO sheets do not cover them, so those insights say there is no approved reference. We plan to add guidelines. |

## Timing tips

- Total spoken text is about 1,100 words, which is about 8 minutes at a calm pace, leaving about 2 minutes for the four demos.
- If you run long, skip the ask-box question (Tanusree) and the terminal (Sneha).
- Hand off with the last sentence of each demo so the next person is already standing.
