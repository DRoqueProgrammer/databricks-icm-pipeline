# Databricks notebook source
# Bronze Ingest: IBGE SIDRA Population Estimates
# Stage: 01-bronze
# Dataset: ibge-sidra-population
# Generated: 2026-06-21 (example run, simulated for end-to-end validation)

# COMMAND ----------

# MAGIC %md
# MAGIC # Bronze: IBGE SIDRA Population Estimates
# MAGIC
# MAGIC Raw ingest into `dbfs:/Volumes/ibge/ibge_sidra_population_bronze/raw/ibge-sidra-population`.
# MAGIC Schema-on-read. No transformations. Ingest metadata columns added.
# MAGIC
# MAGIC **Source**: https://sidra.ibge.gov.br/tabela/6579
# MAGIC **Run parameters**:
# MAGIC - `source_path`: where the raw file lives (Volume path or URL)
# MAGIC - `dataset_slug`: should already be ibge-sidra-population

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.types import *
import uuid
from datetime import date

# COMMAND ----------

# Widget parameters (set at notebook run time, or override via job)
dbutils.widgets.text("source_path", "dbfs:/Volumes/ibge/_uploads/sidra_6579_2024.csv", "Source file path (dbfs:/Volumes/... or URL)")
dbutils.widgets.text("dataset_slug", "ibge-sidra-population", "Dataset slug")

source_path = dbutils.widgets.get("source_path")
dataset_slug = dbutils.widgets.get("dataset_slug")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Read source
# MAGIC
# MAGIC IBGE SIDRA CSV notes:
# MAGIC - Uses `;` as delimiter (Brazilian PT-BR standard)
# MAGIC - Latin-1 encoding (ISO-8859-1)
# MAGIC - Header row at line 4 (lines 1-3 are titles/notes)
# MAGIC - First column `D1C` is state code, then `D1N` is state name, etc.

# COMMAND ----------

# CSV from SIDRA -- adjust the .option() calls below if your file uses semicolon delimiter
df_raw = (
    spark.read
    .format("csv")
    .option("header", "true")
    .option("inferSchema", "true")
    .option("sep", ";")                # IBGE SIDRA uses semicolon
    .option("encoding", "ISO-8859-1")  # Brazilian government standard
    .option("multiLine", "true")
    .option("escape", '"')
    .option("quote", '"')
    .option("mode", "PERMISSIVE")
    .option("skipRows", 3)             # SIDRA puts 3 title lines before the header
    .load(source_path)
)

print(f"Source row count: {df_raw.count()}")
print(f"Source columns ({len(df_raw.columns)}):")
for c in df_raw.columns:
    print(f"  - {c}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Rename columns to snake_case
# MAGIC
# MAGIC SIDRA uses codes like `D1C`, `D1N`, `V`. Renaming here is a Bronze-stage EXCEPTION:
# MAGIC the column NAMES are the schema, not the values. We do not rename VALUE columns
# MAGIC (we keep all V columns as-is), but we do rename the dimension columns to be readable.

# COMMAND ----------

# Map SIDRA codes to readable names. The V column stays as-is.
rename_map = {
    "D1C": "state_id",
    "D1N": "state_name",
    "D2C": "year_code",
    "D2N": "year",
    "D3C": "variable_code",
    "D3N": "variable_name",
    "D4C": "sex_code",
    "D4N": "sex",
    "MC": "measurement_code",
    "MN": "measurement_unit",
    "V": "value",
}

df_renamed = df_raw
for old, new in rename_map.items():
    if old in df_renamed.columns:
        df_renamed = df_renamed.withColumnRenamed(old, new)

print("Columns after rename:")
for c in df_renamed.columns:
    print(f"  - {c}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Add ingest metadata

# COMMAND ----------

batch_id = str(uuid.uuid4())
ingestion_date = date.today().isoformat()
source_file = source_path.rsplit("/", 1)[-1]

df_bronze = (
    df_renamed
    .withColumn("ingestion_date", F.lit(ingestion_date))
    .withColumn("source_file", F.lit(source_file))
    .withColumn("batch_id", F.lit(batch_id))
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Write to Bronze Volume

# COMMAND ----------

bronze_path = "dbfs:/Volumes/ibge/ibge_sidra_population_bronze/raw/" + dataset_slug

(
    df_bronze.write
    .format("delta")
    .mode("append")
    .partitionBy("ingestion_date")
    .save(bronze_path)
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Verify

# COMMAND ----------

df_verify = spark.read.format("delta").load(bronze_path)

print(f"Bronze table written: {bronze_path}")
print(f"Total rows in Bronze: {df_verify.count()}")
print(f"Distinct batch_ids: {df_verify.select('batch_id').distinct().count()}")
print(f"Ingestion date partitions: {df_verify.select('ingestion_date').distinct().count()}")
print(f"\nLast batch ({batch_id}):")
df_verify.filter(F.col("batch_id") == batch_id).show(10, truncate=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC - Rows ingested: <filled at runtime>
# MAGIC - Batch ID: <filled at runtime>
# MAGIC - Bronze path: dbfs:/Volumes/ibge/ibge_sidra_population_bronze/raw/ibge-sidra-population
# MAGIC
# MAGIC Next step: review this notebook, then run **Stage 02 (Silver)**.