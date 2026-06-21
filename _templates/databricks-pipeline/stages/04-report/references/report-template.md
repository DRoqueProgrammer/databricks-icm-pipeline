# Report Template

The structure every Stage 04 report follows. Fill in the placeholders from the actual run; do not leave them in the final report.

---

```markdown
# Pipeline Report: {{DATASET_DISPLAY_NAME}}

**Dataset**: {{DATASET_SLUG}}
**Source**: [{{DATASET_SOURCE}}]({{DATASET_SOURCE_URL}})
**Run timestamp**: <fill>
**Batch ID**: <fill from Bronze notebook>

---

## Executive Summary

<2-4 sentences: what was ingested, what was found, any critical issues>

---

## Pipeline Run Summary

| Stage | Output | Row count |
|-------|--------|-----------|
| Bronze | `{{BRONZE_VOLUME_PATH}}/{{DATASET_SLUG}}` | <fill> |
| Silver (kept) | `{{SILVER_VOLUME_PATH}}/{{DATASET_SLUG}}_clean` | <fill> |
| Silver (quarantined) | `{{QUARANTINE_VOLUME_PATH}}/quarantine_{{DATASET_SLUG}}_clean` | <fill> |
| Gold: {{AGGREGATE_1}} | `{{GOLD_VOLUME_PATH}}/{{AGGREGATE_1}}` | <fill> |
| Gold: {{AGGREGATE_2}} | `{{GOLD_VOLUME_PATH}}/{{AGGREGATE_2}}` | <fill> |

---

## Data Quality Findings

<Summary from `{{DATASET_SLUG}}-dq-report.md`>

### Top failure reasons

| Failure reason | Rows | % of quarantined |
|----------------|------|------------------|
| <fill> | <fill> | <fill> |

### Notes

- <Any notable patterns: e.g. "All quarantined rows had null `state_id`, suggesting upstream join issue">
- <Recommended follow-ups: e.g. "Investigate why 12% of rows fail `year BETWEEN 1900 AND 2100` -- likely a parsing issue with two-digit years">

---

## Gold Aggregates

### {{AGGREGATE_1}}

- **Grain**: one row per <dimension combination>
- **Dimensions**: <list>
- **Measures**: <list>
- **Sample query**: `<SQL query that uses this aggregate>`

### {{AGGREGATE_2}}

- **Grain**: ...
- **Dimensions**: ...
- **Measures**: ...
- **Sample query**: ...

---

## Recommendations

1. <Actionable next step, e.g. "Add a check for the `state_id` null root cause in the upstream source">
2. <E.g. "Increase the dedup window if multiple Bronze batches are arriving per day">
3. <E.g. "Consider adding a `cohort_year` dimension to enable retention analysis in Gold">

---

## Appendix

### Paths

| Layer | Volume path |
|-------|-------------|
| Bronze | `{{BRONZE_VOLUME_PATH}}/{{DATASET_SLUG}}` |
| Silver (kept) | `{{SILVER_VOLUME_PATH}}/{{DATASET_SLUG}}_clean` |
| Silver (quarantine) | `{{QUARANTINE_VOLUME_PATH}}/quarantine_{{DATASET_SLUG}}_clean` |
| Gold: {{AGGREGATE_1}} | `{{GOLD_VOLUME_PATH}}/{{AGGREGATE_1}}` |

### Notebooks (in `output/`)

| Stage | Notebook |
|-------|----------|
| Bronze | `{{DATASET_SLUG}}-bronze-notebook.py` |
| Silver | `{{DATASET_SLUG}}-silver-notebook.py` |
| Gold | `{{DATASET_SLUG}}-gold-notebook.py` |

### Batch metadata

- **Batch ID**: <fill>
- **Ingestion date**: <fill>
- **Source file**: <fill>
```

---

## Writing tips

- **Executive summary first**: a stakeholder should be able to read the first paragraph and know what happened
- **Numbers, not adjectives**: "1,234 quarantined rows (12% of Bronze)" beats "many quarantined rows"
- **Actionable recommendations**: each one should be specific enough that the next person knows what to do
- **No jargon**: a non-technical reader should understand the report
- **Link the paths**: make it easy to find the actual data

## What NOT to do in a report

- Bury the lede -- the executive summary goes at the top
- Include code samples unless they answer a specific question (link to the notebook instead)
- Add marketing language ("powerful", "robust", "scalable")
- Use emojis
- Include raw stack traces -- summarize what went wrong and link to the notebook