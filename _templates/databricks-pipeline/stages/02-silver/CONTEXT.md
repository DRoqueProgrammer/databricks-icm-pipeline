# Stage 02: Silver

Take the Bronze notebook that landed in `stages/01-bronze/output/` and produce a Silver notebook that enforces the data contract: type coercion, dedup, null handling, quarantine invalid rows. The notebook writes both the cleaned Silver Delta table and a DQ report.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Previous stage | `../01-bronze/output/` | Most recent `{{DATASET_SLUG}}-bronze-notebook.py` | The Bronze notebook -- defines the Bronze Delta path to read from |
| Config | `_config/workspace.yaml` | Full file | Volume paths, partition column, catalog |
| Config | `_config/data-quality-rules.md` | "Silver layer" expectations | The rules Silver enforces |
| Config | `_config/conventions.md` | "Column naming", "Data types" | Target schema for type coercion |
| Shared | `../../shared/medallion-cheatsheet.md` | "Silver: The cleaned version" | Mental model |
| Shared | `../../shared/databricks-free-edition-gotchas.md` | Sections 1, 2, 5 (only as needed) | Free Edition traps when writing Delta |
| Shared | `../../shared/volume-paths.md` | "Layout" -- silver_cleansed and quarantine paths | Output paths |
| Reference | `references/silver-transforms.md` | Full file | Code patterns for the common transforms |
| Reference | `references/silver-output-and-report.md` | Full file | Write Silver Delta, DQ report, what Silver should NEVER do |
| Reference | `references/expectations.md` | Full file | GE expectation syntax (or Soda fallback) |

Do NOT load Bronze references or Gold/Report references.

## Process

1. Read the Bronze notebook in `../01-bronze/output/` to find the exact Bronze Delta path it writes to (look for the `bronze_path =` variable and the write call).
2. Read `_config/data-quality-rules.md` to confirm the dataset-specific overrides: primary keys, dedup keys, required columns, value ranges, FKs.
3. Read the Bronze Delta table. Get a sample (first 100 rows + summary stats: null counts per column, distinct counts, value distributions for low-cardinality columns).
4. **[Checkpoint 1]** -- Present the Bronze profile to the human. Confirm: target schema (column names + types) looks right? Dedup keys are right? Required columns are right? Any type quirks (e.g. "yes"/"no" booleans, comma decimals, leading-zero IDs)?
5. Author the Silver notebook in `output/{{DATASET_SLUG}}-silver-notebook.py`. The notebook must:
   - Read from the Bronze Delta path
   - Apply type coercion to the target schema from conventions.md
   - Deduplicate using `{{DEDUP_KEY_1}}`, `{{DEDUP_KEY_2}}` (keep first by `ingestion_date`)
   - Filter rows where required columns (`{{REQUIRED_COL_1}}`, `{{REQUIRED_COL_2}}`) are null, sending them to quarantine
   - Apply value range checks (e.g. `year BETWEEN 1900 AND 2100`)
   - Apply FK checks if configured
   - Write the surviving rows to `{{SILVER_VOLUME_PATH}}/{{DATASET_SLUG}}_clean` as Delta
   - Write the quarantined rows to `{{QUARANTINE_VOLUME_PATH}}/quarantine_{{DATASET_SLUG}}_{{silver_table}}` with `_dq_failure_reason`, `_dq_failure_value`, `_dq_check_time` columns
   - Write a DQ report to `output/{{DATASET_SLUG}}-dq-report.md` (counts, top failure reasons, sample bad rows)
6. **[Checkpoint 2]** -- Walk the human through the Silver notebook. Confirm: schema enforcement matches expectations? Dedup rule right? Quarantine thresholds right?
7. Run the audit checks below. If any fail, revise the notebook before declaring complete.
8. Save the notebook + DQ report to `output/`.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|------------|---------------|---------------|
| 3 | Bronze profile: row count, column count, null counts per column, distinct counts, value distributions for low-cardinality columns | Confirm target schema, dedup keys, required columns, value ranges |
| 5 | The finished Silver notebook, summarized cell by cell | Confirm schema, dedup, quarantine logic |

## Audit

| Check | Pass Condition |
|-------|---------------|
| Bronze to Silver row count | `silver_kept + silver_quarantined == bronze_count` (no rows lost) |
| Type coercion success rate | 100% of Silver rows match the target schema (else quarantine fired) |
| Dedup applied | Duplicate count from Bronze > 0 means dedup ran (if no dupes, dedup still ran, just nothing to do) |
| Required columns not null | 0 nulls in `{{REQUIRED_COL_1}}` and `{{REQUIRED_COL_2}}` in Silver |
| Quarantine table exists | A Delta table exists at `{{QUARANTINE_VOLUME_PATH}}/quarantine_{{DATASET_SLUG}}_*` if any rows were quarantined |
| DQ report exists | `output/{{DATASET_SLUG}}-dq-report.md` is non-empty and contains row counts |

If any check fails, revise the notebook and re-run the audit.

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Silver notebook | `output/{{DATASET_SLUG}}-silver-notebook.py` | Python notebook |
| DQ report | `output/{{DATASET_SLUG}}-dq-report.md` | Markdown summary: row counts, top failure reasons, sample bad rows |
| Silver Delta table | `{{SILVER_VOLUME_PATH}}/{{DATASET_SLUG}}_clean` | Delta table on Databricks (read-only from here) |
| Quarantine Delta table | `{{QUARANTINE_VOLUME_PATH}}/quarantine_{{DATASET_SLUG}}_clean` | Delta table with `_dq_failure_reason`, `_dq_failure_value`, `_dq_check_time` |

The Silver notebook + DQ report in `output/` are the human edit surface. Open them, adjust thresholds, change dedup keys, fix a type coercion. Stage 03 reads whatever is there.