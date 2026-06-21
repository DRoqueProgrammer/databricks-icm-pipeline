# Bronze Ingest Patterns

Code patterns for the most common ingest sources. The Bronze notebook uses one of these (or a combination) depending on what the user provides.

---

## CSV (most common)

```python
from pyspark.sql import functions as F
from pyspark.sql.types import *
import uuid
from datetime import date

# Widget parameters (set at notebook run time)
dbutils.widgets.text("source_path", "", "Source CSV path in Volume")
dbutils.widgets.text("dataset_slug", "{{DATASET_SLUG}}", "Dataset slug")

source_path = dbutils.widgets.get("source_path")
dataset_slug = dbutils.widgets.get("dataset_slug")

# Read with schema inference (Bronze is schema-on-read)
df = (
    spark.read
    .format("csv")
    .option("header", "true")
    .option("inferSchema", "true")
    .option("multiLine", "true")        # for CSVs with embedded newlines in quoted fields
    .option("escape", '"')
    .option("quote", '"')
    .option("mode", "PERMISSIVE")       # don't fail on bad rows; quarantine in Silver
    .load(source_path)
)

# Add ingest metadata
batch_id = str(uuid.uuid4())
df_bronze = (
    df
    .withColumn("ingestion_date", F.lit(date.today().isoformat()))
    .withColumn("source_file", F.lit(source_path.rsplit("/", 1)[-1]))
    .withColumn("batch_id", F.lit(batch_id))
)

# Write to Bronze Volume as Delta
bronze_path = "{{BRONZE_VOLUME_PATH}}/" + dataset_slug
(
    df_bronze.write
    .format("delta")
    .mode("append")
    .partitionBy("ingestion_date")
    .save(bronze_path)
)

print(f"Bronze ingest complete: {df_bronze.count()} rows written to {bronze_path}")
print(f"Batch ID: {batch_id}")
```

---

## JSON (line-delimited or array)

```python
# Line-delimited JSON (one JSON object per line)
df = spark.read.format("json").option("multiLine", "false").load(source_path)

# JSON array (single root array)
df = spark.read.format("json").option("multiLine", "true").load(source_path)

# Nested JSON -- flatten in Silver, not Bronze. Store as StringType here if schema unknown.
```

---

## Parquet

```python
df = spark.read.format("parquet").load(source_path)
```

Parquet already carries schema, so no inference needed. Bronze is essentially a copy with metadata.

---

## Excel (.xlsx)

Excel is the trickiest source. Always read via `pandas` first to detect the header row, then convert to Spark.

```python
import pandas as pd
from pyspark.sql import SparkSession

spark = SparkSession.builder.getOrCreate()

# pandas infers the header row -- real xlsx often has a title row above
df_raw = pd.read_excel(source_path, header=None)

# Detect header: first row with string cells under 60 chars
header_row_idx = 0
for i, row in df_raw.iterrows():
    cell = str(row.iloc[0])
    if cell and len(cell) < 60 and not cell.isdigit() and cell != "nan":
        header_row_idx = i
        break

df_pandas = pd.read_excel(source_path, header=header_row_idx)

# Coerce column names to snake_case and remove whitespace
df_pandas.columns = [
    c.strip().lower().replace(" ", "_").replace("-", "_")
    for c in df_pandas.columns
]

# Convert to Spark
df = spark.createDataFrame(df_pandas)

# Then add Bronze metadata as in the CSV pattern
```

If the file is large (>100k rows), chunk the pandas read with `pd.read_excel(..., chunksize=...)` and concatenate the Spark DataFrames. For really large files, ask the user to export as CSV.

---

## API / HTTP source

```python
import requests
import json

response = requests.get(source_url, headers={"Accept": "application/json"})
response.raise_for_status()
data = response.json()

# If it's a JSON array, normalize to rows
if isinstance(data, list):
    pdf = pd.DataFrame(data)
elif isinstance(data, dict):
    # Often the payload is {"data": [...], "meta": {...}}
    for key in ("data", "results", "items", "records"):
        if key in data and isinstance(data[key], list):
            pdf = pd.DataFrame(data[key])
            break
    else:
        # Single object, treat as one row
        pdf = pd.DataFrame([data])
else:
    raise ValueError(f"Unexpected JSON shape from {source_url}")

df = spark.createDataFrame(pdf)
```

For Brazilian public APIs (IBGE SIDRA, Brasil.IO), check if a Spark connector exists before pulling all data through pandas. Brasil.IO has a `basedosdados` package that can stream into BigQuery/Databricks directly.

---

## Multiple files (a directory)

```python
df = (
    spark.read
    .format("csv")
    .option("header", "true")
    .option("inferSchema", "true")
    .load(f"{bronze_path}/*.csv")   # glob
)

# Each row's source_file column should reflect the actual file it came from
df = df.withColumn("source_file", F.input_file_name())
```

---

## Existing Delta table (re-ingest / merge)

```python
# If the Bronze Delta table already exists, append. If the schema changed, you may need:
df_existing = spark.read.format("delta").load(bronze_path)
df_new_schema = df_existing.schema

# Apply the same schema to incoming data
df_incoming = spark.read.format("csv").schema(df_new_schema).load(new_source_path)
```

---

---

## See also

- `bronze-pitfalls.md` -- common pitfalls and what Bronze should NEVER do