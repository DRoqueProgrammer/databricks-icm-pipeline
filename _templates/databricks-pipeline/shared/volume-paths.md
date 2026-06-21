# Volume Paths

Canonical Volume URIs for this workspace. Single source of truth for where Bronze/Silver/Gold/quarantine data lands.

If you change a Volume path here, every stage picks up the new path on the next run. Do not hardcode Volume paths inside stage CONTEXT.md files.

---

## Layout

```
{{CATALOG_NAME}}/
├── {{BRONZE_SCHEMA}}/
│   └── raw/                                          # source files as they arrived
│       ├── {{DATASET_SLUG}}/
│       │   ├── {{DATASET_SLUG}}_YYYY-MM-DD.csv     # one file per ingestion_date partition
│       │   └── ...
│       └── _manifest/                                # ingest metadata, one row per file
│
├── {{SILVER_SCHEMA}}/
│   ├── cleansed/                                     # valid Silver tables (Delta)
│   │   ├── {{DATASET_SLUG}}_clean                   # main Silver table
│   │   └── ...
│   └── quarantine/                                   # invalid rows from Silver DQ checks
│       └── quarantine_{{DATASET_SLUG}}_<table>     # one quarantine Delta table per source
│
└── {{GOLD_SCHEMA}}/
    └── aggregates/                                   # business aggregates (Delta)
        ├── {{DATASET_SLUG}}_by_<dimension1>_<dimension2>
        └── ...
```

---

## Naming convention

- Schemas: `{dataset_slug}_{layer}` in lowercase, underscores only
- Volume subdirectories: `raw/`, `cleansed/`, `aggregates/`, `quarantine/` (always lowercase, plural)
- Bronze raw files: `{dataset_slug}_{YYYY-MM-DD}.{ext}` where ext is the source extension
- Silver tables: `{dataset_slug}_{entity}_{grain}` (e.g. `ibge_population_clean`)
- Gold tables: `{dataset_slug}_{aggregate_name}` (e.g. `ibge_population_by_state_year`)
- Quarantine tables: `quarantine_{dataset_slug}_{silver_table_name}`

---

## Path templates (filled by `setup`)

```yaml
# Read in stage CONTEXT.md Inputs tables as:
bronze_raw_path:    "{{BRONZE_VOLUME_PATH}}/{{DATASET_SLUG}}"
silver_cleansed_path: "{{SILVER_VOLUME_PATH}}"
quarantine_path:    "{{QUARANTINE_VOLUME_PATH}}"
gold_aggregates_path: "{{GOLD_VOLUME_PATH}}"

# Example values (after setup):
bronze_raw_path:    "dbfs:/Volumes/ibge/ibge_sidra_bronze/raw/ibge_sidra_population"
silver_cleansed_path: "dbfs:/Volumes/ibge/ibge_sidra_silver/cleansed"
quarantine_path:    "dbfs:/Volumes/ibge/ibge_sidra_silver/quarantine"
gold_aggregates_path: "dbfs:/Volumes/ibge/ibge_sidra_gold/aggregates"
```

---

## Read/write rules

- **Always use `dbfs:/Volumes/...`** prefix on Free Edition. See `shared/databricks-free-edition-gotchas.md` #1.
- Use `dbutils.fs.ls(path)` to verify the path exists before reading.
- Use `dbutils.fs.mkdirs(path)` (idempotent) when creating directories.
- For Delta writes, prefer `df.write.format("delta").mode("append").save(path)` over `saveAsTable` when you want the path-based Delta table (easier to inspect, easier to move).
- For SQL warehouse access, use fully-qualified catalog.schema.table names without the `dbfs:/` prefix: `SELECT * FROM {{CATALOG_NAME}}.{{BRONZE_SCHEMA}}.{{DATASET_SLUG}}_raw`.

---

## Volume creation

If the Volume does not exist yet, the Bronze stage creates it. Use the SQL warehouse or the Catalog UI:

```sql
-- Run once per workspace (replace {{}} with actual values from setup):
CREATE CATALOG IF NOT EXISTS {{CATALOG_NAME}};
CREATE SCHEMA IF NOT EXISTS {{CATALOG_NAME}}.{{BRONZE_SCHEMA}};
CREATE VOLUME IF NOT EXISTS {{CATALOG_NAME}}.{{BRONZE_SCHEMA}}.raw;

CREATE SCHEMA IF NOT EXISTS {{CATALOG_NAME}}.{{SILVER_SCHEMA}};
CREATE VOLUME IF NOT EXISTS {{CATALOG_NAME}}.{{SILVER_SCHEMA}}.cleansed;
CREATE VOLUME IF NOT EXISTS {{CATALOG_NAME}}.{{SILVER_SCHEMA}}.quarantine;

CREATE SCHEMA IF NOT EXISTS {{CATALOG_NAME}}.{{GOLD_SCHEMA}};
CREATE VOLUME IF NOT EXISTS {{CATALOG_NAME}}.{{GOLD_SCHEMA}}.aggregates;
```

If `CREATE VOLUME` is not supported on Free Edition, create the schema and use `dbutils.fs.mkdirs()` for the subdirectories inside the schema's default Volume.