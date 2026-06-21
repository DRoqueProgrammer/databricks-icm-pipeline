# databricks-icm-pipeline

**A reusable [ICM](https://arxiv.org/abs/2603.16021) workspace template for Databricks Free Edition.** Four-stage medallion pipeline (Bronze -> Silver -> Gold -> Report) orchestrated by markdown files and folder structure, not by a multi-agent framework.

Built on the [Interpretable Context Methodology](https://github.com/RinDig/Interpreted-Context-Methdology) by Jake Van Clief & David McDermott.

---

## What is ICM?

ICM replaces framework-level orchestration with filesystem structure. Numbered folders represent stages. Plain markdown files carry the prompts and context that tell a single AI agent what role to play at each step. The result is a system where one agent, reading the right files at the right moment, does the work that would otherwise require a multi-agent framework.

The core insight: if the prompts and context for each stage already exist as files in a well-organized folder hierarchy, you don't need coordination code. You need one agent that reads the right files at the right time. The folder structure tells it what to do.

### Five layers of context

```
Layer 0: CLAUDE.md           "Where am I?"           Always loaded (~800 tokens)
Layer 1: CONTEXT.md          "Where do I go?"         Read on entry (~300 tokens)
Layer 2: Stage CONTEXT.md    "What do I do?"          Read per-task (~200-500 tokens)
Layer 3: Reference material  "What rules apply?"      Loaded selectively (varies)
Layer 4: Working artifacts   "What am I working with?" Loaded selectively (varies)
```

This template uses all five. Each stage CONTEXT.md specifies exactly which files from Layers 3 and 4 the agent loads -- the "What to Load" table prevents the model from drowning in irrelevant context.

---

## What's in this repo

```
databricks-icm-pipeline/
├── README.md                                       (this file)
├── CLAUDE.md                                       (Layer 0 routing for the workspace hub)
├── .gitignore
├── _templates/
│   └── databricks-pipeline/                        (the reusable template -- copy this)
│       ├── CLAUDE.md                               Layer 0
│       ├── CONTEXT.md                              Layer 1
│       ├── README.md
│       ├── setup/questionnaire.md                  runs with `setup` trigger
│       ├── _config/                                Layer 3 factory (set once)
│       │   ├── workspace.yaml                      catalog, volumes, cluster, paths
│       │   ├── conventions.md                      naming, partitioning, file formats
│       │   └── data-quality-rules.md               per-layer DQ rules
│       ├── shared/                                 Layer 3 cross-stage references
│       │   ├── medallion-cheatsheet.md             mental model
│       │   ├── databricks-free-edition-gotchas.md  10 documented Free Edition traps
│       │   └── volume-paths.md                     canonical Volume URIs
│       ├── skills/databricks-free-edition/         Layer 3 bundled domain skill
│       └── stages/
│           ├── 01-bronze/                          raw ingest (schema-on-read)
│           ├── 02-silver/                          cleansing, dedup, quarantine
│           ├── 03-gold/                            business aggregates, KPIs
│           └── 04-report/                          markdown report
└── ibge-sidra-population-pipeline/                 (worked example -- IBGE Brazilian census data)
    └── ...same structure, fully configured with zero {{}} placeholders remaining
```

---

## Quick start

### 1. Duplicate the template for your dataset

```bash
git clone https://github.com/DRoqueProgrammer/databricks-icm-pipeline.git
cd databricks-icm-pipeline
cp -r _templates/databricks-pipeline ./my-dataset-pipeline
cd my-dataset-pipeline
```

### 2. Run `setup`

Open the folder in your editor (VSCode, Cursor, anything that reads `CLAUDE.md`). Tell your AI agent:

> "Run `setup` in this workspace"

The agent reads `setup/questionnaire.md`, asks 18 questions in a single message, then replaces every `{{PLACEHOLDER}}` across the workspace with your answers.

The questionnaire configures:
- Databricks workspace URL + auth method
- Unity Catalog name, schemas, Volume paths
- Cluster ID (Free Edition clusters take 4-7 min to start)
- Default input format and partition column
- Primary keys, dedup keys, required columns, value ranges, foreign keys

After setup, zero `{{}}` patterns should remain. The agent scans for leftovers and asks if any are missing.

### 3. Run the pipeline

Tell the agent:

> "Ingest the dataset at `<path>` and produce Bronze"

The agent reads `stages/01-bronze/CONTEXT.md`, loads only the files listed in its "Inputs" table, and writes a notebook to `stages/01-bronze/output/`. You review the notebook, edit if needed, then ask for Silver. Repeat through Gold and Report.

### 4. Status check

> "status"

The agent scans `stages/*/output/` and renders an ASCII diagram:

```
Pipeline Status: my-dataset-pipeline

  [01-bronze]  -->  [02-silver]  -->  [03-gold]  -->  [04-report]
    COMPLETE          PENDING           PENDING         PENDING
  (bronze-notebook.py)
```

---

## Why ICM for Databricks?

| Problem with traditional approach | How ICM solves it |
|---|---|
| Airflow + dbt + notebook framework for every pipeline = 3 repos, 3 deploys | One workspace folder = one pipeline |
| Change the dedup logic = edit Python in 3 places | Change `_config/data-quality-rules.md` once |
| Hand off to a teammate = document env, deps, setup | Copy the folder |
| Debug a mid-pipeline failure = read logs, grep dashboards | Open the `output/` folder, read the markdown |
| Pipeline state lives in tool-specific storage | State is just files on disk |
| Review agent output = black box | Every intermediate artifact is editable markdown |

The Free Edition has additional constraints (CLI v1.3.0 bugs, Repos UI cache, $40 credit, OIDC-only auth, CSV path prefix quirk) that the bundled skill and `shared/databricks-free-edition-gotchas.md` document and work around.

---

## The worked example

`ibge-sidra-population-pipeline/` is a complete end-to-end run on Brazilian census data (IBGE SIDRA table 6579, population estimates). It demonstrates:

- A 18-question setup fully applied (zero `{{}}` remaining)
- A Bronze notebook with IBGE-specific patterns:
  - `sep=';'` delimiter (Brazilian CSV standard)
  - `encoding='ISO-8859-1'` (Brazilian government standard)
  - `skipRows=3` (SIDRA puts 3 title lines before the header)
  - `rename_map` for SIDRA dimension codes (`D1C` -> `state_id`, `V` -> `value`, etc.)
  - Ingest metadata columns (`ingestion_date`, `source_file`, `batch_id`)
  - Write to `dbfs:/Volumes/ibge/.../raw/ibge-sidra-population` as Delta

It's the proof that the template works on real data. Use it as a reference when building your own pipeline.

---

## Adapting the template

### For a different medallion stack

The template assumes Spark on Databricks. To adapt:

- **Snowflake / BigQuery**: replace the `databricks-free-edition` skill with one for your warehouse; replace `dbfs:/Volumes/...` paths with `s3://...` or `gs://...`
- **dbt instead of notebooks**: replace the `01-bronze/output/*.py` notebook generation with `models/staging/*.sql` generation
- **Airflow orchestration**: keep the ICM stages as-is, wrap them in Airflow tasks that read the `output/` folder as the task boundary

### For a non-medallion pipeline

The structure generalizes. Replace the four stages with whatever your workflow needs:

- Research -> Draft -> Edit -> Publish (writing)
- Idea -> Spec -> Code -> Test (software)
- Source -> Extract -> Transform -> Load (any ETL)
- Question -> Research -> Synthesize -> Report (any analysis)

The ICM contract is the same: numbered stages, each with a CONTEXT.md, each writing to `output/`, each loading only what its Inputs table says.

---

## Contributing

PRs welcome. The CI workflow (`.github/workflows/validate.yml`) enforces the ICM conventions:

- CONTEXT.md files <= 80 lines
- Reference files <= 200 lines
- No em dashes (` -- ` only)
- Every empty output/ folder has a `.gitkeep`
- No unresolved `{{PLACEHOLDER}}` patterns in template files

If you're adding a new workspace template, follow `_core/CONVENTIONS.md` from the [upstream repo](https://github.com/RinDig/Interpreted-Context-Methdology) (Patterns 1-15).

---

## References

- Paper: Van Clief, J. & McDermott, D. (2026). *Interpretable Context Methodology: Folder Structure as Agent Architecture.* arXiv:2603.16021. https://arxiv.org/abs/2603.16021
- Upstream repo: https://github.com/RinDig/Interpreted-Context-Methdology
- Databricks Free Edition 2026+ docs: https://docs.databricks.com/en/getting-started/free-edition.html

## License

MIT, same as the upstream ICM repo.