# Team tasks after the risk model, uploads, document store and clinical view

Written from the state of the project on 24 November 2026: what is built and tested (341 tests pass), and what still needs a person. Each task says what **done** looks like so it can be checked, not just claimed. Nothing below has been reviewed by a clinician; several tasks are about getting that review.

## Uday Kumar Reddy Yarradoddi: lead, backend, security, QA

1. **Protect and back up the document store key.** `data/.docstore_key` (or `PRANA_DOCSTORE_KEY`) seals every uploaded document; losing it makes them unreadable. Decide where the key lives for real use (environment or a secrets manager), write the backup and restore steps, and test a restore on a copy. *Done when:* a fresh machine opens a restored document.
2. **Security review of the new surfaces.** Administrator role (`PRANA_ADMIN_IDS`), the audit log entries (`admin_document_view`, `admin_denied`, `profile_edit`, `document_values_reviewed`), rate limits on the new routes, and the "not found for strangers" rule. Decide whether the values in the main database should be encrypted too (today they are not). *Done when:* a short threat model lists each risk and what covers it, and any gap has an owner.
3. **Decide the Nemotron second reader's privacy position.** It sends identity-stripped lines of an uploaded document to a hosted free service. Approve it, restrict it, or switch it off (`PRANA_EXTRACT_AI=0`), and say so in the privacy text. Test the identity removal (`src/prana/risk/extract_ai.py`) against real-looking documents. *Done when:* a written decision, and tests for any new rule.
4. **Move the document store and the main database to a production setup.** `DOCSTORE_URL` can point at PostgreSQL; add backups, and make `scripts/pg_local.py start` part of the run guide (PostgreSQL stopped after every restart during this work). *Done when:* both databases survive a restart and a backup restores.
5. **QA on the new flows.** 21 tests are skipped (browser tests among them). Add browser tests for upload, review and correct, the clinical view tabs, and the account edit. Run the full suite in CI. *Done when:* the skipped count is explained or reduced, and CI is green on every push.
6. **Password recovery.** Registration has no email, so a lost password cannot be recovered. Propose and build the smallest safe option (for example, one-time recovery codes shown at sign-up). *Done when:* a person who lost their password can regain their account without an administrator seeing their data.

## Gavinnolla Tanusree Reddy: front end, UX, conversational AI

1. **Test the five-place layout with real people.** Three to five people, one task each: upload a document and correct a value; find the missing values; open the clinical view; edit their details. Note where they hesitate. *Done when:* a one-page findings list and the fixes made.
2. **Accessibility pass beyond the automated checks.** The automated checks found no problems, but they do not replace a screen reader (NVDA), keyboard only, 200% zoom, dark mode and a phone. *Done when:* each page is checked in all five ways and issues are fixed or listed.
3. **Polish the review page.** Show the original document next to the values where possible (PDF preview), make the table a stack of cards on a phone, and decide with the client whether a person may add a value that was not read (today only read values can be changed). *Done when:* the client has seen and approved it.
4. **Tune the highlights.** Review the word lists in `web/js/highlight.js` against real MedGemma output once new insights are generated, so the right values, measures and direction words stand out and nothing else. Apply the same highlighting to chat answers. *Done when:* a sample of 20 outputs is highlighted sensibly.
5. **Chat (Prana).** Update the suggestions and page links to the five places, remove leftover "10-year" wording anywhere it survives, and decide about the "Chat with Prana" button in the Home header (the top-bar one was removed). *Done when:* every suggested question gets an answer that matches the Home cards.
6. **Check the Architecture and How it works pages read well.** Read them as a patient and as a clinician; shorten what is heavy. *Done when:* one reviewer outside the team understands the upload flow from the diagram alone.

## Sneha Gunturu: data, database, documentation

1. **Write the data dictionary and database diagram.** Tables `accounts`, `profiles`, `documents`, `observations`, `risk_snapshots`, and the document store's JSON document (version it, `version: 1`). Include the 21 parameters with units, limits and the conversions. *Done when:* a new teammate can find any value from upload to screen using only the document.
2. **Fill the knowledge-base gaps and get sign-off.** The WHO anaemia sheet and the CDC and NIH vitamin D pages could not be read; find replacements or fix the fetch. Check each of the 23 sources' licence and date, and get a clinician's name on `approved_by` instead of the project owner's. *Done when:* every source has a reviewer, and a search for each lab test the portal shows returns a passage.
3. **Verify the unit conversions and plausibility limits** (mmol/L to mg/dL, HbA1c mmol/mol to %, the limits in `src/prana/risk/params.py`) against a laboratory reference. *Done when:* a table of the checks sits beside the code.
4. **Grow the sample documents.** More layouts (two-column reports, ranges before and after results, other languages' decimal commas), and real de-identified layouts with permission. Keep the README current. *Done when:* each failure found becomes a sample and a test.
5. **Update the documents that predate the new work.** The 20-slide deck and the 10-minute script describe the old risk estimate and know nothing of uploads, review, the clinical view or the document store. Update `README.md` and `docs/RUN_GUIDE.md` too. *Done when:* a demo can be given from the documents alone.
6. **Data handling for legacy and backups.** A script that moves documents uploaded before the store existed, and one that checks the main database and the store agree. *Done when:* the check reports zero mismatches.

## Sindhu Padmaja Dudekula: analytics, clinical AI, validation

1. **Clinical review of the risk model.** Get a clinician to review the 21 parameters, the direction rules (for example "higher LDL can only raise heart risk"), the class cut-offs and the wording, and to read at least 100 outputs. State plainly that the labels are recorded diagnoses in practice records, not what happened later. *Done when:* a signed review note, and changes made from it.
2. **Run the fine-tuning and judge it honestly.** On a GPU you have permission to use, run `finetune/train_lora.py`, then `finetune/evaluate.py` against the untuned MedGemma on the same validation prompts. A tuned model replaces the old one only if it passes more checks and a clinician agrees. *Done when:* a results table, tuned against untuned, and a yes or no.
3. **Widen the extraction evaluation.** `scripts/eval_extraction.py` used made-up documents from a few layouts. Add real de-identified layouts and report recall, precision, F1 and invented values again; the invented count must stay zero. *Done when:* the Architecture page's numbers come from the wider set.
4. **Validate what the statistics claim.** Re-run `scripts/validate.py` and the forecast back-test, check the class cut-offs across age and sex groups, and list any group where the model behaves differently. *Done when:* a short fairness and stability note.
5. **Judge the medical insights properly.** Build a small expert-annotated set (about 50 cases) and score MedGemma's insights the way medical-insight benchmarks do: recall, precision, F1 and novelty, plus a clinician's accuracy check. *Done when:* a scored report that says whether the insights are good enough to show patients.
6. **Check the clinical view is what a doctor needs.** Show it to a clinician and list the numbers they expected and did not find, and any they found misleading. *Done when:* the list is turned into changes or marked "not needed".

## Together

- **Order:** Uday's 1–3 (key, security, privacy decision) and Sindhu's 1 (clinical review) come first, because they decide whether the work can be shown to real patients. The rest can run alongside.
- **Before the client demo:** Sneha's slides and script (5), Tanusree's user test (1), and one full run-through of upload, review, Home, Outlook, the clinical view and the Architecture page.
- **Definition of done for everyone:** the change has a test or a written check, the full suite passes, and anything that touches patient data names who reviewed it.
