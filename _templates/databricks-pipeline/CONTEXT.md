# Databricks Pipeline Workspace

This workspace runs a four-stage medallion pipeline on Databricks Free Edition: raw ingest (Bronze), cleansed (Silver), aggregated (Gold), and a markdown report. Each stage is a separate folder with its own CONTEXT.md and produces an editable output that the next stage reads.

## Task Routing

| Task Type | Go To | Description |
|-----------|-------|-------------|
| I have raw data and want Bronze notebooks | `stages/01-bronze/CONTEXT.md` | Schema-on-read ingest into a Volume; preserves lineage; minimal transformation |
| I have Bronze and need Silver | `stages/02-silver/CONTEXT.md` | Type coercion, dedup, null handling, quarantine invalid rows; Great Expectations checks |
| I have Silver and need Gold | `stages/03-gold/CONTEXT.md` | Business aggregates, KPIs, dimensions; Z-order optimization; column comments |
| I want a final report from Bronze/Silver/Gold | `stages/04-report/CONTEXT.md` | Row counts, top issues, schema diff, suggestions for next iteration |
| I need to configure this workspace for the first time | `setup/questionnaire.md` | Asks for workspace URL, catalog, volume paths, cluster |

## Shared Resources

| Resource | Location | Contains |
|----------|----------|----------|
| Medallion cheatsheet | `shared/medallion-cheatsheet.md` | What each layer is for, common mistakes, when to stop |
| Free Edition gotchas | `shared/databricks-free-edition-gotchas.md` | `dbfs:/` prefix, no CREATE OR REPLACE, Repos UI cache bug, CLI v1.3.0 EOF trap |
| Volume paths | `shared/volume-paths.md` | Canonical Volume URIs per layer (Bronze/Silver/Gold) |
| Workspace config | `_config/workspace.yaml` | Catalog, schema, cluster ID, default file format |
| Naming conventions | `_config/conventions.md` | Table naming, partition columns, file format defaults |
| Data quality rules | `_config/data-quality-rules.md` | Per-layer GE expectations and quarantine thresholds |
| Free Edition skill | `skills/databricks-free-edition/SKILL.md` | Operational knowledge for Free Edition traps |

## Stage Outputs (after a run completes)

| Stage | Output | Consumed By |
|-------|--------|-------------|
| 01-bronze | `stages/01-bronze/output/{{DATASET_SLUG}}-bronze-notebook.py` | Stage 02 reads it as the source of truth for what landed in Bronze |
| 02-silver | `stages/02-silver/output/{{DATASET_SLUG}}-silver-notebook.py` + `{{DATASET_SLUG}}-dq-report.md` | Stage 03 reads the notebook; DQ report goes to Stage 04 |
| 03-gold | `stages/03-gold/output/{{DATASET_SLUG}}-gold-notebook.py` | Stage 04 reads the Gold schema and row counts |
| 04-report | `stages/04-report/output/{{DATASET_SLUG}}-report.md` | Human reads, edits, shares with stakeholders |