# Stage 01: Bronze

Take a raw data source and produce a Bronze notebook that ingests it into the Bronze Volume with full lineage preserved. Bronze is schema-on-read; the only transformations are metadata additions.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| User | (conversation) | Source path (local, URL, or Volume path) + format | The raw data to ingest |
| Config | `_config/workspace.yaml` | Full file | Catalog, Volume paths, partition column, ingest metadata column names |
| Config | `_config/conventions.md` | "Table naming", "Column naming", "File format defaults" | Naming rules |
| Shared | `../../shared/medallion-cheatsheet.md` | "Bronze: The vault" | Mental model for what Bronze is |
| Shared | `../../shared/databricks-free-edition-gotchas.md` | "Read this first" -- sections 1, 2, 5, 6 (only the Free Edition traps likely to hit during ingest) | Free Edition traps |
| Shared | `../../shared/volume-paths.md` | "Layout" + "Volume creation" | Where Bronze lands |
| Reference | `references/bronze-ingest-patterns.md` | Full file | Code patterns for common sources |
| Reference | `references/bronze-pitfalls.md` | Full file | Common pitfalls and what Bronze should NEVER do |
| Reference | `references/notebook-template.py` | Full file | Starting skeleton for the notebook |

Do NOT load Silver/Gold/Report references at this stage. They are not relevant to raw ingest.

## Process

1. Collect per-run details conversationally from the user: the source path (URL, dbfs path, or local file uploaded to Volume), the source format (csv/json/parquet/xlsx), and any source-specific options (delimiter, encoding, header row).
2. Read the source's structure (head 20 rows for CSV/JSON; metadata for Parquet; sheet names for xlsx). Use `pandas` for xlsx; `spark.read` with the appropriate format for everything else.
3. **[Checkpoint 1]** -- Present the source preview to the human. Confirm: column names look right? Header row correct? Delimiter right? Any columns to drop before ingest (e.g. source-internal row numbers)?
4. Author the Bronze notebook in `output/ibge-sidra-population-bronze-notebook.py` using the template from `references/notebook-template.py`. The notebook must:
   - Read the source with `spark.read.format(...)` or the `dbutils.fs.put` pattern for xlsx
   - Add `ingestion_date` (current date), `source_file` (original filename), `batch_id` (UUID)
   - Partition by `ingestion_date` (default `ingestion_date`)
   - Write to `dbfs:/Volumes/ibge/ibge_sidra_population_bronze/raw/ibge-sidra-population` as Delta, mode `append`
   - Print row counts at the end
5. **[Checkpoint 2]** -- Walk the human through the notebook. Confirm: ingest metadata columns present? Partition column right? Output path matches `shared/volume-paths.md`?
6. Run the audit checks below. If any fail, revise the notebook before declaring the stage complete.
7. Save the notebook to `output/`. Optionally upload it to Databricks via `databricks workspace import` (CLI), but the file in `output/` is the canonical artifact.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|------------|---------------|---------------|
| 2 | Source preview: column names, types, sample rows, total row count estimate | Confirm structure is what they expect, choose to drop columns or adjust parsing |
| 4 | The finished notebook, summarized cell by cell | Confirm metadata columns, partition, output path |

## Audit

| Check | Pass Condition |
|-------|---------------|
| Ingest metadata present | `ingestion_date`, `source_file`, `batch_id` columns exist on the output DataFrame |
| No source-level transformations | Output row count equals input row count (no filtering, no aggregation) |
| Partition column present | The DataFrame has the column specified in `ingestion_date` |
| Output path uses `dbfs:/` prefix | The write path starts with `dbfs:/Volumes/...`, not `/Volumes/...` |
| Format is Delta downstream | The output is `format("delta")` even if the source was CSV/JSON |
| Source lineage recorded | A separate manifest row written to `dbfs:/Volumes/ibge/ibge_sidra_population_bronze/raw/_manifest/` with source path, row count, batch_id, ingestion_date |

If any check fails, revise the notebook and re-run the audit. Do not save a failing notebook.

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Bronze notebook | `output/ibge-sidra-population-bronze-notebook.py` | Python notebook (.py) with cell delimiters (`# COMMAND ----------`) |
| Optional manifest | `output/ibge-sidra-population-bronze-manifest.json` | One JSON object per ingested file: source path, row count, batch_id, timestamp |

The notebook in `output/` is the human edit surface. Open it in Databricks or VSCode, adjust the column list, change the partition, add a derived column. Stage 02 reads whatever is in that file.