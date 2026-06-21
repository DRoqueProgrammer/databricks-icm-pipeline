# Volumes vs DBFS Root — Databricks Free Edition 2026+

## TL;DR

**DBFS Root is disabled.** Use **Unity Catalog Volumes** for all file storage. They have the same `dbutils.fs` API but live under Unity Catalog governance.

## The error you'll see

```
ExecutionError: [DBFS_DISABLED] Public DBFS root is disabled. Access is denied on path: /dbfs:/FileStore/...
```

Or for `dbutils.fs.cp` from a notebook:

```
AnalysisException: Access is denied on path: /mnt/edulake/bronze
```

## Path migration

| Old (DBFS Root, BROKEN) | New (Unity Catalog Volume, WORKS) |
|---|---|
| `dbfs:/FileStore/edulake/bronze/enem/` | `/Volumes/edulake/bronze/enem_raw/` |
| `dbfs:/mnt/datalake/...` | `/Volumes/<catalog>/<schema>/<volume>/...` |
| `dbutils.fs.mkdirs("dbfs:/FileStore/...")` | `spark.sql("CREATE VOLUME IF NOT EXISTS ...")` |
| `dbutils.fs.cp("dbfs:/FileStore/x", "dbfs:/FileStore/y")` | `dbutils.fs.cp("/Volumes/x", "/Volumes/y")` |
| `spark.read.csv("dbfs:/FileStore/file.csv")` | `spark.read.csv("/Volumes/cat/schema/volume/file.csv")` |

## How to create a Volume

In a Python notebook (since `CREATE VOLUME` is SQL DDL, easiest via `spark.sql`):

```python
spark.sql("""
CREATE VOLUME IF NOT EXISTS edulake.bronze.enem_raw
COMMENT 'ENEM microdados — uploaded manually via UI'
""")
```

Or in SQL Editor (with a SQL Warehouse attached):

```sql
CREATE VOLUME IF NOT EXISTS edulake.bronze.enem_raw
COMMENT 'ENEM microdados — uploaded manually via UI';
```

## How to upload files

**Via UI:**

1. Workspace → left sidebar → **Catalog**
2. Navigate: `edulake` → `bronze` → click the Volume (e.g. `enem_raw`)
3. Top right → **Upload to this volume** (or "Add data" → "Upload files")
4. Select local file → click Upload

**Via notebook Python (useful for many small files):**

```python
# Read local file, write to Volume
with open("/local/path/file.csv", "rb") as f:
    data = f.read()
dbutils.fs.put("/Volumes/edulake/bronze/enem_raw/file.csv", data, overwrite=True)
```

## Listing Volume contents

```python
# List files in a Volume
files = dbutils.fs.ls("/Volumes/edulake/bronze/enem_raw/")
for f in files:
    print(f.name, f.size)

# Or via SQL
spark.sql("LIST '/Volumes/edulake/bronze/enem_raw/'").show()
```

## Permissions model

Volumes inherit Unity Catalog governance:

- **Owner of the Volume** = can grant/revoke access
- **Default**: only the Volume owner can read/write
- To allow a job/notebook to read: `GRANT READ VOLUME ON VOLUME edulake.bronze.enem_raw TO \`<user-or-group>\``

On Free Edition 2026+, your user is typically owner of everything you create. Sharing with other users requires admin to grant `EXTERNAL USE SCHEMA` (also Premium).

## When to use Volumes vs other storage

| Use case | Use |
|---|---|
| CSV/parquet files for `CREATE TABLE USING CSV` | Volume ✅ |
| Delta tables | Catalog (managed) or external table on Volume |
| Large ML training data | Volume (or external table pointing to S3/ADLS/GCS) |
| Streaming data (Auto Loader) | Volume (with `cloudFiles` source) |

## Common pitfalls

1. **Creating the Volume in the wrong schema**: must be in a schema that exists. `edulake.bronze` must exist before `CREATE VOLUME edulake.bronze.enem_raw`.
2. **Uploading to a path that doesn't match the Volume name**: Volume `enem_raw` → must upload to `/Volumes/edulake/bronze/enem_raw/`, not `/Volumes/edulake/bronze/enem/` (different name = different Volume = error).
3. **Confusing Volumes with DBFS in old code**: if you copy SQL from old tutorials that use `dbfs:/mnt/...`, change to `/Volumes/...`.
4. **Forgetting to commit the Volume creation**: if you create a Volume in a notebook, it's NOT in the repo. To make it reproducible, capture the `CREATE VOLUME` statement in a `.sql` or `.py` file and commit.

## Reference

- [Unity Catalog Volumes — Databricks docs](https://docs.databricks.com/en/Volumes/index.html)
- [Manage Volumes in Unity Catalog](https://docs.databricks.com/en/volumes/manage-volumes.html)
