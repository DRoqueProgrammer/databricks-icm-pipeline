# Medallion Cheatsheet

The Bronze/Silver/Gold mental model. Every stage in this workspace assumes you've internalized this. If you're unsure what a stage should do, come back here.

---

## Bronze: "The vault of everything that landed"

**Purpose**: preserve every byte of source data, with lineage, in a queryable form. Schema-on-read.

**Mindset**: a Bronze table is a historical record. Once a row is in Bronze, you cannot "lose" it -- you can only stop reading from it.

**Rules**:
- No transformations on column values (no renaming, no type coercion, no filtering)
- Add metadata columns: `ingestion_date`, `source_file`, `batch_id`
- One Bronze table per source file or per source partition (avoid mixing unrelated sources)
- Schema is whatever the source gave you. If the source is JSON and you don't know the schema, store as `StringType` and infer in Silver.
- Partition by `ingestion_date` so old data can be dropped cheaply

**Anti-patterns**:
- Filtering rows in Bronze (you lose information)
- Renaming columns in Bronze (Silvers downstream may break)
- Aggregating in Bronze (that's Gold's job)
- Storing raw bytes when you could parse them -- if the source is small and CSV, parse it; storing raw bytes is a Bronze pattern only for large blobs

**When Bronze is done**:
- Every source file has a corresponding Bronze Delta table
- A row count exists for every table
- Lineage is queryable: "show me everything that came from `file_2024_01.csv`"

---

## Silver: "The cleaned, deduped, typed version"

**Purpose**: enforce the data contract. Same business entities, but values are consistent and types are predictable.

**Mindset**: Silver is where business rules live. "A customer ID is non-null. A date is ISO 8601. A status is one of {active, inactive, pending}." If a row breaks a rule, it goes to quarantine -- it does not silently land in Silver.

**Rules**:
- Type coercion: cast every column to the target schema from `_config/data-quality-rules.md`
- Deduplication: keep the canonical row per business key (first by `ingestion_date`)
- Null handling: required columns are not nullable; optional columns have a documented default
- Quarantine: invalid rows land in `{{QUARANTINE_VOLUME_PATH}}` with `_dq_failure_reason`
- One Silver table per Bronze source, or per business entity if multiple Bronze sources feed one entity
- Schema is strict. If a column exists in Bronze but not in the target schema, it is dropped (and noted in the DQ report)

**Anti-patterns**:
- "I'll fix the nulls later" -- no, fix them in Silver or quarantine them
- Dropping columns silently -- always log what was dropped
- Mixing business entities in one Silver table
- Aggregating in Silver -- still operational, not analytical

**When Silver is done**:
- Every Silver table has a matching DQ report in `stages/02-silver/output/`
- Quarantine tables exist for every rule that fired
- Row counts are documented: Bronze count -> Silver count (kept) + Silver count (quarantined) = Bronze count

---

## Gold: "The business questions, materialized"

**Purpose**: answer business questions. Aggregates, KPIs, dimensions. The shape matches how people query, not how the data arrived.

**Mindset**: Gold is denormalized for read performance. A Gold table is the answer to "show me X by Y by Z". If you find yourself writing a 5-table JOIN to answer a common question, that question deserves a Gold table.

**Rules**:
- One Gold table per business question (or per dashboard, if dashboards are stable)
- Aggregates are precomputed -- Gold should answer most queries in a single table scan
- Z-order on the most-queried filter columns
- Column comments describe what the column means (lineage back to Silver/Bronze lives in `_config/conventions.md`)
- Pre-joined dimensions where it makes sense (star schema)
- No raw operational data. If you need a raw row, go to Silver.

**Anti-patterns**:
- Storing raw row-level data in Gold (Silver's job)
- Multiple Gold tables that answer the same question differently
- No column comments ("revenue" of what? in what currency? gross or net?)
- Tightly coupled Gold tables -- Gold should be independent to allow dashboards to evolve separately

**When Gold is done**:
- Every Gold table has a documented grain and a documented use case
- Sample queries are in the Stage 04 report
- Z-order is configured based on observed query patterns (or sensible defaults)

---

## Mental model summary

| Layer | Job | Shape | Aggregated? | Strict schema? | Lifetime |
|-------|-----|-------|-------------|----------------|----------|
| Bronze | preserve | as-is | no | no | forever (or until retention policy) |
| Silver | enforce contract | typed + deduped | no | yes | forever (or until retention policy) |
| Gold | answer questions | aggregated + denormalized | yes | yes | until business question changes |

A common mistake is treating Silver as "small Gold". Silver is not aggregated. If you need aggregates, that's Gold.

Another common mistake is treating Bronze as "the thing we read from". Bronze is the historical record. Silver is what you read from in production.