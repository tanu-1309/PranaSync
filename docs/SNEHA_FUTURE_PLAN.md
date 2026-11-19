# Sneha: technical plan for the next deliverables (data, database, documentation)

Starting point (already in `src/prana/data/db.py`, SQLAlchemy 2.0 Core, PostgreSQL 16, SQLite fallback for tests):

| Table | Key | Purpose |
|---|---|---|
| `patients` | `patient_id` | age, sex, family history, data-quality JSON |
| `timeline` | `patient_id`, `date`, `signal` (indexed) | long-format measurements: `source`, `signal`, `value`, `unit`, `text` |
| `findings` | `patient_id` + `scenario` | per-scenario result: `surfaced`, `linked_context`, `n_signals`, `evidence` (JSONB) |
| `users` | `patient_id` | scrypt `pw_hash` |
| `records` | `patient_id` | the portal package (JSONB) plus `version`; rebuilt when `PAYLOAD_VERSION` (now 4) changes |
| `audit_log` | `id` | `ts`, `patient_id`, `event`, `detail` (JSONB) |
| `narratives` | `patient_id` | AI text (JSONB), `facts_hash`, `model` (AI version only) |

---

## Deliverable 1 (Fri 14 Nov): data dictionary and ER diagram

**Output:** `docs/DATA_DICTIONARY.md` and `docs/er_diagram.png` (or a Mermaid block in the same file).

**Steps**
1. Generate the dictionary from the live schema, so it cannot drift from the code. Write `scripts/make_data_dictionary.py` using `sqlalchemy.inspect(engine)` to list each table, column, type, nullability, key and index, and write them as Markdown tables.
2. Add by hand, per column: meaning, unit, allowed values, who writes it, and who reads it (for example `timeline.signal` is written by `loader.py` and read by `timeline.py`).
3. Document the signal vocabulary: list the distinct values of `timeline.signal` and `timeline.source` (`SELECT signal, source, COUNT(*), MIN(date), MAX(date) ... GROUP BY 1,2`) with units and the reference range source (`config/reference_ranges.yaml`).
4. Document the lifecycle: load workbook, `save_patient`, pipeline, `save_findings`, `save_record`, with the `PAYLOAD_VERSION` rule (bump the number when the package shape changes, and stale records are rebuilt on demand).
5. Draw the ER diagram: `patients` 1–N `timeline`, 1–N `findings`, 1–1 `users`, 1–1 `records`, 1–1 `narratives`, and `audit_log` as a soft reference (no foreign key, so audit rows survive deletion).
6. Add a "data protection" section: what is personal data, where the password hash lives, what is sent to the AI provider (the facts, not the identifier), retention, and the delete path (`ON DELETE CASCADE` from `patients`).

**Done when:** the script runs in CI, the generated tables match the code, and a teammate can find any column's meaning in under a minute.

---

## Deliverable 2 (Wed 26 Nov): storing data the patient adds (missing data)

Context: `src/prana/insight/missing_data.py` already works out what is missing (`missing_for_scenario` returns `item`, `key`, `reason`). The next step is to let a patient supply it and to re-run the analysis. Tanusree builds the screen; Uday exposes the endpoint; Sneha owns storage.

**Design**
1. New table `patient_inputs`: `id` (PK), `patient_id` (FK, `ON DELETE CASCADE`), `key` (the same `key` as in `wanted_data`), `date`, `value` (Float), `unit`, `source` (always `patient`), `created_at`, `status` (`active` or `superseded`). Indexes: `(patient_id, key, date)`.
2. Keep patient-entered data apart from the original record. The timeline view the pipeline reads becomes `timeline UNION ALL patient_inputs` (a SQL view `timeline_all`), so the real workbook is never overwritten and a user can undo an entry.
3. Validation at the data layer: a value must be inside a plausible range per `key` (read from `config/reference_ranges.yaml`, with hard limits, e.g. HbA1c 3–20), a date cannot be in the future, and a unit must be one we know. Reject, do not clamp.
4. Re-run: `save_patient_input()` writes the row, then deletes the patient's `records` row (or bumps a per-patient `input_version`), so the next read rebuilds the package. In the AI version the `narratives.facts_hash` changes with the facts, so the text is rewritten automatically.
5. Audit: every insert, edit and undo writes `audit_log` (`event = "input_added"`, with the key and not the value).
6. Migration: add `scripts/migrate_add_patient_inputs.py` (idempotent `CREATE TABLE IF NOT EXISTS`), because `init_db()` only creates missing tables.

**Tests (`tests/test_db.py`):** insert, range rejection, future date rejection, undo, the view merges the two sources, the package is rebuilt after an insert, and cascade delete removes the inputs. Run on SQLite and PostgreSQL.

**Done when:** a value added through the API appears in the next analysis, and removing it restores the original result.

---

## Smaller items that help the whole team

- **Indexes and speed:** run `EXPLAIN ANALYZE` on the two hot queries (`read_timeline`, `get_record`), and record the load time for 900 patients in `docs/VALIDATION.md`.
- **Backups and reset:** a documented `pg_dump` / restore command in `docs/RUN_GUIDE.md`, and a note on how to reset the dev database safely.
- **Consistency check:** a script that compares row counts for `patients`, `timeline`, `records` and `users` (`db.counts()` already exists) and fails if they disagree.
- **Documentation sweep:** keep `README.md`, `docs/ARCHITECTURE.md` and `docs/RUN_GUIDE.md` in step with every schema change in the same commit.

## Order of work and dependencies
1. Fri 14 Nov: dictionary and diagram (no dependencies).
2. Mon 17 – Fri 21 Nov: speed notes, backup notes, consistency script.
3. Mon 24 – Wed 26 Nov: `patient_inputs`, the view, validation, tests. Agree the field names and endpoint shape with Tanusree and Uday by Fri 21 Nov.

## Honest limits to say out loud
- Patient-entered values are unverified, so they should be labelled in the analysis and not mixed in silently.
- The data is practice data. Real patient data needs consent, encryption at rest, and a retention policy first.
