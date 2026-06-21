# Databricks notebook source
# Bronze Ingest: IBGE SIDRA Population Estimates
# Stage: 01-bronze
# Dataset: ibge-sidra-population
# Generated: <fill in at runtime>

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
dbutils.widgets.text("source_path", "", "Source file path (dbfs:/Volumes/... or URL)")
dbutils.widgets.text("dataset_slug", "ibge-sidra-population", "Dataset slug")

source_path = dbutils.widgets.get("source_path")
dataset_slug = dbutils.widgets.get("dataset_slug")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Read source

# COMMAND ----------

# CSV from SIDRA -- adjust the .option() calls below if your file uses semicolon delimiter -- adjust the read call based on the source format
df_raw = (
    spark.read
    .format("csv")
    .option("header", "true")
    .option("inferSchema", "true")
    .load(source_path)
)

print(f"Source row count: {df_raw.count()}")
print(f"Source columns ({len(df_raw.columns)}):")
for c in df_raw.columns:
    print(f"  - {c}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Add ingest metadata

# COMMAND ----------

batch_id = str(uuid.uuid4())
ingestion_date = date.today().isoformat()
source_file = source_path.rsplit("/", 1)[-1]

df_bronze = (
    df_raw
    .withColumn("ingestion_date", F.lit(ingestion_date))
    .withColumn("source_file", F.lit(source_file))
    .withColumn("batch_id", F.lit(batch_id))
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Write to Bronze Volume

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
# MAGIC ## 4. Verify

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