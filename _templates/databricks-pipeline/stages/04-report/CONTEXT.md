# Stage 04: Report

Take everything that landed in `stages/01-bronze/output/`, `stages/02-silver/output/`, and `stages/03-gold/output/`, and produce a markdown report summarizing the pipeline run. The report is for humans -- stakeholders, the next analyst, your future self.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Previous stages | `../01-bronze/output/`, `../02-silver/output/`, `../03-gold/output/` | All `.md` files and `.py` notebooks | Row counts, schema, DQ results, aggregate metadata |
| Config | `_config/workspace.yaml` | Full file | Dataset identity, paths, run timestamp |
| Reference | `references/report-template.md` | Full file | The template structure |

Do NOT load any other references. The report is purely summarization.

## Process

1. Read the row counts from each stage's output (Bronze notebook has a print summary, Silver DQ report has counts, Gold notebook has aggregate row counts).
2. Read the DQ report from Silver (`{{DATASET_SLUG}}-dq-report.md`) to extract failure reasons.
3. Read the Gold notebook to enumerate the aggregates built.
4. **[Checkpoint]** -- Present a draft outline of the report to the human. Confirm: which sections to include? Any executive summary? Any specific questions to answer?
5. Author the report in `output/{{DATASET_SLUG}}-report.md` following `references/report-template.md`. Sections:
   - Executive summary (3-5 lines)
   - Pipeline run summary (row counts at each layer)
   - Data quality findings (from the DQ report)
   - Gold aggregates produced (with grain and sample query)
   - Top issues and recommendations
   - Appendix: paths, links, batch ID
6. Run the audit checks below.
7. Save the report to `output/`.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|------------|---------------|---------------|
| 3 | Draft outline: section headers + one-line description of each | Confirm sections, any executive summary needed, any specific questions to answer |

## Audit

| Check | Pass Condition |
|-------|---------------|
| Row counts present | Bronze, Silver (kept), Silver (quarantined), each Gold aggregate have row counts |
| DQ findings included | Top failure reasons from Silver DQ report are summarized |
| Aggregates listed | Each Gold aggregate has a name, grain, and sample query |
| Paths and batch ID | The report includes the Bronze/Silver/Gold Volume paths and the batch ID from this run |
| Markdown valid | Headings are hierarchical, tables are valid, code blocks are tagged |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Final report | `output/{{DATASET_SLUG}}-report.md` | Markdown document with executive summary, row counts, DQ findings, Gold aggregates, recommendations |

The report in `output/` is the human edit surface. Open it in VSCode or any markdown viewer, polish the language, add your own findings, send to stakeholders.