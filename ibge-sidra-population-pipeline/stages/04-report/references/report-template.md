# Report Template

The structure every Stage 04 report follows. Fill in the placeholders from the actual run; do not leave them in the final report.

---

```markdown
# Pipeline Report: IBGE SIDRA Population Estimates

**Dataset**: ibge-sidra-population
**Source**: [IBGE SIDRA](https://sidra.ibge.gov.br/tabela/6579)
**Run timestamp**: <fill>
**Batch ID**: <fill from Bronze notebook>

---

## Executive Summary

<2-4 sentences: what was ingested, what was found, any critical issues>

---

## Pipeline Run Summary

| Stage | Output | Row count |
|-------|--------|-----------|
| Bronze | `dbfs:/Volumes/ibge/ibge_sidra_population_bronze/raw/ibge-sidra-population` | <fill> |
| Silver (kept) | `dbfs:/Volumes/ibge/ibge_sidra_population_silver/cleansed/ibge-sidra-population_clean` | <fill> |
| Silver (quarantined) | `dbfs:/Volumes/ibge/ibge_sidra_population_silver/quarantine/quarantine_ibge-sidra-population_clean` | <fill> |
| Gold: by_state_year | `dbfs:/Volumes/ibge/ibge_sidra_population_gold/aggregates/by_state_year` | <fill> |
| Gold: yearly_summary | `dbfs:/Volumes/ibge/ibge_sidra_population_gold/aggregates/yearly_summary` | <fill> |

---

## Data Quality Findings

<Summary from `ibge-sidra-population-dq-report.md`>

### Top failure reasons

| Failure reason | Rows | % of quarantined |
|----------------|------|------------------|
| <fill> | <fill> | <fill> |

### Notes

- <Any notable patterns: e.g. "All quarantined rows had null `state_id`, suggesting upstream join issue">
- <Recommended follow-ups: e.g. "Investigate why 12% of rows fail `year BETWEEN 1900 AND 2100` -- likely a parsing issue with two-digit years">

---

## Gold Aggregates

### by_state_year

- **Grain**: one row per <dimension combination>
- **Dimensions**: <list>
- **Measures**: <list>
- **Sample query**: `<SQL query that uses this aggregate>`

### yearly_summary

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
| Bronze | `dbfs:/Volumes/ibge/ibge_sidra_population_bronze/raw/ibge-sidra-population` |
| Silver (kept) | `dbfs:/Volumes/ibge/ibge_sidra_population_silver/cleansed/ibge-sidra-population_clean` |
| Silver (quarantine) | `dbfs:/Volumes/ibge/ibge_sidra_population_silver/quarantine/quarantine_ibge-sidra-population_clean` |
| Gold: by_state_year | `dbfs:/Volumes/ibge/ibge_sidra_population_gold/aggregates/by_state_year` |

### Notebooks (in `output/`)

| Stage | Notebook |
|-------|----------|
| Bronze | `ibge-sidra-population-bronze-notebook.py` |
| Silver | `ibge-sidra-population-silver-notebook.py` |
| Gold | `ibge-sidra-population-gold-notebook.py` |

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