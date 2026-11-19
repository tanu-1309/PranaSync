# Presentation split and speaker scripts

Deck: `PranaSync_Client_Presentation.pptx` (23 slides, about 15 to 17 minutes at roughly 40 seconds a slide). The same scripts are in each slide's speaker notes, with the presenter's name at the top.

Each person presents **one continuous block** of slides, says only what they built, says the limits out loud, and answers questions about their own part. Each person also shows their own Git commits on their own laptop.

## Who presents which slides

| Order | Presenter | Role | Slides | Theme |
|---|---|---|---|---|
| 1 | Uday Kumar Reddy Yarradoddi | Lead, backend, security, QA | 1 to 6 (6) | Opening, how the system fits together, safety |
| 2 | Gavinnolla Tanusree Reddy | Front end, UX, conversational AI | 7 to 12 (6) | What the patient sees, the Analytics page, the two models, getting MedGemma running |
| 3 | Sindhu Padmaja Dudekula | Analytics, clinical AI, validation | 13 to 18 (6) | The statistics, the insights and their confidence, what testing found |
| 4 | Sneha Gunturu | Data, database, documentation | 19 to 23 (5) | The data foundation, what is not done, what we need, next steps |

## Running order

| Slide | Presenter | Title |
|---|---|---|
| 1 | Uday | Title |
| 2 | Uday | The whole story in one slide |
| 3 | Uday | Your feedback and what we did |
| 4 | Uday | How the project moved |
| 5 | Uday | How the system fits together |
| 6 | Uday | Safety comes first |
| 7 | Tanusree | A simpler Home |
| 8 | Tanusree | Two AI models, two clear jobs |
| 9 | Tanusree | The Analytics & Intelligence page |
| 10 | Tanusree | Graphs with plain-language explanations |
| 11 | Tanusree | The architecture, shown live |
| 12 | Tanusree | Getting MedGemma connected |
| 13 | Sindhu | The statistics stay in code |
| 14 | Sindhu | Risk estimates with their reasons |
| 15 | Sindhu | A medical insight with its evidence |
| 16 | Sindhu | How the confidence numbers work |
| 17 | Sindhu | What running the real models taught us |
| 18 | Sindhu | Testing and quality |
| 19 | Sneha | A solid data foundation |
| 20 | Sneha | What is not done yet |
| 21 | Sneha | What we need from PranaChain |
| 22 | Sneha | Next steps |
| 23 | Sneha | Thank you |

## Uday Kumar Reddy Yarradoddi (Lead, backend, security, QA): slides 1 to 6

**Slide 1: Title**

> Good morning. We are Team 8, and this is PranaSync, a patient health-record portal. It reads one patient's own record and explains what is changing. It never diagnoses and never advises on medicines. Today we show what changed since the last review, and why.

**Slide 2: The whole story in one slide**

> Five things changed. The interface is simpler. An AI now writes the explanations, with two models sharing the work and each labelled by name. There is a new Analytics page. Safety comes first, with fixed replies and checked numbers. And it is tested, and we are open about what is not done.

**Slide 3: Your feedback and what we did**

> You told us four things: the interface was too long, show a trend with its factors, answer risk questions with reasons, and use AI for the wording. Each row shows what we changed. We will show every one of these live.

**Slide 4: How the project moved**

> Four steps. We built the foundation, updated the plan, upgraded to two AI models, and finally connected the medical model on our own computer. Each step was tested before the next one began.

**Slide 5: How the system fits together**

> Follow the arrows. Code does the numbers. The facts go to a router that picks one of two AI models. Approved documents and safety checks sit after the models. Results are stored per patient, so nothing is recalculated on every visit.

**Slide 6: Safety comes first**

> Emergency, medicine and diagnosis questions get a fixed reply we wrote, and no model is called. This chat reply is an example. Every number an AI writes must be in the record. Only our code can set urgent care. A patient only ever sees their own record.

*Hand-off:* Tanusree will take it from here, starting with what the patient sees.


## Gavinnolla Tanusree Reddy (Front end, UX, conversational AI): slides 7 to 12

**Slide 7: A simpler Home**

> Home is now a short summary. The headline and overview are written by an AI from the record's facts, and the page says so. The ring and every figure are calculated by code. Details moved to their own pages, so nothing is repeated, and the page says it is not a diagnosis.

**Slide 8: Two AI models, two clear jobs**

> Nemotron explains: it writes the summary and a line under each graph, from the numbers the graph shows. MedGemma interprets: it reads the data and gives medical insights. Every result carries its model's name, and if one fails the other keeps working.

**Slide 9: The Analytics & Intelligence page**

> One short page with four parts: summary and graphs from Nemotron, medical insights from MedGemma, and the statistical details and architecture folded away. No model runs when the page opens. Results are stored, so it loads at once.

**Slide 10: Graphs with plain-language explanations**

> Under each graph is a short explanation from Nemotron. It may only use the numbers the graph shows, otherwise the text is rejected. The graphs cover how far measures moved, where a trend is heading, how complete the data is, and what is outside range.

**Slide 11: The architecture, shown live**

> This is on the page itself. Each of the ten parts shows its files, what goes in and out, and its real running state. A missing file would show as not built. MedGemma shows on, and the medical library shows built but empty. Nothing planned is shown as finished.

**Slide 12: Getting MedGemma connected**

> There is no free hosted MedGemma. OpenRouter does not have it, and the Hugging Face route needs paid credit. So we run it on our own computer, which is free and keeps data here. The cost is speed: this computer has no GPU, so one insight takes minutes. We write results ahead of time so the page opens instantly.

*Hand-off:* Sindhu will take it from here, with the numbers, the insights and how confident they are.


## Sindhu Padmaja Dudekula (Analytics, clinical AI, validation): slides 13 to 18

**Slide 13: The statistics stay in code**

> This page has no AI at all. Each measure is compared with the person's own first 60 days. Trends use the Mann-Kendall test, and a pattern needs at least three related signals within 150 days. Our thresholds were set from clinical common sense, so a clinician still needs to review them.

**Slide 14: Risk estimates with their reasons**

> The heart and diabetes estimates show their inputs, their assumptions and their limits. They are estimates for groups of people, not predictions for one person. When data is missing, we say it is not scored and why.

**Slide 15: A medical insight with its evidence**

> Walk down one card. The statement, then evidence strength, then the model's confidence. Below that, the steps that led to it and the numbers behind the steps. Then how medical information helps. The library is empty today, so the card says it is general knowledge, not a cited source.

**Slide 16: How the confidence numbers work**

> There are two separate numbers. Evidence strength is calculated by our code from the statistics, and it is a rule of thumb, not a probability. The model's own level, low, moderate or high, can never be higher than the evidence supports. When we lower it, the card says so.

**Slide 17: What running the real models taught us**

> Real use found bugs. Pages could draw twice. A lab unit was mistaken for a medicine dose. The method's own day counts were rejected as invented. And the small model slipped on its format. Each is fixed and has a test.

**Slide 18: Testing and quality**

> We went from 153 tests to about 300, plus browser, security and database tests. They use stand-in models, so there is no cost. A screenshot comparison shows 23 of 26 older pages unchanged, and the other three have animated backgrounds.

*Hand-off:* Sneha will take it from here, with the data foundation and what is still open.


## Sneha Gunturu (Data, database, documentation): slides 19 to 23

**Slide 19: A solid data foundation**

> We moved from Excel files to a database with 900 patients, 11 sheets each and about 5 million measurements. A record loads in about 3 milliseconds. Every cleaning step is counted and shown, and blank readings are missing, never zero. One limit: the project does not record where this data comes from.

**Slide 20: What is not done yet**

> We want you to hear this from us. No clinician has reviewed the wording or the safety rules. The data's origin is not recorded. The medical library is empty. Consent and privacy law, including PHIPA, are not assessed. And the local medical model is small and slow.

**Slide 21: What we need from PranaChain**

> Five things: where the data comes from and whether it can go to an outside AI service, a clinician to review, approved medical documents with their licences, a decision on consent and regulation, and a decision on faster hosting.

**Slide 22: Next steps**

> Next is work package 8: user testing, clinician review, the items moved from the original plan, and the consent work. Each of us owns an area, and each will show their own work and their own Git commits.

**Slide 23: Thank you**

> Thank you. To repeat: PranaSync describes a person's own data and does not diagnose. Statistics are calculated by code, AI text is labelled with the model that wrote it, and nothing is clinically validated yet. We are happy to take questions.

## Who answers which question

| Question | Answered by | Short answer |
|---|---|---|
| Is this a diagnosis tool? | Uday | No. It describes the patient's own data, never diagnoses, never advises on medicines. |
| Where does the data come from? | Sneha | It is not recorded in the project. We will confirm with PranaChain. |
| What do the confidence numbers mean? | Sindhu | Evidence strength is computed from the statistics, shown with its inputs. The model's level is capped by it. Neither is a probability. |
| Why two models? | Tanusree | Nemotron writes and explains. MedGemma, a medical model, reads the data for insights. Each is labelled, and one failing never affects the other. |
| Does patient data leave the computer? | Uday | MedGemma runs locally, so no. Nemotron runs on OpenRouter and gets only graph numbers for the summary, approved by the project owner. |
| Why is it slow? | Uday | The computer has no GPU. We write results ahead of time and store them. |
| Is it clinically validated? | Sindhu | No. A clinician review is the next step. |

## Before you present

- There are only three hand-offs: after slides 6, 12 and 18. Rehearse those.
- Everyone opens the deck's notes view. The script is there, and the presenter's name is at the top of each slide's notes.
- Uday checks the portal is running (see `docs/DEMO_SCRIPT_TEAM.md`) in case the client asks for a live look.
