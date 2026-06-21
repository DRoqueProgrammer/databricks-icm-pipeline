-- Idempotent DDL for Databricks Free Edition 2026+ workspace.
-- Run in SQL Editor connected to a SQL Warehouse.
-- Idempotent: IF NOT EXISTS everywhere, safe to re-run.
--
-- Replace <catalog_name> and <schema_names> with your values.

-- COMMAND ----------

-- Create catalog (only if your account has CREATE CATALOG privilege)
CREATE CATALOG IF NOT EXISTS <catalog_name>
    COMMENT 'Lakehouse for <project name>';

-- COMMAND ----------

-- Create schemas (Bronze/Silver/Gold or your own layer names)
CREATE SCHEMA IF NOT EXISTS <catalog_name>.bronze
    COMMENT 'Raw layer — unprocessed data ingested via UI or pipelines';

CREATE SCHEMA IF NOT EXISTS <catalog_name>.silver
    COMMENT 'Cleaned layer — DLT with expectations, deduplicated, conformed';

CREATE SCHEMA IF NOT EXISTS <catalog_name>.gold
    COMMENT 'Modeled layer — star schema for BI consumption';

-- COMMAND ----------

-- Validation: should return 3 rows
SHOW SCHEMAS IN <catalog_name>;
