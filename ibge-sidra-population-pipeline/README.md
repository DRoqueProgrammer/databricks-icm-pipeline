# Databricks Pipeline (ICM Workspace Template)

A four-stage medallion pipeline orchestrated by folder structure, following the [Interpretable Context Methodology](https://github.com/RinDig/Interpreted-Context-Methdology).

## What this is

Replace Airflow + dbt + a notebook framework with a single agent that reads the right markdown file at each step. Files in well-named folders tell the agent what to do; the agent writes notebooks and reports into `output/`; the next stage reads them.

## What you get

- **Bronze**: raw ingest into a Unity Catalog Volume, schema-on-read, full lineage preserved
- **Silver**: cleansing, dedup, type coercion, quarantine invalid rows, Great Expectations checks
- **Gold**: business aggregates (KPIs, dimensions), Z-order optimization, column comments
- **Report**: a markdown report with row counts, top data quality issues, and next-step suggestions

## How to use it

This is a **template**. Duplicate it per dataset.

```bash
cp -r ~/workspaces/_templates/databricks-pipeline ~/workspaces/ibge-sidra-pipeline
cd ~/workspaces/ibge-sidra-pipeline
```

Then open the new folder in your editor and run `setup`. The agent asks for:

- Databricks workspace URL
- Catalog name
- Volume paths for Bronze/Silver/Gold
- Cluster ID or "use serverless"
- Default file format (Delta is recommended)

After setup, run the pipeline:

1. Say *"Ingest the dataset at `<path>` and produce Bronze"*
2. Agent reads `stages/01-bronze/CONTEXT.md`, loads only what it needs, writes a notebook to `stages/01-bronze/output/`
3. Review the notebook in VSCode or Databricks. Edit if needed.
4. Say *"Run Silver"*. Agent reads Bronze output + Silver CONTEXT, produces Silver notebook + DQ report.
5. Continue through Gold and Report.

You can stop after any stage. The output folder is yours to edit.

## Why ICM for Databricks

- **Layered context loading**: each stage loads 2-8k tokens instead of dumping the whole workspace
- **Edit surfaces between stages**: you review the Bronze notebook before Silver runs; you fix the schema mapping before Gold consumes it
- **Reference docs are canonical**: if we figure out the right way to dedup, that knowledge goes in `references/silver-transforms.md`, not in every Silver notebook
- **No state machine**: just files in `output/` folders

## See also

- `CLAUDE.md` -- full folder map and routing
- `CONTEXT.md` -- task routing table
- `_core/CONVENTIONS.md` (in the ICM repo) -- the patterns this template follows
- `shared/databricks-free-edition-gotchas.md` -- the operational quirks baked into every stage