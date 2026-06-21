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
- Placeholder: `{{DATABRICKS_WORKSPACE_URL}}`
- Files: `_config/workspace.yaml`
- Type: free text
- Example: `https://dbc-ad8bbac7-4dce.cloud.databricks.com`
- Agent derives `{{DATABRICKS_WORKSPACE_ID}}` from the slug in the URL (no extra question)

### Q2: Auth method
- Placeholder: `{{AUTH_METHOD}}`
- Files: `_config/workspace.yaml`
- Type: selection
- Options: `oidc` (recommended for Free Edition 2026+), `pat` (legacy, deprecated)
- Default: `oidc`

### Q3: Databricks CLI profile name
- Placeholder: `{{DATABRICKS_PROFILE}}`
- Files: `_config/workspace.yaml`
- Type: free text
- Default: `DEFAULT`

### Q4: Unity Catalog name
- Placeholder: `{{CATALOG_NAME}}`
- Files: `_config/workspace.yaml`, `shared/volume-paths.md`
- Type: free text (lowercase, no spaces)
- Example: `ibge`, `brasil_io`, `kaggle_credit`
- Default: same as the dataset slug

### Q5: Dataset slug
- Placeholder: `{{DATASET_SLUG}}`
- Files: `_config/workspace.yaml`, `_config/data-quality-rules.md`, `shared/volume-paths.md`, all stage CONTEXT.md
- Type: free text (lowercase-with-hyphens)
- Example: `ibge-sidra-population`, `brasil-io-eleicoes`, `kaggle-credit-fraud`
- This is the dataset identity. Per-run variants go in stage outputs, not here.

### Q6: Dataset display name
- Placeholder: `{{DATASET_DISPLAY_NAME}}`
- Files: `_config/workspace.yaml`, `stages/04-report/references/report-template.md`
- Type: free text
- Example: `IBGE SIDRA Population Estimates`

### Q7: Dataset source
- Placeholders: `{{DATASET_SOURCE}}`, `{{DATASET_SOURCE_URL}}`
- Files: `_config/workspace.yaml`
- Type: free text
- Example: `IBGE SIDRA` / `https://sidra.ibge.gov.br/...`

### Q8: Bronze/Silver/Gold schema names
- Placeholders: `{{BRONZE_SCHEMA}}`, `{{SILVER_SCHEMA}}`, `{{GOLD_SCHEMA}}`
- Files: `_config/workspace.yaml`, `shared/volume-paths.md`
- Type: free text (lowercase)
- Default (derived from dataset_slug): `{dataset_slug}_bronze`, `{dataset_slug}_silver`, `{dataset_slug}_gold`

### Q9: Volume paths
- Placeholders: `{{VOLUME_ROOT}}`, `{{BRONZE_VOLUME_PATH}}`, `{{SILVER_VOLUME_PATH}}`, `{{GOLD_VOLUME_PATH}}`, `{{QUARANTINE_VOLUME_PATH}}`
- Files: `_config/workspace.yaml`, `shared/volume-paths.md`
- Type: free text
- Default (Free Edition convention): `dbfs:/Volumes/{catalog}/{bronze_schema}/raw`, etc.
- CRITICAL: must use `dbfs:/` prefix. See shared/databricks-free-edition-gotchas.md #1.

### Q10: Compute type
- Placeholders: `{{COMPUTE_TYPE}}`, `{{CLUSTER_ID}}`, `{{SERVERLESS_ENABLED}}`
- Files: `_config/workspace.yaml`
- Type: selection
- Options:
  - `cluster_id` -- use an existing interactive cluster (you provide the ID)
  - `serverless` -- use serverless compute (if enabled on your Free Edition workspace)
- Default: `cluster_id`

### Q11: Cluster ID (if Q10 = cluster_id)
- Placeholder: `{{CLUSTER_ID}}`
- Files: `_config/workspace.yaml`
- Type: free text (cluster ID from the Compute UI)
- Skip if Q10 = serverless

### Q12: Default input file format
- Placeholder: `{{DEFAULT_INPUT_FORMAT}}`
- Files: `_config/workspace.yaml`
- Type: selection
- Options: `csv`, `json`, `parquet`, `delta`
- Default: `csv`

### Q13: Default partition column
- Placeholder: `{{PARTITION_BY_DEFAULT}}`
- Files: `_config/workspace.yaml`
- Type: free text
- Default: `ingestion_date` (set by conventions.md)
- Override only if your dataset has a more natural time column (e.g. `reference_date` for time-series)

### Q14: Primary key columns
- Placeholders: `{{PK_COLUMN_1}}`, `{{PK_COLUMN_2}}`
- Files: `_config/data-quality-rules.md`
- Type: free text (comma-separated list of column names)
- Example: `state_id,year` for yearly state-level data
- Used in Silver for dedup and Gold for grain definition

### Q15: Dedup keys
- Placeholders: `{{DEDUP_KEY_1}}`, `{{DEDUP_KEY_2}}`
- Files: `_config/data-quality-rules.md`
- Type: free text
- Default: same as primary keys
- Override only if dedup uses a different grain (e.g. dedup on `id`, but PK is `(id, year)`)

### Q16: Required (non-nullable) columns
- Placeholders: `{{REQUIRED_COL_1}}`, `{{REQUIRED_COL_2}}`
- Files: `_config/data-quality-rules.md`
- Type: free text
- Example: `state_id`, `year`, `population`
- If the user provides fewer than 2, ask once more. Empty answers become documented optionals.

### Q17: Value range rules
- Placeholder: `{{RANGE_COLUMN}}` / `{{VALID_VALUES_OR_RANGE}}`
- Files: `_config/data-quality-rules.md`
- Type: free text
- Optional. Skip if no range rules.
- Example: `year` / `1900..2100`; `status` / `active|inactive|pending`

### Q18: Foreign key relationships
- Placeholders: `{{FK_COLUMN}}`, `{{REFERENCED_TABLE}}`
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

Workspace: {{DATABRICKS_WORKSPACE_URL}}
Dataset:   {{DATASET_DISPLAY_NAME}} ({{DATASET_SLUG}})
Catalog:   {{CATALOG_NAME}}
Compute:   {{COMPUTE_TYPE}}

Catalog/schemas/Volumes created on Databricks.
Workspace YAML and conventions are populated.

To run the pipeline, say:
  "Ingest the dataset at <path-to-source-file-or-url> and produce Bronze"
or just:
  "Run stage 01"
```

The first stage collects per-run details (which file, which URL) conversationally. The setup is one-time only.