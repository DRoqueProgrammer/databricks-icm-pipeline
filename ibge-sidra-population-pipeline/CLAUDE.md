# Databricks Pipeline (Medallion: Bronze -> Silver -> Gold)

This workspace orchestrates a Databricks Free Edition medallion pipeline. One agent, reading the right files at each stage, does the work that would otherwise require Airflow + dbt + a notebook framework.

The workspace is a TEMPLATE: duplicate this folder per dataset. After `setup`, each run produces a new dataset's Bronze/Silver/Gold notebooks + a final report.

## Folder Map

```
databricks-pipeline/
├── CLAUDE.md                (you are here)
├── CONTEXT.md               (start here for task routing)
├── README.md                (how to use this template)
├── setup/
│   └── questionnaire.md     (one-time onboarding -- workspace, catalog, paths)
├── _config/                 (Layer 3 factory -- set once)
│   ├── workspace.yaml       (catalog, schema, volume paths, cluster config)
│   ├── conventions.md       (naming, partitioning, file format defaults)
│   └── data-quality-rules.md (Great Expectations rules per layer)
├── shared/                  (Layer 3 cross-stage references)
│   ├── medallion-cheatsheet.md        (Bronze/Silver/Gold: what each layer is for)
│   ├── databricks-free-edition-gotchas.md  (CSV dbfs:/ prefix, no CREATE OR REPLACE, etc.)
│   └── volume-paths.md     (canonical Volume paths per layer)
├── skills/                  (Layer 3 bundled domain knowledge)
│   └── databricks-free-edition/
│       └── SKILL.md         (operational quirks, CLI traps, OIDC auth)
└── stages/
    ├── 01-bronze/           (raw ingest: schema-on-read, full lineage)
    │   ├── CONTEXT.md
    │   ├── references/
    │   │   ├── bronze-ingest-patterns.md
    │   │   └── notebook-template.py
    │   └── output/          (Layer 4: finished Bronze notebook)
    ├── 02-silver/           (cleansing, dedup, type coercion, quarantine)
    │   ├── CONTEXT.md
    │   ├── references/
    │   │   ├── silver-transforms.md
    │   │   └── expectations.md
    │   └── output/
    ├── 03-gold/             (business aggregates, KPIs, Z-order)
    │   ├── CONTEXT.md
    │   ├── references/
    │   │   └── gold-aggregates.md
    │   └── output/
    └── 04-report/           (markdown report: counts, top issues, findings)
        ├── CONTEXT.md
        ├── references/
        │   └── report-template.md
        └── output/
```

## Triggers

| Keyword | Action |
|---------|--------|
| `setup` | Run onboarding questionnaire -- configures workspace, catalog, volume paths, cluster |
| `status` | Show pipeline completion for all four stages |

### How `status` works

Scan `stages/*/output/` folders. For each stage, if the output folder contains files other than `.gitkeep`, the stage is COMPLETE. Otherwise it is PENDING. Render:

```
Pipeline Status: databricks-pipeline (dataset=ibge-sidra-population)

  [01-bronze]  -->  [02-silver]  -->  [03-gold]  -->  [04-report]
    STATUS           STATUS           STATUS          STATUS
  (files...)        (files...)       (files...)      (files...)
```

## Routing

| Task | Go To |
|------|-------|
| Ingest raw data into Bronze | `stages/01-bronze/CONTEXT.md` |
| Cleanse and dedup into Silver | `stages/02-silver/CONTEXT.md` |
| Build Gold aggregates and KPIs | `stages/03-gold/CONTEXT.md` |
| Generate the final markdown report | `stages/04-report/CONTEXT.md` |
| Configure this workspace (first run only) | `setup/questionnaire.md` |

## What to Load

The context-window budget is sacred. Each task loads the minimum set that lets the agent do its job well.

| Task | Load These | Do NOT Load |
|------|-----------|-------------|
| Run Bronze stage | `_config/workspace.yaml`, `_config/conventions.md`, `shared/databricks-free-edition-gotchas.md`, `shared/volume-paths.md`, `stages/01-bronze/references/*`, user-provided dataset path | `stages/02..04/*`, `skills/databricks-free-edition/SKILL.md` (load only on error) |
| Run Silver stage | `stages/01-bronze/output/` (the Bronze notebook just produced), `shared/databricks-free-edition-gotchas.md`, `_config/data-quality-rules.md`, `stages/02-silver/references/*` | `stages/01-bronze/references/`, `stages/03..04/*` |
| Run Gold stage | `stages/02-silver/output/`, `_config/conventions.md`, `stages/03-gold/references/*` | `stages/01..02/references/`, `stages/04/*` |
| Run Report stage | `stages/01..03/output/`, `stages/04-report/references/report-template.md` | `stages/*/references/`, `skills/`, `_config/` |

If the agent hits a Databricks Free Edition error (CLI EOF, Repos cache, etc.), load `skills/databricks-free-edition/SKILL.md` and `shared/databricks-free-edition-gotchas.md` for the recovery procedure.

## Stage Handoffs

Each stage writes its finished notebook or report to its own `output/` folder. The next stage reads from there. If you edit an output notebook between stages (add a column, change a partition spec), the next stage picks up your edits when it reads the file.

This is the primary steering mechanism: humans review between stages.

## Template vs Workspace

This folder is a TEMPLATE. To use it for a real dataset:

```bash
cp -r ~/workspaces/_templates/databricks-pipeline ~/workspaces/<dataset-slug>-pipeline
cd ~/workspaces/<dataset-slug>-pipeline
```

Then run `setup`. The questionnaire fills in `ibge-sidra-population`, `ibge`, volume paths, and cluster config. Every run on a new dataset starts from a fresh copy.