# Conventions

The naming and structural rules every stage follows. Single source of truth. If a stage needs a new convention, add it here.

---

## Table naming

```
{catalog_name}.{layer_schema}.{dataset_slug}_{entity}_{grain}
```

Examples:
- `{{CATALOG_NAME}}.{{BRONZE_SCHEMA}}.ibge_sidra_population_raw`
- `{{CATALOG_NAME}}.{{SILVER_SCHEMA}}.ibge_sidra_population_clean`
- `{{CATALOG_NAME}}.{{GOLD_SCHEMA}}.ibge_sidra_population_by_state_year`

Rules:
- `{layer_schema}` is one of the three configured in `_config/workspace.yaml`
- `{entity}` matches the source concept (lowercase, singular or plural by convention)
- `{grain}` describes the row grain: `raw`, `clean`, `by_state_year`, `monthly`, etc.

## Column naming

- Snake_case always
- Booleans prefixed with `is_`, `has_`, or `should_`
- Timestamps end in `_at` (UTC, ISO 8601)
- Dates end in `_date`
- IDs end in `_id`
- Foreign keys match the referenced column name (e.g. `state_id` not `fk_state`)
- Ingest metadata columns are added in Bronze and preserved through Silver/Gold:
  - `ingestion_date` (date, partition key)
  - `source_file` (string, original filename)
  - `batch_id` (string, UUID per run)

## File format defaults

- Source: whatever the source provides (CSV, JSON, Parquet)
- Bronze to Silver: Delta (always)
- Silver to Gold: Delta (always)
- Quarantine: Delta (so we can audit invalid rows later)

## Partitioning

- Bronze: partitioned by `ingestion_date` (so we can drop old data efficiently)
- Silver: partitioned by the same date column the source uses if available; otherwise `ingestion_date`
- Gold: partitioned by the most common query dimension (e.g. `year` for yearly data, `state_id` for state-level)
- Never partition by a high-cardinality column (>10k distinct values)

## Optimization

- Silver: `OPTIMIZE` after the initial load and on a daily schedule (manual in Free Edition)
- Gold: `OPTIMIZE` + `ZORDER BY (most_queried_columns)` after the initial load
- Use `vacuum` only after confirming no time-travel queries need older versions

## Data types

| Source type | Spark type | Notes |
|-------------|------------|-------|
| int, bigint | `LongType` or `IntegerType` | match the source range |
| decimal, numeric | `DecimalType(precision, scale)` | never FloatType for money |
| float | `DoubleType` | only when loss is acceptable |
| bool | `BooleanType` | coerce "yes"/"no"/"1"/"0" in Silver |
| string | `StringType` | default |
| date | `DateType` | ISO `YYYY-MM-DD` |
| timestamp | `TimestampType` | UTC, ISO 8601 |
| json / struct | `StructType` from schema spec | in Bronze, store as `StringType` if schema unknown |

Bronze keeps source types as-is (schema-on-read). Silver enforces the target schema and quarantines rows that do not match.

## Notebook conventions

- One cell per logical step (load, transform, validate, write)
- `dbutils.widgets` for parameters at the top
- `display()` for human inspection at the end of each cell
- Magic command `%run` only for shared utility notebooks, not for cross-stage references
- Final cell: print a summary of row counts and any DQ failures

## Commit cadence

- One commit per stage (Bronze notebook, Silver notebook, etc.) is too granular
- One commit per logical pipeline run (Bronze + Silver + Gold + Report) is correct
- Commit message format: `[{{DATASET_SLUG}}] bronze+silver+gold+report`