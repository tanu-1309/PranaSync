# Uploading and reading a document: how it works

The same flow is drawn on the portal's **How it works → Architecture** tab.

```
You choose a file
  → safety checks (type, 10 MB, 40 PDF pages, zip bombs, duplicate, 15 per minute, signed in, not a guest)
  → read the text (PDF, Word, text, CSV, Excel)           photos and scanned PDFs: on-device OCR (src/prana/risk/ocr.py, RapidOCR), every value marked 'read from an image'
  → pattern reader (src/prana/risk/extract.py)             21 kinds of value, units converted, impossible values dropped, source line kept
  → optional Nemotron second reader (extract_ai.py)        only adds values it can prove; identity removed first; marked "read by AI"
  → you review (web/js/review.js)                          correct or set aside a value; the text and file details cannot be changed
  → saved
       document store   data/documents.db, one sealed JSON document per upload (src/prana/data/docstore.py)
       main database    the values, each tied to its document (observations)
       file on disk     data/uploads/<person>/<id>.<ext>, sealed
  → risk model → Home, Outlook, Clinical view
```

## Photos and scans

PNG, JPG, TIFF, BMP and WEBP pictures, and PDFs that contain only page images, are read by RapidOCR running on this computer (nothing is sent anywhere). OCR text is rebuilt into lines (pieces on the same row, left to right) and matched with a tolerant version of the name patterns, because OCR often drops spaces ("Totalcholesterol"). Up to 6 scanned pages and 25 megapixels. Every value is marked **Read from an image: please check** on the review page. Install with `pip install rapidocr-onnxruntime pypdfium2`; without them pictures are refused with a clear message. Measured only on rendered test pictures: real phone photos (blur, shadows, skew) will be harder.

## The document store

A database of its own (`DOCSTORE_URL`, default `sqlite:///data/documents.db`), apart from the main database. One row per upload, with plain id, owner, times and status, and the **JSON document sealed** (AES-256-GCM, a key per person derived with HKDF from a server key in `data/.docstore_key` or `PRANA_DOCSTORE_KEY`; the owner and document id are bound into the seal). The JSON holds the file's name, size, type and fingerprint, `uploaded_at`, `extracted_at`, `reviewed_at`, the extracted text, every value with its original reading and any correction, the correction history and which reader read it.

**Who can open it:** the signed-in owner, or an administrator (IDs in `PRANA_ADMIN_IDS`) who can read but never change; every administrator read and refusal is in the audit log. Anyone else gets "not found". Losing the key makes the stored documents unreadable: back it up with the database. The values in the main database and the audit log are not sealed.

## Which reader is best

`python scripts/eval_extraction.py` scores the readers on made-up documents with known answers: recall, precision, F1 and **invented values** (must be zero). Last run (40 documents per kind, `results/extraction_eval.json`):

| | Recall | Precision | F1 | Invented |
|---|---|---|---|---|
| Pattern reader, easy layouts | 100% | 100% | 1.00 | 0 |
| Pattern reader, unusual layouts | 48% | 100% | 0.65 | 0 |
| Pattern reader + Nemotron, unusual layouts | 100% | 100% | 1.00 | 0 |

Nemotron answered in about 5 seconds per document (slowest 16 s), with no failed calls. **Read this with care:** the documents are made up from a small set of layouts, so real documents will be harder; the second reader is therefore only ever an addition, every value it adds must be on a real line of the document, and the review page shows it as "read by AI: please check".

## Privacy of the second reader

Document text goes to a hosted model, so first only lines containing a digit are kept, lines that look like a name, birth date, address, phone, email or ID are dropped, and long digit strings are masked. Switch it off with `PRANA_EXTRACT_AI=0` in `.env`. It is on only if `PRANA_EXTRACT_AI=1` and the model is configured.
