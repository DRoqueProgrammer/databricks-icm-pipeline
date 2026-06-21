# Silver Output and Reporting

Companion to `silver-transforms.md`. Covers the final write of Silver Delta, the quarantine table, the DQ report, and operational pitfalls.

## 7. Write outputs

```python
# Silver kept rows
silver_path = "{{SILVER_VOLUME_PATH}}/{{DATASET_SLUG}}_clean"
(
    df_kept.write
    .format("delta")
    .mode("overwrite")  # Silver is fully rebuilt from Bronze on each run
    .partitionBy("{{PARTITION_BY_DEFAULT}}")
    .save(silver_path)
)

# Quarantine
quarantine_path = f"{{QUARANTINE_VOLUME_PATH}}/quarantine_{{DATASET_SLUG}}_clean"
(
    df_quarantined_final.write
    .format("delta")
    .mode("append")  # accumulate quarantine history
    .partitionBy("_dq_check_time")
    .save(quarantine_path)
)
```

`mode("overwrite")` on Silver is correct: Silver is rebuilt from Bronze on each run. Quarantine uses `mode("append")` so we accumulate the history of invalid rows.

## 8. Write the DQ report

The DQ report is a markdown summary. It goes in `output/{{DATASET_SLUG}}-dq-report.md`:

```python
bronze_count = df_bronze.count()
silver_count = df_kept.count()
quarantine_count = df_quarantined_final.count()

# Top failure reasons
top_reasons = df_quarantined_final.groupBy("_dq_failure_reason").count().orderBy(F.desc("count")).limit(10).collect()

dq_report = f"""# Silver DQ Report: {{DATASET_DISPLAY_NAME}}

**Run timestamp**: {F.current_timestamp()}
**Batch ID**: {batch_id}

## Row counts

| Stage | Count |
|-------|-------|
| Bronze (input) | {bronze_count:,} |
| Silver (kept) | {silver_count:,} |
| Silver (quarantined) | {quarantine_count:,} |
| Total (kept + quarantined) | {silver_count + quarantine_count:,} |

## Top failure reasons

| Failure reason | Rows |
|----------------|------|
""" + "
".join([f"| {row['_dq_failure_reason']} | {row['count']:,} |" for row in top_reasons])

# Write to output/
dbutils.fs.put("file:///Workspace/.../stages/02-silver/output/{{DATASET_SLUG}}-dq-report.md", dq_report, overwrite=True)
```

## Pitfalls

- **Dedup before FK checks**: the FK reference table only has unique keys; if you check FKs before dedup, the FK check sees the same duplicate row multiple times
- **Don't `.collect()` on the full DF**: use `count()`, `show()`, or sample before bringing data to the driver
- **`unionByName(allowMissingColumns=True)`**: when combining DataFrames that may not have all the same columns (kept vs quarantined have different schemas)
- **Quarantine rows preserve lineage**: keep `ingestion_date`, `source_file`, `batch_id` from Bronze so quarantine rows can be traced back
- **Databricks Free Edition**: use `dbfs:/Volumes/...` paths everywhere; see `shared/databricks-free-edition-gotchas.md` #1

## What Silver should NEVER do

- Aggregate
- Join with Gold tables (Gold depends on Silver, never the other way)
- Drop the ingest metadata columns (Bronze lineage is preserved through Silver)
- Silently coerce nulls to defaults (quarantine them instead, with a clear reason)
