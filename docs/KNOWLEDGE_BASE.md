# The medical knowledge base

A small, controlled set of approved documents the medical AI may cite. It starts **empty**: until you add documents, the AI is given no references and says so. Nothing is downloaded by the portal.

## How to add a document

1. Choose a document and **check its licence** and that your use is allowed. Some publishers need written permission. Write what you found in `license`.
2. Save its text yourself as a `.md` or `.txt` file (headings with `#`, paragraphs separated by a blank line) in `data/knowledge/`.
3. List it in `data/knowledge/manifest.yaml`. Copy `config/knowledge_manifest.example.yaml`, which has no real document in it.
4. A named person approves it in `approved_by`.
5. Run `python scripts/ingest_knowledge.py`. An entry that breaks a rule is rejected with the reasons; the others still run. `python scripts/ingest_knowledge.py --list` shows what is stored.

## Added since: more WHO sheets and MedlinePlus (23 sources, 386 passages)

Six more WHO fact sheets (healthy diet, tobacco, alcohol, salt reduction, polycystic ovary syndrome, noncommunicable diseases) with `scripts/fetch_who_factsheets.py`, and twelve MedlinePlus pages (cholesterol and its levels, triglycerides, HbA1c, blood glucose, high blood pressure, type 2 diabetes, prediabetes, PCOS, TSH, vitamin D, eGFR) with `scripts/fetch_medical_sources.py`. This closes the gaps listed below for cholesterol, vitamin D, thyroid, kidney and PCOS. Hosts `medlineplus.gov` and `nih.gov` were added to `config/knowledge_sources.yaml` (the host list still needs clinician and licence review). The WHO anaemia sheet and the CDC and NIH Office of Dietary Supplements pages could not be read (changed layout or refused), so they are not included. MedlinePlus pages are US-government patient-education pages: they explain what a topic or test is, not clinical thresholds. Approval is recorded as the project owner; **no clinician has reviewed them.**

## What was loaded first

Five public World Health Organization fact sheets (66 passages), saved by `scripts/fetch_who_factsheets.py` and ingested with `scripts/ingest_knowledge.py`:

| Source | Covers | Page date |
|---|---|---|
| Hypertension | blood pressure | 25 September 2025 |
| Diabetes | blood sugar, HbA1c | 11 November 2026 |
| Cardiovascular diseases (CVDs) | heart disease | 31 July 2025 |
| Obesity and overweight | weight, BMI | 7 October 2026 |
| Physical activity | steps, activity | 4 November 2026 |

- **Approval:** recorded as the project owner (Gavinnolla Tanusree Reddy). **No clinician has reviewed these sources.**
- **Licence:** WHO's copyright policy says WHO publications are CC BY-NC-SA 3.0 IGO (non-commercial, attribution, share-alike). These web fact sheets do not state their own licence on the page, so each manifest entry says so and the texts are for non-commercial project use only until WHO confirms. The saved text files are git-ignored; the manifest is kept.
- **Gaps:** a search for cholesterol or LDL, vitamin D and sleep finds nothing useful in these five sheets, so insights about those still say "no approved medical reference". These are general public-health fact sheets, not clinical guidelines, so they explain what a topic is but do not give the detailed thresholds a guideline would.
- **Rebuild:** `python scripts/fetch_who_factsheets.py --approved-by "Your Name"` then `python scripts/ingest_knowledge.py`.

## Rules (`config/knowledge_sources.yaml`)

The web address must be https on an allowed host. The proposed host list needs clinician and licence review and is not a statement that those sites are suitable. Dates must be valid, the licence and approver must be named, and a terminology standard needs a version. A changed file replaces the old one whole; an unchanged one is skipped.

| Type | Use |
|---|---|
| `guideline`, `government` | Clinical or public-health guidance: may be cited to explain a finding |
| `terminology` | ICD-11, SNOMED CT, LOINC: used only to explain what a term means, never as clinical guidance |

## Retrieval

Keyword ranking (BM25) always works. If you set `PRANA_EMBED_URL`, `PRANA_EMBED_KEY` and `PRANA_EMBED_MODEL` (an OpenAI-style embeddings endpoint), passages also get vectors and the two rankings are combined ("hybrid"). Without one it is keyword retrieval and says so. Only a query made of measure names with every number removed is ever sent to an embeddings endpoint. The AI may cite only references built from retrieved passages, and a check confirms any cited reference and quoted passage really exist in the stored source.

pgvector ships with the local PostgreSQL, but the SQLite fallback and CI cannot use it. For a few thousand passages, comparing vectors in Python is enough, so it was not added.

## Licences found by search (not legal advice)

- WHO publications after November 2016 are generally under CC BY-NC-SA 3.0 IGO (non-commercial, attribution, share-alike); some items such as ICD have different terms. Check each publication.
- SNOMED CT in Canada is licensed through Canada Health Infoway: an account and annual acceptance of its terms; use outside Canada needs notice. The agreement itself was not read.
- Diabetes Canada and Hypertension Canada carry copyright notices, and some text is published by journals (CMAJ, Canadian Journal of Diabetes). No clear reuse policy was found, so expect to need written permission.
- LOINC and ICD-11 terms were not checked.

## Limits

All passages are loaded into memory (fine for a few thousand). Chunking was tested on simple text: convert PDFs and tables to text first. Without an embeddings endpoint it is not semantic search.
