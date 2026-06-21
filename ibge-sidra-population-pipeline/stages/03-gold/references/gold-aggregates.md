# Gold Aggregates

Code patterns for the Gold notebook. Gold's job is to materialize business questions as pre-aggregated, denormalized, Z-ordered Delta tables.

---

## 1. Read from Silver

```python
from pyspark.sql import functions as F
from pyspark.sql.window import Window

# Read Silver Delta path (extracted from ../02-silver/output/ibge-sidra-population-silver-notebook.py)
silver_path = "dbfs:/Volumes/ibge/ibge_sidra_population_silver/cleansed/ibge-sidra-population_clean"

df_silver = spark.read.format("delta").load(silver_path)
print(f"Silver row count: {df_silver.count()}")
```

---

## 2. Define aggregates

Each aggregate is a separate DataFrame. Define them all in one block before writing, so the human can review them together at the checkpoint.

```python
# Aggregate 1: by_state_year -- one row per (state, year)
agg_1 = (
    df_silver
    .groupBy("state_id", "year")
    .agg(
        F.sum("population").alias("total_population"),
        F.count("*").alias("row_count"),
        F.avg("population").alias("avg_population"),
        F.min("population").alias("min_population"),
        F.max("population").alias("max_population"),
    )
    .withColumn("last_updated", F.current_timestamp())
)

# Aggregate 2: yearly_summary -- one row per year
agg_2 = (
    df_silver
    .groupBy("year")
    .agg(
        F.sum("population").alias("total_population"),
        F.countDistinct("state_id").alias("state_count"),
    )
    .withColumn("last_updated", F.current_timestamp())
)

# Aggregate 3: top_states_overall -- one row per state, ranked by total population
state_totals = df_silver.groupBy("state_id").agg(F.sum("population").alias("total_population"))
window = Window.orderBy(F.desc("total_population"))
agg_3 = (
    state_totals
    .withColumn("rank", F.row_number().over(window))
    .withColumn("last_updated", F.current_timestamp())
)

aggregates = {
    "by_state_year": agg_1,
    "yearly_summary": agg_2,
    "top_states_overall": agg_3,
}
```

---

## 3. Write each aggregate with column comments

Column comments are critical for downstream consumers. Add them via the `CREATE TABLE` DDL or via `ALTER TABLE`.

```python
for name, df in aggregates.items():
    gold_path = f"dbfs:/Volumes/ibge/ibge_sidra_population_gold/aggregates/{name}"

    # Write the data
    (
        df.write
        .format("delta")
        .mode("overwrite")
        .save(gold_path)
    )

    # Add column comments
    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS ibge.ibge_sidra_population_gold.{name}
        USING DELTA
        LOCATION '{gold_path}'
    """)

    for col in df.columns:
        comment = COLUMN_COMMENTS.get((name, col), f"Column {col} from aggregate {name}")
        spark.sql(f"""
            ALTER TABLE ibge.ibge_sidra_population_gold.{name}
            ALTER COLUMN {col} COMMENT '{comment}'
        """)

    # Z-order
    zorder_cols = ZORDER_COLUMNS.get(name, [])
    if zorder_cols:
        spark.sql(f"OPTIMIZE ibge.ibge_sidra_population_gold.{name} ZORDER BY ({', '.join(zorder_cols)})")

    print(f"Wrote {name}: {df.count()} rows, Z-ordered by {zorder_cols}")

# Define the comments and Z-order columns at the top
COLUMN_COMMENTS = {
    ("by_state_year", "state_id"): "IBGE state code (e.g. 35 = SP)",
    ("by_state_year", "year"): "Reference year",
    ("by_state_year", "total_population"): "Sum of population for this state-year",
    # ...
}

ZORDER_COLUMNS = {
    "by_state_year": ["state_id", "year"],
    "yearly_summary": ["year"],
    "top_states_overall": ["rank"],
}
```

---

## 4. Verify

```python
# Read back and confirm each aggregate
for name in aggregates.keys():
    gold_path = f"dbfs:/Volumes/ibge/ibge_sidra_population_gold/aggregates/{name}"
    df_verify = spark.read.format("delta").load(gold_path)
    print(f"\n=== {name} ===")
    print(f"Rows: {df_verify.count()}")
    df_verify.show(5, truncate=False)
```

---

## Common aggregate shapes

| Question | Aggregate shape | Example |
|----------|-----------------|---------|
| "Total X by Y" | `groupBy(Y).sum(X)` | Population by state |
| "Average X by Y and Z" | `groupBy(Y, Z).avg(X)` | Avg revenue by region and month |
| "Top N X" | `groupBy(X).sum(measure)` + `rank` | Top 10 customers by revenue |
| "Time series" | `groupBy(date_trunc).sum(measure)` | Monthly active users |
| "Cohort" | `groupBy(cohort_col, period_col).agg(...)` | Retention by signup month |
| "Distribution" | `groupBy(bucket).count()` | Order value distribution |

## Denormalization patterns

If Gold joins Silver with a reference table (e.g. `states`), do it once at Gold time and store the result. Do not make downstream queries do the join.

```python
# Reference table example: states metadata
states_df = spark.read.format("delta").load("dbfs:/Volumes/ibge/reference/states_clean")

# Denormalize in Gold
agg_denormalized = (
    df_silver
    .join(states_df, on="state_id", how="left")
    .select(
        df_silver["*"],
        states_df["state_name"],
        states_df["region"],
        states_df["capital"],
    )
)
```

## Pitfalls

- **Accidental fanout from joins**: a join with a many-side reference table will multiply rows. Check row count before and after.
- **Z-order too many columns**: Z-order on >4 columns is slow and rarely helpful. Pick the most-queried 1-3.
- **Missing column comments**: downstream consumers (and your future self) won't know what `revenue` means.
- **Aggregating too early**: if you find yourself aggregating an aggregate, that's a smell -- go back to Silver.
- **Gold dependencies**: Gold should not depend on other Gold tables. Each aggregate is computed from Silver (or from a reference table).

---

## What Gold should NEVER do

- Contain raw, row-level operational data (Silver's job)
- Depend on other Gold tables (creates cascade of rebuilds)
- Be queried for "the latest raw data" (use Silver for that)
- Have undocumented columns
- Be the only place business logic lives (document in `conventions.md`)