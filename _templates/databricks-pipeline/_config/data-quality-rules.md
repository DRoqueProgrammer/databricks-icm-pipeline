# Data Quality Rules

The Great Expectations (or Soda) rules applied at each layer. Per ICM pattern, these are stable across runs -- they describe what "good" means for this dataset, regardless of the specific ingest batch.

When `setup` runs, fill in the dataset-specific columns. The thresholds below are defaults and can be tuned per dataset.

---

## Layer expectations

### Bronze layer

Bronze is raw. The only rule at this layer is "did the file land and can we read it?"

| Check | Threshold | Action on failure |
|-------|-----------|-------------------|
| File is non-empty | size > 0 bytes | abort the stage, alert user |
| File is readable by Spark | no parsing exceptions | log the exception, abort |
| Ingest metadata populated | `ingestion_date`, `source_file`, `batch_id` present on every row | abort (cannot trace lineage) |

Bronze does NOT validate column values, types, or uniqueness. That is Silver's job.

### Silver layer

Silver enforces the contract. Every row that survives to Silver meets these rules. Rows that fail are quarantined with their failure reason.

| Check | Default threshold | Quarantine behavior |
|-------|-------------------|---------------------|
| Required columns non-null | 0% nulls in PK columns, <2% in others | quarantine the offending row |
| Schema match | 100% of columns present, types match the target schema | quarantine if a column is missing in a way the target schema cannot fill |
| Type coercion success | 100% of rows coerce cleanly | quarantine rows with unparseable values |
| Duplicate detection | 0 duplicates on the configured `dedup_keys` | keep first occurrence (by `ingestion_date`), quarantine the rest |
| Value range | values fall within documented domain (e.g. year 1900-2100) | quarantine |
| Referential integrity | if FK is configured, value exists in referenced table | quarantine |

Tune the thresholds in `setup/questionnaire.md` per dataset.

### Gold layer

Gold assumes Silver is clean. The rules at this layer are about aggregate correctness, not row-level.

| Check | Default threshold | Action on failure |
|-------|-------------------|-------------------|
| Aggregation matches source | row count of aggregate equals distinct count of underlying group-by keys | abort, alert (data model bug) |
| No NULL in dimension columns | 0% nulls in dimensions used as group-by keys | abort (likely upstream bug) |
| Date continuity | if time series, no unexpected gaps (configurable) | report in the markdown report, do not abort |

---

## Quarantine handling

Rows that fail Silver checks land in `{{QUARANTINE_VOLUME_PATH}}` as a Delta table named:

```
{{CATALOG_NAME}}.{{SILVER_SCHEMA}}.quarantine_{dataset_slug}_{silver_table_name}
```

The quarantine table has the original columns plus two metadata columns:
- `_dq_failure_reason` (string): which rule failed
- `_dq_failure_value` (string): the offending value
- `_dq_check_time` (timestamp): when the check ran

Quarantine rows are NOT lost. They are reviewed in Stage 04 (Report).

## Per-dataset overrides

After `setup`, the dataset-specific DQ rules land in this file, replacing the `{{}}` placeholders:

```yaml
dataset:
  slug: "{{DATASET_SLUG}}"
  primary_keys: ["{{PK_COLUMN_1}}", "{{PK_COLUMN_2}}"]   # composite if needed
  dedup_keys: ["{{DEDUP_KEY_1}}", "{{DEDUP_KEY_2}}"]
  required_columns:
    - "{{REQUIRED_COL_1}}"
    - "{{REQUIRED_COL_2}}"
  value_ranges:
    "{{RANGE_COLUMN}}": "{{VALID_VALUES_OR_RANGE}}"
  foreign_keys:
    "{{FK_COLUMN}}": "{{REFERENCED_TABLE}}"
```

If a dataset has no required column overrides, the defaults above apply.