# Auth and Credentials — Databricks Free Edition 2026+

## What works

| Method | Status | How to use |
|---|---|---|
| **OIDC federation (browser)** | ✅ Only working method for end users | Login at workspace URL → browser handles token |
| **Personal Access Token (PAT)** | ❌ Deprecated in 2026+ Free Edition. All endpoints return 401. | Don't bother. |
| **OAuth M2M (service principal)** | ❌ Premium-only. Not available. | N/A |
| **Databricks GitHub App** | ❌ Premium-only. Not available. | N/A |

## OIDC federation (the only path)

The Free Edition 2026+ workspace URL is **specific to your account**, not the generic `community.cloud.databricks.com`. It looks like:

```
https://dbc-<workspace-id>-<hash>.cloud.databricks.com/?o=<account-id>
```

Example: `https://dbc-ad8bbac7-4dce.cloud.databricks.com/?o=7474650009424249`

You log in via Google, GitHub, or Azure AD (whichever you signed up with). Databricks handles the token transparently for ~24h, then re-auth is required.

## What you CAN do with OIDC

- **SQL Editor**: works, all DDL/DQL runs (CREATE CATALOG, CREATE SCHEMA, CREATE TABLE, CREATE VOLUME, SHOW, DESCRIBE, SELECT, INSERT).
- **Workspace / Repos**: works, edit and commit `.py`/`.ipynb` files.
- **Notebooks (Python kernel)**: works, `dbutils`, `spark.sql`, `spark.read.csv` all available.
- **Lakeflow Pipelines (serverless)**: works, SQL-only declarative pipelines.

## What you CAN'T do

- **Authenticate CLI or scripts externally** — no PAT, no service principal. Only browser.
- **Trigger Databricks jobs from GitHub Actions** — no auth method available.
- **Connect Power BI via JDBC/ODBC with PAT** — same problem.

## Workaround for Power BI (Phase 5 of EduLake)

Power BI Desktop can connect to Databricks via OAuth user flow. Steps (TBD, depends on Databricks docs at the time of Phase 5):

1. Power BI Desktop → Get Data → Databricks
2. Server: `dbc-<workspace-id>-<hash>.cloud.databricks.com`
3. HTTP Path: from SQL Warehouse connection details
4. Auth: OAuth 2.0 → browser popup → login → token cached for session

## Practical tip: where to find the workspace URL

When you log in and the home page loads, the URL bar shows your full workspace URL. Save it — you'll need it for any external tool, even if you can't authenticate.

## Common errors

| Error | Cause | Fix |
|---|---|---|
| `401 Unauthorized` from any API call | Trying to use a PAT. Doesn't work. | Use OIDC via browser instead. |
| `403 Forbidden` on a workspace | Wrong workspace logged in | Check URL bar, re-login to correct workspace |
| OAuth flow loops back to login | Browser cookies from old workspace | Clear cookies, login again |

## Anti-patterns to avoid

- ❌ Generating a PAT in the UI and pasting it into `~/.databrickscfg` — the CLI will accept it but every API call will return 401
- ❌ Running `databricks auth login` interactively on Windows — the v1.3.0 CLI has bugs that leave the config in a broken state
- ❌ Trying to use a service principal — not available on Free Edition

## Reference: auth changes timeline

| Year | Auth model |
|---|---|
| Until 2025 | Community Edition with PAT (90d) + OAuth M2M (Premium) |
| 2026 (current) | Free Edition with OIDC only. PAT deprecated. |
