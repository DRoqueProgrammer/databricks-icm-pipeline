---
name: databricks-free-edition
description: Work with Databricks Free Edition 2026+ (and related plans like Community Edition legacy or Premium trials). Covers the quirks that don't appear in official docs but bite in practice — PAT is deprecated, DBFS Root is disabled (use Unity Catalog Volumes), dbutils only works in Python notebooks (not SQL Editor), CLI v1.3.0 has multiple Windows bugs, REST API endpoints changed, and Repos is the only sane way to sync GitHub code. Use when setting up, deploying, or debugging a Databricks workspace — especially when the user is on a free/cheap tier with limited features.
---

# Databricks Free Edition 2026+ — Practical Reference

This is a working reference for the realities of Databricks Free Edition in 2026. It captures quirks that aren't in the official docs but that will eat hours if you don't know about them.

## Quick reference

| Topic | Reality in 2026+ Free Edition |
|---|---|
| **Auth (PAT)** | ❌ Deprecated. All `/api/*` endpoints return 401 with `"Credential was not sent or was of an unsupported type"` even with a fresh PAT. |
| **Auth (OIDC)** | ✅ Only working method. Login via browser, Databricks handles the token. |
| **Auth (GitHub App)** | ❌ Premium-only. Don't bother. |
| **Auth (OAuth M2M)** | ❌ Premium-only. Service principals not available. |
| **DBFS Root** | ❌ Disabled. `dbutils.fs.mkdirs("dbfs:/FileStore/...")` returns `DBFS_DISABLED: Public DBFS root is disabled`. |
| **Unity Catalog Volumes** | ✅ Working replacement for DBFS. Path: `/Volumes/<catalog>/<schema>/<volume>/`. |
| **Databricks Repos** | ✅ Works. Clone GitHub repo, sync commits, edit `.py` files directly. |
| **Custom Spark clusters** | ❌ Disabled. Only serverless SQL Warehouse. |
| **PySpark notebooks** | ❌ No custom runtime. Lakeflow Declarative Pipelines (serverless) only. |
| **CLI v1.3.0** | ⚠️ Multiple Windows bugs. `auth login` is flaky, POST requests return EOF, `auth_type = pat` config is required. |
| **`dbutils.fs.open` / `dbutils.fs.read`** | ❌ `AttributeError: 'RemoteFsHandler' object has no attribute 'open'`. Only `ls`/`mkdirs`/`mv`/`cp`/`put` work. **Don't try to use dbutils for byte I/O.** |
| **`dbutils.fs.put(path, STRING, overwrite=True)`** | ✅ Works! Up to 1 MB per call (perfect for CSVs, xlsx → CSV conversions, config blobs). Returns nothing on success. **Accepts STRING, not bytes** — pass `csv_text` (str) directamente, not `csv_bytes` (bytes). For multi-MB blobs, fall back to `spark.read.format("binaryFile")` + temp file + `dbutils.fs.cp`. |
| **`spark.read.format("binaryFile")`** | ⚠️ Hits 128MB gRPC limit on Free Edition. OK for small files, breaks on zips > 100MB. |
| **`spark.read.csv(path.zip)`** | ❌ Spark does NOT read zips natively (as of 2026+). `path` must point to extracted CSVs. |
| **`spark.sql("CREATE VOLUME ...")`** | ✅ Use this instead of `dbutils.fs.mkdirs` for Volumes. Idempotent with `IF NOT EXISTS`. |
| **`CREATE TABLE USING CSV OPTIONS (path='dbfs:/...')`** | ❌ **Broken on Free Edition 2026+ Unity Catalog.** Returns `UC_FILE_SCHEME_FOR_TABLE_CREATION_NOT_SUPPORTED: Creating table in Unity Catalog with file scheme dbfs is not supported`. Use the `read_files()` function instead (see Bronze ingestion section). |
| **`CREATE OR REPLACE TABLE ... USING CSV`** | ❌ Free Edition 2026+ disabled `REPLACE TABLE` for Unity Catalog. Returns `UNSUPPORTED_FEATURE.TABLE_OPERATION: ... does not support REPLACE TABLE`. Use `DROP TABLE IF EXISTS; CREATE TABLE ...;` instead. |
| **`read_files()` (Unity Catalog function, DBR 13.3+)** | ✅ **The canonical path for Bronze ingestion on Free Edition 2026+.** `CREATE TABLE x USING CSV AS SELECT * FROM read_files('/Volumes/catalog/schema/volume/', format=>'csv', header=>'true', delimiter=>';', encoding=>'iso-8859-1', multiLine=>'true')`. Accepts `/Volumes/...` paths directly (no scheme prefix). Charset names must be **canonical** (RFC 2978): `iso-8859-1`, `utf-8`, `utf-16`, `us-ascii` — NOT `Latin-1`, `cp1252`, `utf8`. |

## Auth (no PAT, OIDC only)

Always use OIDC federation via browser login. SQL Editor, Workspace, and Repos all support this without any CLI. The CLI is unreliable on Windows — see `references/cli-pitfalls.md`.

If you must script something, do it via REST API directly with `curl` + Bearer token from a session cookie (extracted after browser login), not via `databricks` CLI.

## Storage (Volumes, not DBFS)

DBFS Root (`dbfs:/FileStore/...`) is disabled. Use Unity Catalog Volumes:

```sql
CREATE VOLUME IF NOT EXISTS edulake.bronze.enem_raw
COMMENT 'ENEM microdados — uploaded manually via UI';
```

Then upload via UI: **File > Upload data** → select Volume as destination. The uploaded file lands at `/Volumes/edulake/bronze/enem_raw/file.csv`.

## Repos (the only sane sync path)

Databricks Repos is a built-in Git client that clones a GitHub repo into your workspace. To set up:

1. Workspace → Create → Repo
2. Paste `https://github.com/<owner>/<repo>.git`
3. Authorize GitHub via OAuth
4. Repo appears as a folder. `.py` files open directly as notebooks.

Commit and push from Databricks UI → goes back to GitHub. Edits on GitHub → appear in Databricks via "Pull" (auto-sync is configurable).

### Repos UI cache bug (intermittent but real)

Sometimes the Repos UI **shows a stale version of a file** even though `git pull` on the command line confirms the new content is in the repo. Symptoms:

- You run a notebook from Repos, the output uses an old version of the code
- `git log` shows the commit is in main
- The Repos UI shows "Synced" but doesn't reflect the new content
- "Pull" button doesn't appear or doesn't actually pull

**Workarounds (in order of preference):**

1. **Refresh the page** (Ctrl+Shift+R) and check again. ~30% of the time, this is just a browser cache.
2. **Open the file in a new tab** — Repos sometimes caches per-file, not per-repo.
3. **Edit-dummy-commit**: open the file in Repos UI, add a space anywhere, commit with message like "touch: force Repos sync". The dummy commit triggers a new sync and the file is reloaded. You can revert the dummy commit right after.
4. **Bypass Repos entirely**: create a new notebook in **Workspace** (not Repos), paste the content of the `.py` file (open it locally with `cat` and Ctrl+C), run. The notebook in Workspace is independent of Repos. Use this when a session is time-boxed and you can't wait for Repos to recover.

When the Repos UI is stuck, **don't fight it** — bypass to Workspace, finish the work, and clean up the Repos later. Reference: EduLake BR session 2026-06-14, ~1 hour of session time lost to Repos not pulling.

## dbutils and SQL Editor — gotchas that bite in every session

These cost real time on every Databricks Free Edition setup. Save them in muscle memory:

1. **`dbutils` is Python, not SQL.** `dbutils.fs.mkdirs("...")` in a SQL Editor query → `PARSE_SYNTAX_ERROR Syntax error at or near 'dbutils' line 7, pos 0`. Use a Python notebook for any `dbutils` call. SQL Editor only accepts DDL/DQL (`CREATE`, `SHOW`, `DESCRIBE`, `SELECT`).

2. **`dbutils.fs.open` and `dbutils.fs.read` DO NOT EXIST in Free Edition 2026+.** `dbutils.fs.open(path, "rb")` throws `AttributeError: 'RemoteFsHandler' object has no attribute 'open'`. The exposed API is just `ls`, `mkdirs`, `mv`, `cp` (and `rm` sometimes). **You cannot read or write bytes via dbutils on Free Edition.** Use:
   - For small files (<128MB): `spark.read.format("binaryFile").load(path).first().content` to read; `dbutils.fs.cp("file:/local/tmp", volume_path)` to write (write to local tmp first via `open().write()`).
   - For large files: extract on the user's local machine and upload CSVs to the Volume (see robust extraction pattern below).

3. **SQL Editor doesn't see what `dbutils` wrote.** If you create a Volume via Python notebook with `dbutils`, you can list it with `SHOW VOLUMES IN edulake.bronze` in SQL Editor, but the reverse is also asymmetric: `spark.sql("CREATE VOLUME ...")` works in both, `dbutils.fs.ls` works only in Python.

4. **`DESCRIBE CATALOG ... EXTENDED` is read-only metadata, not a table.** You can't `SELECT * FROM (DESCRIBE CATALOG edulake EXTENDED)` like a subquery. The return is a single result set of metadata, but Spark can't materialize it as a subquery — it expects real tables. For storage estimates, use `DESCRIBE DETAIL <table>` per table or `SHOW TABLES` to count.

5. **`spark.read.format("binaryFile")` hits a 128MB gRPC message limit on Free Edition.** Loading a 600MB ENEM zip via `binaryFile` → `SparkConnectGrpcException: Received message larger than max (620778072 vs. 134217728)`. Avoid for files > 100MB. The `binaryFile` reader does work, just not for big zips.

6. **Spark does NOT read zips natively.** `spark.read.csv("/Volumes/.../file.zip")` does not auto-decompress. The `path` option in `CREATE TABLE USING CSV` must point to a folder of extracted CSVs, not a zip. Plan for an extraction step before CREATE TABLE.

## Robust extraction pattern (extract on the user's machine, upload CSVs)

The cleanest path for big zips (ENEM 1.5GB, Censo 200MB+) is to **skip Databricks-side extraction entirely** and have the user extract locally, then upload the CSVs. This avoids every binary-handling bug in Databricks Free Edition 2026+.

**On the user's local shell (git-bash on Windows):**

```bash
cd ~/Downloads
mkdir -p enem_extracted
for year in 2020 2021 2022 2023; do
    mkdir -p enem_extracted/enem_$year
    unzip -j microdados_enem_${year}.zip "DADOS/MICRODADOS_ENEM_${year}.csv" \
        -d enem_extracted/enem_$year/
done
```

**Then upload via Databricks UI:** Catalog → `edulake` → `bronze` → Volume (e.g. `enem_raw`) → "Upload to this Volume" → select the local CSV. Databricks Volumes accept files up to 5GB per upload.

**For xlsx (IDEB, PIB):** convert locally with pandas, then upload the resulting CSV:

```bash
pip install pandas openpyxl  # one-time
python3 -c "
import pandas as pd
xls = pd.ExcelFile('divulgacao_anos_finais_escolas_2023.xlsx')
df = pd.read_excel(xls, sheet_name=xls.sheet_names[0])
df.to_csv('ideb_anos_finais_2023.csv', index=False, encoding='utf-8')
"
```

**Why this beats the Databricks-side approach:** no `binaryFile` 128MB limit, no `dbutils.fs.open` AttributeError, no zip native reading limitations, no Risk of a notebook hanging for 10 min on a 600MB binary read. Total time: ~30-60 min of uploads instead of 2 hours of debugging + retries.

## Excel/xlsx gotchas (INEP/IBGE files)

- **Headers often start at row 3-5, not row 1.** Reading `header=0` (default) gives you a row of `Unnamed: 0`, `Unnamed: 1`, etc. Use `header=N` (e.g. `header=3`) or pass `skiprows=2` to skip the metadata rows.
- **Multi-sheet workbooks:** IBGE PIB xlsx has 5+ sheets (PIB total, PIB per capita, rankings, etc.). Pick the one named "PIB per capita" explicitly — `sheet_name="PIB per capita"`, NOT index-based.
- **ODS files (LibreOffice format):** INEP sometimes publishes as `.ods` instead of `.xlsx`. The standard `pd.read_excel()` reads `.xlsx` only. For `.ods`, install `odfpy` (`pip install odfpy`) and use `pd.read_excel(file, engine='odf')`.
- **Encoding for xlsx → CSV:** IBGE xlsx typically Latin-1. When writing CSV with pandas, use `df.to_csv(..., encoding='latin-1')`. UTF-8 corrupts accents on read-back.

## Data formats — what to expect when uploading Brazilian public data

Free Edition 2026+ project datasets come in three shapes. Each needs different handling:

### CSV from INEP (ENEM, Censo Escolar, IDEB)

- **Encoding:** Latin-1 (ISO-8859-1), NOT UTF-8. If you specify `encoding = 'UTF-8'` on `CREATE TABLE USING CSV`, accents get corrupted.
- **Separator:** varies per dataset. ENEM uses `;`, Censo Escolar uses `|` (pipe — escape it carefully in SQL with `delimiter = '|'`), IDEB varies.
- **File pattern:** uploads arrive as `.zip` (smaller than extracted CSVs). **Extract on the user's local machine** (see "Robust extraction pattern" above), then point `CREATE TABLE` at the extracted folder.

### XLSX (PIB per capita from IBGE)

- Spark does NOT read `.xlsx` directly in `CREATE TABLE USING`.
- Convert via `pandas.read_excel` on the user's local machine (see "Excel/xlsx gotchas" above), then upload the resulting CSV.
- IBGE XLSX files have **multiple sheets** — pick the one named "PIB per capita" (or similar) explicitly. Sheet index is 0-based and the order is not guaranteed by name.
- Encoding is typically Latin-1 even from IBGE; verify with a `DESCRIBE TABLE` and check a row with accents.

### Parquet (modern INEP datasets, Base dos Dados)

- Spark reads Parquet natively. No `OPTIONS` needed beyond `path`.
- Faster than CSV (columnar, compressed).

## Standard 3-step setup flow (catalog + schemas + volumes + bronze)

Every Free Edition project hits the same setup. The proven sequence (zero guesses), **updated 2026+ for Unity Catalog realities**:

1. **SQL Editor** → run `CREATE CATALOG` + 3 `CREATE SCHEMA` (one `.sql` file, all idempotent with `IF NOT EXISTS`)
2. **Python notebook** → run 4 `CREATE VOLUME` (one cell per Volume, via `spark.sql`)
3. **User's local shell** → extract zips locally (`unzip`, `pandas.read_excel`) — see "Robust extraction pattern"
4. **UI** → upload extracted CSVs to each Volume (skip zips/xlsx — already extracted locally)
5. **SQL Editor** → run **4 `CREATE TABLE AS SELECT * FROM read_files(...)` per source** (the canonical Free Edition 2026+ path; `USING CSV OPTIONS` with `dbfs:/` scheme is broken on Unity Catalog). Pattern:

   ```sql
   DROP TABLE IF EXISTS edulake.bronze.enem_participante_raw;

   CREATE TABLE edulake.bronze.enem_participante_raw
   USING CSV
   AS SELECT * FROM read_files(
       '/Volumes/edulake/bronze/enem_raw/',
       format => 'csv',
       header => 'true',
       delimiter => ';',
       encoding => 'iso-8859-1',  -- canonical name (RFC 2978), NOT 'Latin-1'
       multiLine => 'true',
       escape => '"',
       quote => '"'
   );

   SELECT COUNT(*) AS total_rows FROM edulake.bronze.enem_participante_raw;
   ```
6. **Python notebook** → smoke test (`SELECT COUNT(*)`, ranges vs. expected) + storage check

**Critical: `encoding` must be the canonical name** (`iso-8859-1`, not `Latin-1`; `utf-8`, not `utf8`). The error message lists the valid set: `iso-8859-1, us-ascii, utf-16, utf-16be, utf-16le, utf-32, utf-8`. Use exactly one of those.

Total: ~30-60 min for a 4-source project on Free Edition. Each step has a one-liner diagnostic that fails fast.

## Notebooks committed to git: linting + cell-separator gotchas

When you put a Databricks notebook (`.py`) under git for sync via Repos, two non-Python quirks will trip you and your linter:

1. **`# Databricks notebook source` must be the literal first line** of the file. Without it, Databricks won't recognize the file as a notebook when you open it from Repos (it shows as a plain Python file, not a runnable cell). Always add this as line 1 of every notebook you commit.

2. **`# COMMAND ----------` is a cell separator**, not a Python comment. It tells the Databricks runtime "the cell ends here, next thing is a new cell". It does NOT trigger the Python interpreter. But many linters (ruff, pylint) will flag it as an "unused" or weirdly-formatted line. Linters also flag the `subprocess.run(...)` patterns you end up using as a workaround for `dbutils.fs.open`.

   **Mitigation:** in your `pyproject.toml`, exclude the notebook path from Python linting with a per-file-ignores rule. Example for a Databricks notebooks folder:

   ```toml
   [tool.ruff.lint.per-file-ignores]
   "databricks/notebooks/**/*.py" = ["E402", "F821", "B007", "E999"]
   ```

   The errors `E999` (syntax, raised by `# COMMAND ----------` or `%\pip install`), `F821` (`dbutils`, `spark` undefined in plain Python), `B007` (unused loop variable, common in shell wrappers), and `E402` (module-level import not at top, common in notebook cell order) are the ones you'll hit.

3. **`%pip install openpyxl` is a Databricks cell magic.** It works inside a notebook cell, but if you copy/paste it into a plain `.py` file in git, Python's parser rejects it as a `SyntaxError` on the `%`. If you need the notebook file to also be valid Python (for tooling, linting, testing), replace `%pip install` with `subprocess.run(["pip", "install", "<pkg>"], check=True, capture_output=True)`. This works in both Databricks runtime and plain Python.

## Working URL for new Free Edition workspaces (2026+)

The legacy `community.cloud.databricks.com` URL no longer issues new accounts. Sign-up since 2026 creates a workspace at a URL like `dbc-<8-char-hash>-<hash>.cloud.databricks.com` (e.g. `dbc-ad8bbac7-4dce.cloud.databricks.com`). Your `?o=<workspace_id>` query param identifies the workspace. The `~/.databrickscfg` host should be the per-workspace URL, not the alias. The alias only redirects to a specific workspace; if you have multiple workspaces (e.g. one AWS trial that was blocked + one Free Edition), they have different `dbc-*` URLs and need separate profiles.

## Reference files

- `references/auth-and-credentials.md` — full list of what auth methods work and don't
- `references/volumes-vs-dbfs.md` — path migration guide, upload patterns
- `references/cli-pitfalls.md` — the bugs in v1.3.0 and workarounds
- `references/data-formats.md` — CSV/Parquet/XLSX/zip handling for Brazilian public datasets
- `references/notebook-authoring-gotchas.md` — cell separators, magic commands, lint config
- `references/institutional-data-source-gotchas.md` — which IDEB/PIB/ENEM zip to download, the 5-tab PIB xlsx structure, column name drift across years
- `references/edu-lake-br-session-2026-06-14.md` — **session-specific reproduction recipes**: exact error messages from the EduLake BR portfolio project, user-debugged fixes (header=None, dynamic header detection, dbutils.fs.put accepts STRING), the 7-bugs-in-order narrative, mistakes not to repeat
- `templates/create-volumes-notebook.py` — known-good notebook for creating 4 Volumes
- `templates/01_catalog_and_schemas.sql` — idempotent DDL for catalog + schemas
- `templates/02_extract_uploads.py` — small-file zip/xlsx extraction (NOT for files > 100MB — extract locally)
