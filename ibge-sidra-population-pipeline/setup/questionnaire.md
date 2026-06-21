# Onboarding Questionnaire: Databricks Pipeline

<!-- Agent instructions: Read this file when the user types "setup". Ask ALL questions
     below in a single conversational pass. The user should be able to answer everything
     in one message. These questions configure the workspace -- not a specific dataset run.

     After collecting answers:
       1. Replace {{}} placeholders across all files in this workspace
       2. Fill derived fields (catalog defaults, volume paths) without asking
       3. Scan for remaining {{ patterns -- resolve or ask
       4. Confirm with the user before running any stage -->

<!-- Per ICM CONVENTIONS.md Pattern 8:
     - FLAT STRUCTURE (no groupings)
     - ALL AT ONCE (one message from user)
     - SYSTEM-LEVEL (catalog/cluster, not per-dataset name -- that's per-run)
     - DERIVE, DON'T ASK (infer PKs from dedup_keys if composite, etc.)
     - SENSIBLE DEFAULTS (always provide one)
     - ASK ONCE -->

---

### Q1: Databricks workspace URL
- Placeholder: `https://dbc-ad8bbac7-4dce.cloud.databricks.com`
- Files: `_config/workspace.yaml`
- Type: free text
- Example: `https://dbc-ad8bbac7-4dce.cloud.databricks.com`
- Agent derives `dbc-ad8bbac7-4dce` from the slug in the URL (no extra question)

### Q2: Auth method
- Placeholder: `oidc`
- Files: `_config/workspace.yaml`
- Type: selection
- Options: `oidc` (recommended for Free Edition 2026+), `pat` (legacy, deprecated)
- Default: `oidc`

### Q3: Databricks CLI profile name
- Placeholder: `DEFAULT`
- Files: `_config/workspace.yaml`
- Type: free text
- Default: `DEFAULT`

### Q4: Unity Catalog name
- Placeholder: `ibge`
- Files: `_config/workspace.yaml`, `shared/volume-paths.md`
- Type: free text (lowercase, no spaces)
- Example: `ibge`, `brasil_io`, `kaggle_credit`
- Default: same as the dataset slug

### Q5: Dataset slug
- Placeholder: `ibge-sidra-population`
- Files: `_config/workspace.yaml`, `_config/data-quality-rules.md`, `shared/volume-paths.md`, all stage CONTEXT.md
- Type: free text (lowercase-with-hyphens)
- Example: `ibge-sidra-population`, `brasil-io-eleicoes`, `kaggle-credit-fraud`
- This is the dataset identity. Per-run variants go in stage outputs, not here.

### Q6: Dataset display name
- Placeholder: `IBGE SIDRA Population Estimates`
- Files: `_config/workspace.yaml`, `stages/04-report/references/report-template.md`
- Type: free text
- Example: `IBGE SIDRA Population Estimates`

### Q7: Dataset source
- Placeholders: `IBGE SIDRA`, `https://sidra.ibge.gov.br/tabela/6579`
- Files: `_config/workspace.yaml`
- Type: free text
- Example: `IBGE SIDRA` / `https://sidra.ibge.gov.br/...`

### Q8: Bronze/Silver/Gold schema names
- Placeholders: `ibge_sidra_population_bronze`, `ibge_sidra_population_silver`, `ibge_sidra_population_gold`
- Files: `_config/workspace.yaml`, `shared/volume-paths.md`
- Type: free text (lowercase)
- Default (derived from dataset_slug): `{dataset_slug}_bronze`, `{dataset_slug}_silver`, `{dataset_slug}_gold`

### Q9: Volume paths
- Placeholders: `dbfs:/Volumes/ibge/ibge_sidra_population_bronze/raw`, `dbfs:/Volumes/ibge/ibge_sidra_population_bronze/raw`, `dbfs:/Volumes/ibge/ibge_sidra_population_silver/cleansed`, `dbfs:/Volumes/ibge/ibge_sidra_population_gold/aggregates`, `dbfs:/Volumes/ibge/ibge_sidra_population_silver/quarantine`
- Files: `_config/workspace.yaml`, `shared/volume-paths.md`
- Type: free text
- Default (Free Edition convention): `dbfs:/Volumes/{catalog}/{bronze_schema}/raw`, etc.
- CRITICAL: must use `dbfs:/` prefix. See shared/databricks-free-edition-gotchas.md #1.

### Q10: Compute type
- Placeholders: `cluster_id`, `0609-145002-9j1f9vy7`, `false`
- Files: `_config/workspace.yaml`
- Type: selection
- Options:
  - `cluster_id` -- use an existing interactive cluster (you provide the ID)
  - `serverless` -- use serverless compute (if enabled on your Free Edition workspace)
- Default: `cluster_id`

### Q11: Cluster ID (if Q10 = cluster_id)
- Placeholder: `0609-145002-9j1f9vy7`
- Files: `_config/workspace.yaml`
- Type: free text (cluster ID from the Compute UI)
- Skip if Q10 = serverless

### Q12: Default input file format
- Placeholder: `csv`
- Files: `_config/workspace.yaml`
- Type: selection
- Options: `csv`, `json`, `parquet`, `delta`
- Default: `csv`

### Q13: Default partition column
- Placeholder: `ingestion_date`
- Files: `_config/workspace.yaml`
- Type: free text
- Default: `ingestion_date` (set by conventions.md)
- Override only if your dataset has a more natural time column (e.g. `reference_date` for time-series)

### Q14: Primary key columns
- Placeholders: `state_id`, `year`
- Files: `_config/data-quality-rules.md`
- Type: free text (comma-separated list of column names)
- Example: `state_id,year` for yearly state-level data
- Used in Silver for dedup and Gold for grain definition

### Q15: Dedup keys
- Placeholders: `state_id`, `year`
- Files: `_config/data-quality-rules.md`
- Type: free text
- Default: same as primary keys
- Override only if dedup uses a different grain (e.g. dedup on `id`, but PK is `(id, year)`)

### Q16: Required (non-nullable) columns
- Placeholders: `state_id`, `year`
- Files: `_config/data-quality-rules.md`
- Type: free text
- Example: `state_id`, `year`, `population`
- If the user provides fewer than 2, ask once more. Empty answers become documented optionals.

### Q17: Value range rules
- Placeholder: `year` / `year BETWEEN 1900 AND 2100`
- Files: `_config/data-quality-rules.md`
- Type: free text
- Optional. Skip if no range rules.
- Example: `year` / `1900..2100`; `status` / `active|inactive|pending`

### Q18: Foreign key relationships
- Placeholders: `state_id`, `dbfs:/Volumes/ibge/reference/states_clean`
- Files: `_config/data-quality-rules.md`
- Type: free text
- Optional. Skip if no FKs.

---

## After Onboarding

1. Replace every `{{}}` placeholder across the workspace using the answers above
2. Derive the defaults (workspace_id from URL slug, schema names from dataset_slug)
3. Scan the workspace for any remaining `{{` patterns. If any remain, ask the user for the missing info.
4. Create the catalog, schemas, and Volumes on Databricks (run the SQL in `shared/volume-paths.md`)
5. Tell the user:

```
You are set up.

Workspace: https://dbc-ad8bbac7-4dce.cloud.databricks.com
Dataset:   IBGE SIDRA Population Estimates (ibge-sidra-population)
Catalog:   ibge
Compute:   cluster_id

Catalog/schemas/Volumes created on Databricks.
Workspace YAML and conventions are populated.

To run the pipeline, say:
  "Ingest the dataset at <path-to-source-file-or-url> and produce Bronze"
or just:
  "Run stage 01"
```

The first stage collects per-run details (which file, which URL) conversationally. The setup is one-time only.