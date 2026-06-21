# Databricks Free Edition Gotchas

Operational quirks specific to **Databricks Free Edition 2026+** that you will hit. Read this once, internalize the patterns, and reference it whenever a stage throws an unexpected error.

This file is the canonical list. If you find a new gotcha, add it here. Do not duplicate it in stage CONTEXT.md files -- they reference this file.

---

## 1. CSV path must use `dbfs:/` prefix, even for Unity Catalog Volumes

```python
# WRONG (works on Pro/Enterprise, fails on Free Edition):
df = spark.read.csv("/Volumes/my_catalog/my_schema/my_volume/raw/file.csv", header=True)

# CORRECT (works everywhere):
df = spark.read.csv("dbfs:/Volumes/my_catalog/my_schema/my_volume/raw/file.csv", header=True)
```

Symptom if wrong: `AnalysisException: Path does not exist` even though the file is there. Free Edition does not auto-translate `/Volumes/` paths to the `dbfs:/` mount the way Pro/Enterprise do.

**Always use `dbfs:/Volumes/...` for `spark.read`, `spark.write`, and `dbutils.fs.ls` paths.**

---

## 2. `CREATE OR REPLACE TABLE` is NOT supported

```sql
-- WRONG:
CREATE OR REPLACE TABLE my_catalog.my_schema.my_table AS ...;

-- CORRECT (always):
DROP TABLE IF EXISTS my_catalog.my_schema.my_table;
CREATE TABLE my_catalog.my_schema.my_table AS ...;
```

In a notebook cell, `DROP IF EXISTS` + `CREATE` is fine. Wrap them in separate cells or use `%sql` for the drop and Python for the create if you want idempotent reruns.

If you see `SyntaxError: ... at or near "OR"` on Free Edition, this is why.

---

## 3. CLI v1.3.0 has bugs on Windows

The official Databricks CLI v1.3.0 has two known issues on Windows:

- **EOF on POST commands** (e.g. `databricks jobs create`, `databricks workspace import`): the CLI sends an HTTP `Expect: 100-continue` header that the Free Edition server does not handle, causing the POST to hang and eventually fail with `EOFError`.
- **Secure storage**: `databricks auth login --profile foo` fails to write the token to the OS keychain on Windows; the token stays in `~/.databrickscfg` in plaintext.

**Workarounds**:
- For POST commands, downgrade to CLI v0.240.x or use `curl` against the REST API directly
- For auth, accept the plaintext token in `~/.databrickscfg` -- it is local-user only and acceptable for Free Edition
- OIDC (`databricks auth login` with browser flow) is the recommended path going forward and avoids the plaintext token

---

## 4. Repos UI cache bug

The Repos UI on Free Edition sometimes shows a stale notebook after you push a new version from your local repo. Refresh alone does not always clear it.

**Workaround**: do not rely on the Repos UI for the current version of a notebook you just edited. Either:
- Create a new notebook in the Workspace and import the latest code
- Use `databricks workspace import` (CLI) which bypasses the Repos cache
- Use `%run /Workspace/Users/.../notebook` from another notebook to import the latest version explicitly

---

## 5. Notebook `.put()` to Volume accepts STRING, not BYTES

```python
# WRONG:
dbutils.fs.put("/Volumes/catalog/schema/volume/file.csv", b"col1,col2\nval1,val2", overwrite=True)

# CORRECT:
dbutils.fs.put("/Volumes/catalog/schema/volume/file.csv", "col1,col2\nval1,val2", overwrite=True)
```

Symptom if wrong: `TypeError: a bytes-like object is required, not 'str'`. The `dbutils.fs.put` on Free Edition expects a string for text files.

To read a binary file (e.g. parquet):

```python
bytes_data = spark.read.format("binaryFile").load(path).first().content
```

---

## 6. Reading `.xlsx` requires dynamic header detection

The Python `pandas.read_excel` infers headers from the first row. Real-world xlsx files often have a title row, blank row, then headers. The fix:

```python
import pandas as pd

df_raw = pd.read_excel("file.xlsx", header=None)
# Detect the header row: it's the first row with string cells under 60 chars
header_row_idx = 0
for i, row in df_raw.iterrows():
    cell = str(row.iloc[0])
    if cell and len(cell) < 60 and not cell.isdigit():
        header_row_idx = i
        break

df = pd.read_excel("file.xlsx", header=header_row_idx)
```

---

## 7. `$40 trial credits, OIDC only`

Free Edition 2026+ ships with a $40 credit and is OIDC-only. Personal Access Tokens are deprecated.

```bash
# OIDC login (browser flow):
databricks auth login --host https://dbc-ad8bbac7-4dce.cloud.databricks.com --profile DEFAULT

# Verify:
databricks auth describe --profile DEFAULT
```

If you see `PATs are not supported`, you are on a Free Edition workspace and need OIDC.

---

## 8. Workspace filesystem is case-sensitive on Volumes, case-insensitive on DBFS root

- `/dbfs/mnt/...` is case-insensitive on Windows clients
- `/Volumes/...` is case-sensitive

Always use lowercase path components in your code to avoid surprises.

---

## 9. Cluster startup is slow on Free Edition

Free Edition clusters take 4-7 minutes to start (no autoscaling, no pools). Plan for it. Serverless compute (when available) is faster but not always enabled.

For long pipelines, prefer a single persistent cluster rather than ephemeral ones.

---

## 10. `display()` on large DataFrames truncates

`display(df)` in a notebook shows up to 1000 rows by default and 1000 characters per cell. For larger inspection, use `df.show(n=50, truncate=False)` instead.

---

## When to read this file

A stage CONTEXT.md will reference this file in its Inputs table when Free Edition errors are plausible (CLI commands, DBFS/Volume path resolution, Repos). Load only on first error or on stage startup -- not at every cell.

For deeper operational knowledge (CLI command reference, auth flows, troubleshooting), load `skills/databricks-free-edition/SKILL.md`.