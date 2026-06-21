# Volume Paths

Canonical Volume URIs for this workspace. Single source of truth for where Bronze/Silver/Gold/quarantine data lands.

If you change a Volume path here, every stage picks up the new path on the next run. Do not hardcode Volume paths inside stage CONTEXT.md files.

---

## Layout

```
ibge/
├── ibge_sidra_population_bronze/
│   └── raw/                                          # source files as they arrived
│       ├── ibge-sidra-population/
│       │   ├── ibge-sidra-population_YYYY-MM-DD.csv     # one file per ingestion_date partition
│       │   └── ...
│       └── _manifest/                                # ingest metadata, one row per file
│
├── ibge_sidra_population_silver/
│   ├── cleansed/                                     # valid Silver tables (Delta)
│   │   ├── ibge-sidra-population_clean                   # main Silver table
│   │   └── ...
│   └── quarantine/                                   # invalid rows from Silver DQ checks
│       └── quarantine_ibge-sidra-population_<table>     # one quarantine Delta table per source
│
└── ibge_sidra_population_gold/
    └── aggregates/                                   # business aggregates (Delta)
        ├── ibge-sidra-population_by_<dimension1>_<dimension2>
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
bronze_raw_path:    "dbfs:/Volumes/ibge/ibge_sidra_population_bronze/raw/ibge-sidra-population"
silver_cleansed_path: "dbfs:/Volumes/ibge/ibge_sidra_population_silver/cleansed"
quarantine_path:    "dbfs:/Volumes/ibge/ibge_sidra_population_silver/quarantine"
gold_aggregates_path: "dbfs:/Volumes/ibge/ibge_sidra_population_gold/aggregates"

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
- For SQL warehouse access, use fully-qualified catalog.schema.table names without the `dbfs:/` prefix: `SELECT * FROM ibge.ibge_sidra_population_bronze.ibge-sidra-population_raw`.

---

## Volume creation

If the Volume does not exist yet, the Bronze stage creates it. Use the SQL warehouse or the Catalog UI:

```sql
-- Run once per workspace (replace {{}} with actual values from setup):
CREATE CATALOG IF NOT EXISTS ibge;
CREATE SCHEMA IF NOT EXISTS ibge.ibge_sidra_population_bronze;
CREATE VOLUME IF NOT EXISTS ibge.ibge_sidra_population_bronze.raw;

CREATE SCHEMA IF NOT EXISTS ibge.ibge_sidra_population_silver;
CREATE VOLUME IF NOT EXISTS ibge.ibge_sidra_population_silver.cleansed;
CREATE VOLUME IF NOT EXISTS ibge.ibge_sidra_population_silver.quarantine;

CREATE SCHEMA IF NOT EXISTS ibge.ibge_sidra_population_gold;
CREATE VOLUME IF NOT EXISTS ibge.ibge_sidra_population_gold.aggregates;
```

If `CREATE VOLUME` is not supported on Free Edition, create the schema and use `dbutils.fs.mkdirs()` for the subdirectories inside the schema's default Volume.