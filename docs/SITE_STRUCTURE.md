# Site structure: five places

The portal used to have twelve pages behind a "More" menu. It now has five places, the same for everyone, and everything else is a tab inside one of them or a page reached from a button.

| Place | Address | What is inside |
|---|---|---|
| Home | `#/` | Health at a glance (three risk classes), numbers worth knowing, what would help, what has changed, your care at a glance, most important right now, when to get help now |
| Trends and labs | `#/records/{trends,labs,medicines,history}` | Four tabs |
| Analytics and outlook | `#/insights/{outlook,analytics,help}` | Three tabs, and an **Open the clinical view** button that opens `#/clinical` (a page of its own, with a back link) |
| How it works | `#/how/{models,architecture,method,evidence}` | The models (job, why it matters, how it was checked, precision table), **Architecture** (flow diagrams: upload to risk class, where everything lives, who can open a document, how every AI answer is checked, how the best reader is chosen), how patterns are found, evidence and limits |
| Account | `#/account` | Your details (editable, each field shows where it came from), sign-in and security, your data (documents, download a copy, data quality, print), what we keep |

Two buttons in the top bar are not places: **Upload** (`#/upload`) and **Chat with Prana**.

People who registered and upload their own documents see four places (no Trends and labs, because one document has no time series).

Old addresses (`#/timeline`, `#/labs`, `#/medications`, `#/history`, `#/outlook`, `#/analytics`, `#/help`, `#/method`, `#/evidence`) still work and open the right tab, so bookmarks and chat answers do not break. `#/quality` opens from Account and keeps Account lit in the menu.

## Account details and where they are stored

Name, age, sex, blood group, height, allergies, family history, email, phone and emergency contact. Table `profiles` (one JSON row per person, no foreign key, because people from the training workbooks have no `accounts` row). A value the person enters wins over the record's value. Age and sex also feed the risk model (shown as "from your profile"). Edits are written to the audit log as field names only. Guests can look but not edit. `GET /api/export` returns everything held about the person as one file.

## Numbers on the How it works page

All come from files the project produced: `models/risk_model.json` (development check, AUC, 5-fold by person), `results/metrics.json` (pattern detection on planted patterns), `results/forecast_backtest.json`. For the two language models no accuracy was measured, and the page says so instead of showing a figure.

## Links and getting back

- Link text says where it goes or what it does ("Compare every measure in Labs", "Open the statistical findings", "Download a copy of my data"), never "click here" or a bare "see more". Links that leave the portal say so for screen readers.
- Pages reached from a button (Upload documents, Statistical findings, Data quality) start with **← Back to <the page you came from>**, for example "Back to Analytics and outlook: Analytics and intelligence". Opened directly, they fall back to a sensible parent.
- The browser's Back button returns to the same place on the page you left. A redraw of the page you are on (when the AI text arrives) no longer jumps you to the top. Moving to a new page puts keyboard and screen-reader focus on its heading.
- After an upload: See your updated risk classes on Home, Read the reasons in Outlook, or Add another document.

## Clinical view (`#/clinical/...`, reached from a button, not the menu)

For a doctor: **Statistical findings** (moved here from its own page), **Values and tables** (baseline comparison, trend tests, reference ranges with sources, every laboratory result, projections), **Risk model detail** (every value the model used, where it came from, each value's share of the push, never the score), **Documents and extracted values** (upload and check times, original and corrected values, the change history), **Medicines and adherence**, and **Data quality**. "Print for the clinic" prints the open tab. `#/statistics` and `#/quality` still work and open the right tab.

## Review a document (`#/review/<id>`)

Shown right after every upload. Each value read from the document, with the line it came from, can be corrected or set aside (only the values: never the text, the file's details or the times). Values read by the AI second reader are marked. See `docs/ARCHITECTURE_UPLOAD.md`.
