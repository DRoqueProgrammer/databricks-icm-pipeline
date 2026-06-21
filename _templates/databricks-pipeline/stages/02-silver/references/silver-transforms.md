# Silver Transforms

Code patterns for the Silver notebook. Apply these in order; the order matters (you want to dedup before applying FK checks, because the FK table only has unique keys).

---

## 1. Read from Bronze

```python
from pyspark.sql import functions as F
from pyspark.sql.types import *
from pyspark.sql.window import Window

# Read Bronze Delta path (extracted from ../01-bronze/output/{{DATASET_SLUG}}-bronze-notebook.py)
bronze_path = "{{BRONZE_VOLUME_PATH}}/{{DATASET_SLUG}}"

df_bronze = spark.read.format("delta").load(bronze_path)
print(f"Bronze row count: {df_bronze.count()}")
```

---

## 2. Define the target schema

The target schema is the contract Silver enforces. Define it from `conventions.md` + `data-quality-rules.md`:

```python
# Required columns from Q16 of setup/questionnaire.md (or defaults if skipped)
required_columns = ["{{REQUIRED_COL_1}}", "{{REQUIRED_COL_2}}"]

# Dedup keys from Q15
dedup_keys = ["{{DEDUP_KEY_1}}", "{{DEDUP_KEY_2}}"]

# Value range rules from Q17
range_rules = {
    # column: (validation_expression_as_string, failure_message)
    "{{RANGE_COLUMN}}": ("{{VALID_VALUES_OR_RANGE}}", "{{RANGE_COLUMN}} failed validation"),
}

# Foreign keys from Q18
fk_rules = {
    # column: (referenced_table, failure_message)
    "{{FK_COLUMN}}": ("{{REFERENCED_TABLE}}", "{{FK_COLUMN}} not found in {{REFERENCED_TABLE}}"),
}
```

---

## 3. Type coercion

Apply types in one pass with `select` + `cast`. Anything that fails the cast gets sent to quarantine.

```python
from pyspark.sql.types import StructType, StructField, StringType, LongType, DoubleType, DateType, TimestampType, BooleanType, DecimalType

# Define the target schema explicitly
target_schema = StructType([
    # {{COLUMN_NAME}}: {{SPARK_TYPE}},
    StructField("{{REQUIRED_COL_1}}", StringType(), nullable=False),
    StructField("{{REQUIRED_COL_2}}", LongType(), nullable=False),
    # ... more columns
    StructField("ingestion_date", StringType(), nullable=False),
    StructField("source_file", StringType(), nullable=True),
    StructField("batch_id", StringType(), nullable=True),
])

# Cast every column. Failures land in quarantine (see step 5).
df_coerced = df_bronze
for field in target_schema.fields:
    df_coerced = df_coerced.withColumn(field.name, F.col(field.name).cast(field.dataType))
```

For boolean coercion ("yes"/"no"/"1"/"0"/"true"/"false"):

```python
df_coerced = df_coerced.withColumn(
    "{{BOOL_COLUMN}}",
    F.when(F.lower(F.col("{{BOOL_COLUMN}}")).isin("yes", "true", "1", "s", "sim"), F.lit(True))
    .when(F.lower(F.col("{{BOOL_COLUMN}}")).isin("no", "false", "0", "n", "nao", "não"), F.lit(False))
    .otherwise(F.lit(None))
)
```

For decimal coercion (Brazilian sources often use comma as decimal separator):

```python
df_coerced = df_coerced.withColumn(
    "{{DECIMAL_COLUMN}}",
    F.regexp_replace(F.col("{{DECIMAL_COLUMN}}"), ",", ".").cast(DecimalType(18, 4))
)
```

---

## 4. Deduplicate

Keep the canonical row per dedup key. First by `ingestion_date` (oldest wins; preserves history). Quarantine the rest.

```python
window = Window.partitionBy(*dedup_keys).orderBy(F.col("ingestion_date").asc())

df_with_rank = df_coerced.withColumn("_dup_rank", F.row_number().over(window))

df_deduped = df_with_rank.filter(F.col("_dup_rank") == 1).drop("_dup_rank")
df_duplicates = df_with_rank.filter(F.col("_dup_rank") > 1).drop("_dup_rank")
```

The duplicates DataFrame goes to quarantine with `_dq_failure_reason = "duplicate"`.

---

## 5. Apply DQ rules and split into kept / quarantined

This is where the magic happens. Each rule produces two DataFrames: rows that pass and rows that fail.

```python
# Start with all rows "kept"
df_kept = df_deduped
df_quarantined_all = df_duplicates.withColumn("_dq_failure_reason", F.lit("duplicate"))

# Required columns not null
for col in required_columns:
    null_mask = F.col(col).isNull()
    df_new_quarantine = df_kept.filter(null_mask).withColumn("_dq_failure_reason", F.lit(f"required_column_null:{col}"))
    df_quarantined_all = df_quarantined_all.unionByName(df_new_quarantine, allowMissingColumns=True)
    df_kept = df_kept.filter(~null_mask)

# Value range rules
for col, (validation_expr, message) in range_rules.items():
    fail_mask = ~F.expr(validation_expr)
    df_new_quarantine = df_kept.filter(fail_mask).withColumn("_dq_failure_reason", F.lit(message))
    df_quarantined_all = df_quarantined_all.unionByName(df_new_quarantine, allowMissingColumns=True)
    df_kept = df_kept.filter(~fail_mask)

# FK rules
for col, (referenced_table, message) in fk_rules.items():
    referenced_keys = spark.read.format("delta").load(referenced_table).select(F.col(col).alias("_ref_key")).distinct()
    df_with_ref = df_kept.join(referenced_keys, df_kept[col] == referenced_keys["_ref_key"], "left")
    fail_mask = F.col("_ref_key").isNull()
    df_new_quarantine = df_with_ref.filter(fail_mask).drop("_ref_key").withColumn("_dq_failure_reason", F.lit(message))
    df_quarantined_all = df_quarantined_all.unionByName(df_new_quarantine, allowMissingColumns=True)
    df_kept = df_with_ref.filter(~fail_mask).drop("_ref_key")
```

Add metadata columns to the quarantined table:

```python
df_quarantined_final = (
    df_quarantined_all
    .withColumn("_dq_failure_value", F.lit(None).cast(StringType()))  # fill in per rule if useful
    .withColumn("_dq_check_time", F.current_timestamp())
)
```

---

---

## See also

- `silver-output-and-report.md` -- writing Delta tables, the DQ report, and what Silver should NEVER do