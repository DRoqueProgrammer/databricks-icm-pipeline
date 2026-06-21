# Stage 03: Gold

Take the Silver Delta table that landed in `stages/02-silver/output/` and produce a Gold notebook that builds business aggregates: KPIs, dimensions, denormalized joins. Gold is what dashboards query.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Previous stage | `../02-silver/output/` | Most recent `ibge-sidra-population-silver-notebook.py` and `ibge-sidra-population-dq-report.md` | Silver schema and DQ caveats |
| Config | `_config/workspace.yaml` | Full file | Gold Volume paths |
| Config | `_config/conventions.md` | "Optimization" and "Table naming" | Z-order columns, Gold naming |
| Shared | `../../shared/medallion-cheatsheet.md` | "Gold: The business questions" | Mental model |
| Shared | `../../shared/databricks-free-edition-gotchas.md` | Section 1 only (path trap) | Path conventions |
| Shared | `../../shared/volume-paths.md` | "Layout" -- gold_aggregates path | Output path |
| Reference | `references/gold-aggregates.md` | Full file | Aggregate patterns, Z-order, column comments |

Do NOT load Bronze references or Silver references (Silver's data-quality-rules.md is already baked into Silver's output).

## Process

1. Read the Silver notebook in `../02-silver/output/` to find the Silver Delta path (look for `silver_path =`).
2. Read the DQ report (`ibge-sidra-population-dq-report.md`). Note the row counts and quarantine reasons -- if many rows were quarantined for a specific reason, you may want to flag that in the Gold report.
3. Read the Silver Delta table. Understand the grain, the dimensions, and the measures.
4. **[Checkpoint 1]** -- Propose the Gold aggregates to the human. For each, give: name, grain, dimensions, measures, intended use case. Examples: `by_state_year` (one row per state-year), `top_states_overall` (ranked), `yearly_summary` (one row per year). Confirm which ones to build.
5. Author the Gold notebook in `output/ibge-sidra-population-gold-notebook.py`. The notebook must:
   - Read the Silver Delta table
   - Build each confirmed aggregate as a separate Spark DataFrame
   - Add column comments using `ALTER TABLE ... ALTER COLUMN ... COMMENT '...'` (or via the table creation DDL)
   - Z-order the most-queried columns per aggregate
   - Write each aggregate to `dbfs:/Volumes/ibge/ibge_sidra_population_gold/aggregates/{aggregate_name}` as Delta
   - Print row counts and sample rows for each aggregate
6. **[Checkpoint 2]** -- Walk the human through the Gold notebook. Confirm: aggregates match the questions to answer? Column comments are accurate? Z-order columns are the right ones?
7. Run the audit checks below.
8. Save the notebook to `output/`.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|------------|---------------|---------------|
| 3 | Silver schema summary: column names + types, grain, sample rows, distinct count of grain keys | Confirm aggregates are useful, choose which to build |
| 5 | The finished Gold notebook, summarized cell by cell | Confirm aggregates, column comments, Z-order |

## Audit

| Check | Pass Condition |
|-------|---------------|
| Aggregate grain matches dimensions | Row count of aggregate == distinct count of group-by keys (no accidental dedup or fanout) |
| No null in dimension columns | 0% nulls in dimensions used as group-by keys |
| Column comments populated | Every column has a comment (lineage back to Silver) |
| Z-order applied | Each Gold table has `OPTIMIZE ... ZORDER BY` for the right columns |
| Output paths use `dbfs:/` | Each write path starts with `dbfs:/Volumes/...` |
| Format is Delta | All Gold tables are Delta |

If any check fails, revise the notebook and re-run.

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Gold notebook | `output/ibge-sidra-population-gold-notebook.py` | Python notebook with one cell per aggregate |
| Gold Delta tables | `dbfs:/Volumes/ibge/ibge_sidra_population_gold/aggregates/{aggregate_name}` | One Delta table per confirmed aggregate |

The Gold notebook in `output/` is the human edit surface. Add an aggregate, change a measure, switch a Z-order column. The Report stage reads whatever is there.