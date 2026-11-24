# What is still lacking (24 November 2026)

An honest list, grouped by how much it matters. "Built" means it exists and is tested; it does not mean it is clinically or legally ready.

## Must be done before any real patient uses it

| Gap | Why it matters | Owner (see TEAM_TASKS.md) |
|---|---|---|
| **No clinician has reviewed anything**: the risk model's parameters, directions and cut-offs, the wording, the 23 knowledge sources, the clinical view | Everything shown to a patient is unreviewed medical content | Sindhu, Sneha |
| **The risk model learned from synthetic practice records, and its answers are recorded diagnoses, not outcomes.** No external validation, no proof it ranks real people well | A class means "resembles people with the recorded condition", not "will develop it". Its accuracy figures are development checks only | Sindhu |
| **No privacy or legal assessment** (for Ontario: PHIPA and PIPEDA), no consent text, no retention or deletion policy, no data-processing agreement with the hosted AI service | Health records and uploaded documents are personal health information | Uday |
| **Document text goes to a hosted service (Nemotron second reader)** after identity removal that has only been tested on made-up documents | Needs an explicit decision, or switch it off | Uday |
| **No password recovery, no multi-factor sign-in, no delete-my-account or withdraw-consent** | A lost password locks a person out for good; people cannot leave | Uday |
| **Not served over HTTPS**; runs as a development server started by hand; PostgreSQL stops after a restart and must be started manually | Nothing here is deployable as it stands | Uday |

## Security and data protection gaps

- The document store is sealed, but the **key is a file** (`data/.docstore_key`) with no rotation and no managed backup. Losing it loses every stored document.
- The **values read from documents, the profiles and the audit log are stored unencrypted** in the main database. The original uploaded files are sealed; older ones saved before sealing are not.
- Administrators are named in an environment setting. There is no administrator management screen and no second factor for administrators.
- There is no way for a person to see who has looked at their documents (the audit log exists, but only the team can read it).
- Rate limits cover uploads and sign-ups; other new routes have not been load-tested.

## Reading documents

- **OCR is new and only tested on rendered pictures** (clean text, slight tilt, JPEG compression). Real phone photos with blur, shadows or skew are untested; handwriting is not read.
- The pattern reader and the AI second reader were measured on **made-up documents from a few layouts**. Real documents will be harder; the AI reader's 100% recall is on that test only.
- The AI second reader never reads age, sex or family history, and cannot work out BMI from a height and weight.
- Tables spanning pages, two-column reports, decimal commas, other languages and other date formats are untested.
- Values from several uploads are merged so the **newest wins**; the screen shows only the latest value, not how a value changed across documents. A person who uploads only documents has no Trends, Labs or Medicines pages.

## AI models

- **Nothing has been fine-tuned.** The dataset, scoring and training script exist (`finetune/`); there is no GPU to run them. Nemotron, a hosted free model, cannot be tuned.
- MedGemma's insights take minutes per person on this computer, so they are **pre-generated only for the sample record**. Everyone else waits when they press "Generate insights".
- The highlighting and the new "plain words, key words marked" prompt have not been seen on a freshly generated MedGemma answer yet, only on text written before.
- The medical insights and the plain-language text have **no accuracy measurement**; they are checked (numbers must come from the facts, no diagnosis wording) but not scored against expert answers.
- The knowledge base is public patient-education pages and WHO fact sheets, not clinical guidelines, and retrieval is keyword-based (no embeddings). Four sources could not be fetched (WHO anaemia, two CDC pages, an NIH vitamin D page).
- The free hosted model has rate limits: Home text can show "not available right now" when it is busy.

## Testing and quality

- **21 automated tests are skipped** (browser tests among them).
- The browser checks of the new screens (upload, review, clinical view, account, architecture, back links) were **run by hand-written scripts that are not in the repository**, so they will not run again by themselves.
- Accessibility was checked with an automated tool only. No screen-reader, keyboard-only or 200% zoom test by a person. Only the Edge browser was used: Firefox and Safari are untested. Phone layouts were checked on a few pages.
- No continuous integration, no performance test with many users or many documents, no pagination on long lists.
- English only.

## Documents and demo

- The 20-slide deck and the 10-minute script describe the **old** risk estimate and know nothing of uploads, review, the clinical view, the document store or the Architecture page.
- `PRESENTATION_TEAM_SPLIT.md` is out of date; `docs/TEAM_TASKS.md` replaces it.

## Housekeeping to do now

- Keys and tokens pasted into earlier chats (a Hugging Face token, OpenRouter and Gemini keys) should be revoked or rotated if not done. The local PostgreSQL password also appeared once in a command's output during this work; rotate it if that output is shared.
