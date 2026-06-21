# Data Formats — Brazilian Public Data on Free Edition 2026+

The three file shapes you'll encounter when building a portfolio project with INEP/IBGE/Base dos Dados, and how to handle each in Databricks SQL + Python notebooks.

## CSV (ENEM, Censo Escolar, IDEB raw extracts)

**Encoding is almost always Latin-1** (ISO-8859-1), even for modern INEP datasets. This catches people because:
- The default `encoding` in `CREATE TABLE USING CSV` is UTF-8
- The first few rows look fine (English/symbols only) so you don't notice
- Then `SELECT * FROM ... WHERE NO_MUNICIPIO LIKE '%Cuiab%'` returns 0 rows because the accent got mangled to `CuiabÃ¡`

**Symptom:** sample rows show accented characters as `Ã©`, `Ã§`, `Ã£`, `Ã±`, `Ãº`. Encoding is wrong.

**Fix:** specify `encoding = 'Latin-1'` in the `CREATE TABLE USING CSV` OPTIONS.

**Separators vary per dataset:**

| Dataset | Separator | Notes |
|---|---|---|
| ENEM microdados | `;` (semicolon) | Plus `header = 'true'`, `inferSchema = 'true'` |
| Censo Escolar | `\|` (pipe) | Escape carefully in SQL: `delimiter = '\|'` |
| IDEB | `;` or `,` | Varies per year — check the actual file first |
| PIB per capita IBGE | `;` or tab (from XLSX) | See XLSX section below |

**Working template (ENEM):**

```sql
CREATE OR REPLACE TABLE edulake.bronze.enem_participante_raw
USING CSV
OPTIONS (
    path '/Volumes/edulake/bronze/enem_raw/',
    header = 'true',
    delimiter = ';',
    encoding = 'Latin-1',
    inferSchema = 'true',
    multiLine = 'true',
    escape = '"',
    quote = '"'
);
```

**Working template (Censo Escolar with pipe separator):**

```sql
CREATE OR REPLACE TABLE edulake.bronze.censo_escola_raw
USING CSV
OPTIONS (
    path '/Volumes/edulake/bronze/censo_raw/',
    header = 'true',
    delimiter = '|',
    encoding = 'Latin-1',
    inferSchema = 'true',
    multiLine = 'true',
    escape = '"',
    quote = '"'
);
```

## XLSX (PIB per capita from IBGE)

Spark `CREATE TABLE USING` does NOT support `.xlsx`. You must convert to CSV first via a Python notebook.

**IBGE XLSX quirks:**

1. **Multiple sheets.** The PIB-Municípios XLSX has 4-6 sheets: "PIB", "PIB per capita", "População", etc. You want "PIB per capita" specifically.
2. **Sheet names are NOT in the file name.** Inspect first:
   ```python
   from openpyxl import load_workbook
   wb = load_workbook(io.BytesIO(xlsx_bytes), read_only=True, data_only=True)
   print(wb.sheetnames)  # ['PIB', 'PIB per capita', 'População residente', ...]
   ```
3. **Encoding is Latin-1**, even though the file is `.xlsx`. When you write CSV, encode to UTF-8 with explicit `open(..., encoding='utf-8')` so Databricks reads it back as UTF-8.
4. **Some sheets have merged cells or empty rows.** Filter with `if all(cell is None for cell in row): continue` when iterating.

**Working template (XLSX → CSV conversion) — REVISED 2026-06-14:**

`dbutils.fs.open()` **NAO EXISTE** no Free Edition 2026+. Use este workaround (validado pelo user Davi Roque):

```python
import io
from openpyxl import load_workbook

# Lê bytes do Volume via Spark binary file
xlsx_bytes = spark.read.format("binaryFile").load(
    "/Volumes/edulake/bronze/pib_raw/tabelas_completas_2022.xlsx"
).first().content

wb = load_workbook(io.BytesIO(xlsx_bytes), read_only=True, data_only=True)
print("Sheets:", wb.sheetnames)

# Pick the PIB per capita sheet
target_sheet = next(
    s for s in wb.sheetnames if "per capita" in s.lower()
)
ws = wb[target_sheet]

# CRITICAL: pd.read_excel() (ou openpyxl direto) trata a primeira linha como
# header por padrao. XLSXs do IBGE/INEP tem 2-3 linhas de titulo/subtitulo
# ANTES do header real, que viram "Unnamed: 0", "Unnamed: 1", etc. e bagunçam
# tudo. Use header=None e faca deteccao dinamica do header real:
#
# import pandas as pd
# df = pd.read_excel(io.BytesIO(xlsx_bytes), sheet_name=target_sheet, header=None)
# header_idx = None
# for i, row in df.iterrows():
#     val = row.iloc[0]
#     if pd.notna(val) and isinstance(val, str) and len(str(val).strip()) < 60:
#         header_idx = i
#         break
# if header_idx is not None:
#     df.columns = df.loc[header_idx]
#     df = df.loc[header_idx + 1:].reset_index(drop=True)
#
# Versao 1-linha (sem pandas): use openpyxl puro + itere nas primeiras 10
# linhas procurando a primeira com string de tamanho razoavel.

# Write CSV to Volume
# CRITICAL: dbutils.fs.put aceita STRING (nao bytes) no Free Edition 2026+!
csv_path = "/Volumes/edulake/bronze/pib_raw/pib_per_capita_2022.csv"
csv_text = f"# Converted from {target_sheet}\n"
for row in ws.iter_rows(values_only=True):
    if all(c is None for c in row):
        continue
    line = ",".join(
        f'"{str(c).replace(chr(34), chr(34)*2)}"' if c is not None and ("," in str(c) or '"' in str(c) or "\n" in str(c))
        else ("" if c is None else str(c))
        for c in row
    )
    csv_text += line + "\n"
dbutils.fs.put(csv_path, csv_text, overwrite=True)
```

**Fallback POSIX `open()`** (Free Edition 2026+ monta `/Volumes/...` via FUSE):

```python
# Funciona como ultima opcao se dbutils.fs.put der permissao
with open(csv_path, "w", encoding="utf-8") as f:
    f.write(csv_text)
```

**Then the SQL `CREATE TABLE`:**

```sql
CREATE OR REPLACE TABLE edulake.bronze.pib_municipio_raw
USING CSV
OPTIONS (
    path '/Volumes/edulake/bronze/pib_raw/pib_per_capita_2022.csv',  -- single file, not folder
    header = 'true',
    delimiter = ',',
    encoding = 'Latin-1',
    inferSchema = 'true'
);
```

## Zip extraction (the universal pattern)

INEP microdados arrive as `.zip` files in the Volume. The `CREATE TABLE` reads from the folder and can't read inside zips. Extract via Python notebook first.

**Why zip uploads are common:** a 1.5GB zipped ENEM becomes 1.2GB CSV, but the original is ~50MB. Uploading 50MB is way faster than 1.5GB. Same for Censo Escolar (~3GB CSV extracted from ~300MB zip).

**Working template (idempotent) — REVISED 2026-06-14:**

`dbutils.fs.open()` **NAO EXISTE** no Free Edition 2026+. Use este workaround (validado pelo user):

```python
import zipfile, io

zip_path = "/Volumes/edulake/bronze/enem_raw/microdados_enem_2023.zip"
target_csv = "/Volumes/edulake/bronze/enem_raw/MICRODADOS_ENEM_2023.csv"

# Idempotency: skip if already extracted
try:
    dbutils.fs.ls(target_csv)
    print("✅ Already extracted, skipping")
except:
    # dbutils.fs.open NAO EXISTE! Use Spark binary file:
    zip_bytes = spark.read.format("binaryFile").load(zip_path).first().content
    # ^ LIMIT: Free Edition 2026+ tem gRPC 128MB message limit. Zips >100MB
    # falham com SparkConnectGrpcException. Pra zips grandes (ENEM ~600MB),
    # extraia localmente e faca upload do CSV (veja "Robust extraction
    # pattern" no SKILL.md principal).
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        # Pick the CSV (some zips have .txt README + the .csv)
        csv_name = next(n for n in zf.namelist() if n.endswith(".csv"))
        with zf.open(csv_name) as src:
            csv_data = src.read()
    # Escreve via workaround: temp file + dbutils.fs.cp (nao file:/tmp,
    # que pode ser restrito no Free Edition). Use POSIX open() no path
    # /Volumes (montado via FUSE):
    with open(target_csv, "wb") as f:
        f.write(csv_data)
    print(f"✅ Extracted {target_csv}")
```

**For zip with multiple CSVs** (Censo Escolar often has escolas.csv, turmas.csv, matriculas.csv, docentes.csv):

```python
# Extract only the ones you need to save storage
essential = [n for n in zf.namelist() if any(
    kw in n.lower() for kw in ["matriculas", "escolas", "docentes"]
)]
for name in essential:
    with zf.open(name) as src, dbutils.fs.open(
        f"/Volumes/edulake/bronze/censo_raw/{os.path.basename(name)}", "wb"
    ) as dst:
        dst.write(src.read())
```

**Spark can also read zipped CSVs directly** via `spark.read.csv("path/*.zip")` but it requires `spark-csv` package and is finicky. Don't bother — extract to Volume.

## Parquet (modern datasets, Base dos Dados)

Easiest format. Spark reads natively.

```sql
CREATE OR REPLACE TABLE edulake.bronze.ideb_escola_raw
USING PARQUET
OPTIONS (
    path '/Volumes/edulake/bronze/ideb_raw/ideb_2023.parquet'
);
```

Or if you have a folder of parquet files (partitioned by year):

```sql
CREATE OR REPLACE TABLE edulake.bronze.ideb_escola_raw
USING PARQUET
OPTIONS (
    path '/Volumes/edulake/bronze/ideb_raw/'
);
```

No encoding issue (Parquet is binary), no separator issue (columnar). The only thing to watch: if the parquet was written with a different schema, `inferSchema` doesn't help — check the actual schema with `DESCRIBE TABLE` and explicitly cast columns in Phase 3 (Silver) if needed.

## Storage math (sanity check before Phase 2 commits)

Free Edition has 15GB total (DBFS + Volumes). Rough budget for a 4-source project:

| Source | Raw on disk | As Delta table | Notes |
|---|---|---|---|
| ENEM 2020-2023 (4 zips + 4 CSVs) | ~6GB | ~2GB | Columnar compression wins here |
| Censo Escolar 2023 | ~3GB | ~1.5GB | High cardinality columns compress less |
| IDEB 2023 | ~50MB | ~10MB | Small dataset |
| PIB 2022 | ~5MB | ~1MB | Small |
| **Total Bronze** | **~9GB** | **~3.5GB** | Leaves ~10GB for Silver + Gold |

If you exceed ~12GB, you need to:
- Drop 1-2 ENEM years (Censo is usually the largest, drop subset of CSVs)
- Increase `inferSchema` strictness to avoid string columns where int is expected
- Use `partitionBy` to split by year and drop old partitions

## Working smoke test (consolidated, all 4 tables)

After running all 4 `CREATE TABLE`, run this notebook cell to confirm everything:

```python
checks = [
    ("enem_participante_raw", 10_000_000, 18_000_000),  # ~14M rows expected
    ("censo_escola_raw",        5_000_000, 60_000_000),  # ~47M depending on extracted files
    ("ideb_escola_raw",          100_000,    300_000),  # ~178k schools
    ("pib_municipio_raw",          5_000,      6_500),  # ~5570 municipalities
]
for name, lo, hi in checks:
    n = spark.sql(f"SELECT COUNT(*) AS n FROM edulake.bronze.{name}").collect()[0].n
    status = "✅" if lo <= n <= hi else "⚠️"
    print(f"{status} {name}: {n:,} rows (expected {lo:,}-{hi:,})")
```

If any table returns 0 rows, the issue is usually:
- Wrong encoding (rebuild with Latin-1)
- Wrong separator (rebuild with `|` for Censo, `;` for ENEM)
- Wrong path (path doesn't match the actual upload location)
- File wasn't extracted yet (run the zip notebook first)
