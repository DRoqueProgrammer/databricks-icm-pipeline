# Bronze Pitfalls and Constraints

Companion to `bronze-ingest-patterns.md`. Read after the code patterns.

## Common pitfalls

- **Multi-line CSVs**: enable `multiLine=true` and explicit `quote`/`escape` options
- **Mixed encodings**: read with `.option("encoding", "UTF-8")` or `"ISO-8859-1"` (common in Brazilian government data)
- **Header rows in unexpected places**: detect dynamically as in the xlsx pattern
- **Source paths with spaces**: use raw strings or escape; avoid if possible
- **Files larger than the driver's memory**: rely on Spark's distributed read; do not call `.collect()` or `.toPandas()` on the full DF
- **Databricks Free Edition CSV path**: always use `dbfs:/Volumes/...`, never `/Volumes/...` -- see shared/databricks-free-edition-gotchas.md #1

## What Bronze should NEVER do

- Filter rows
- Rename columns
- Aggregate
- Coerce types
- Join with other tables

Those are Silver and Gold's jobs. Bronze preserves the source bytes.
