# Databricks notebook source
# Creates N Unity Catalog Volumes in a given schema (default: edulake.bronze).
# Idempotent: CREATE VOLUME IF NOT EXISTS skips if exists.
# Run as a Python notebook (dbutils is required).

# COMMAND ----------

# Customize these
CATALOG = "edulake"
SCHEMA = "bronze"
VOLUMES = [
    f"{CATALOG}.{SCHEMA}.enem_raw",   # CSV Latin-1, sep=';'
    f"{CATALOG}.{SCHEMA}.censo_raw",  # CSV Latin-1, sep='|'
    f"{CATALOG}.{SCHEMA}.ideb_raw",   # parquet
    f"{CATALOG}.{SCHEMA}.pib_raw",    # XLSX converted to CSV
]

# COMMAND ----------

# Step 1: ensure the schema exists (skip if catalog/schema don't exist yet)
print(f"Ensuring schema {CATALOG}.{SCHEMA} exists...")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
print(f"✅ Schema {CATALOG}.{SCHEMA} ready")

# COMMAND ----------

# Step 2: create each Volume
for vol in VOLUMES:
    print(f"Creating Volume {vol}...")
    spark.sql(f"CREATE VOLUME IF NOT EXISTS {vol}")
    print(f"✅ {vol}")

# COMMAND ----------

# Step 3: list all Volumes to confirm
print("\n=== Volumes in", f"{CATALOG}.{SCHEMA}", "===")
spark.sql(f"SHOW VOLUMES IN {CATALOG}.{SCHEMA}").show(truncate=False)

# COMMAND ----------

# Step 4: print upload paths for the UI
print("\n=== Upload paths (for Databricks UI File > Upload data) ===")
for vol in VOLUMES:
    path = f"/Volumes/{vol.replace('.', '/')}/"
    print(f"  {path}")
