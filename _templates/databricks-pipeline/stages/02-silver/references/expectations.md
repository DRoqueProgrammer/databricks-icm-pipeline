# Data Quality Expectations

Reference for the DQ rules Silver enforces. The actual rules per dataset live in `_config/data-quality-rules.md`. This file documents the syntax.

---

## Required columns

A required column must not be null on any row in Silver.

```python
# In the Silver notebook, this becomes:
for col in required_columns:
    null_mask = F.col(col).isNull()
    # rows where null_mask is True go to quarantine with reason "required_column_null:{col}"
```

## Type coercion success

Every column must coerce cleanly to the target schema from `_config/conventions.md`. Spark's `cast()` returns null for unparseable values (rather than throwing), so a missing or invalid value shows up as a null and lands in quarantine via the required-column check (if the column is required) or via a dedicated "type_coercion_failed" reason (if not).

```python
# Detect type coercion failures: a row where the casted value is null AND the original was not null
for field in target_schema.fields:
    if isinstance(field.dataType, (LongType, IntegerType, DoubleType, DecimalType, DateType, TimestampType)):
        original = F.col(field.name)  # the casted column -- renamed back to original name
        # Spark's cast() returns null on failure. Compare against the un-cast source if possible.
        # Simpler: count nulls after cast vs before cast
```

## Deduplication

Rows with the same `{{DEDUP_KEY_1}}` and `{{DEDUP_KEY_2}}` are duplicates. The first occurrence (by `ingestion_date`) is kept; the rest are quarantined with reason `duplicate`.

```python
window = Window.partitionBy(*dedup_keys).orderBy(F.col("ingestion_date").asc())
df_with_rank = df.withColumn("_dup_rank", F.row_number().over(window))
df_kept = df_with_rank.filter(F.col("_dup_rank") == 1)
df_quarantined = df_with_rank.filter(F.col("_dup_rank") > 1)
```

## Value range rules

A column must satisfy a documented expression. For example, `year BETWEEN 1900 AND 2100`, or `status IN ('active', 'inactive', 'pending')`.

```python
# In the Silver notebook:
range_rules = {
    "year": ("year BETWEEN 1900 AND 2100", "year out of valid range"),
    "status": ("status IN ('active', 'inactive', 'pending')", "unknown status"),
}

for col, (validation_expr, message) in range_rules.items():
    fail_mask = ~F.expr(validation_expr)
    # rows where fail_mask is True go to quarantine with message
```

## Foreign key integrity

A column's value must exist in the referenced table. Example: `state_id` must exist in the `states` reference table.

```python
# In the Silver notebook:
fk_rules = {
    "state_id": ("dbfs:/Volumes/{{CATALOG_NAME}}/reference/states_clean", "state_id not in reference table"),
}

for col, (referenced_path, message) in fk_rules.items():
    ref_df = spark.read.format("delta").load(referenced_path).select(F.col(col).alias("_ref_key")).distinct()
    df_with_ref = df.join(ref_df, df[col] == ref_df["_ref_key"], "left")
    fail_mask = F.col("_ref_key").isNull()
    # rows where fail_mask is True go to quarantine with message
```

## Custom rules

If a dataset needs a rule that doesn't fit the above categories, add it to `_config/data-quality-rules.md` as a "Custom rule" with the validation expression and message.

```python
# Example: "value must be divisible by 3"
custom_rules = [
    ("value", "value % 3 = 0", "value not divisible by 3"),
]
```

## When NOT to use this file

- Bronze stage: doesn't validate anything beyond file presence
- Gold stage: validates aggregate correctness, not row-level
- Report stage: reads the DQ report from Silver, doesn't define new rules

If you find yourself writing complex validation logic in Gold or Report, that's a smell -- move it to Silver or `_config/data-quality-rules.md`.