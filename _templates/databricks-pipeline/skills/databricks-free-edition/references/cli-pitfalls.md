# Databricks CLI v1.3.0 — Known Bugs and Workarounds

The Databricks CLI on Windows is a minefield. Here's what to expect and how to dodge it.

## The bugs

### 1. `databricks auth login` is broken on Windows

The v1.3.0 CLI tries to use Windows Credential Manager as the default token storage. The flow:

1. CLI prompts for host → you enter
2. CLI prompts for token → you paste
3. CLI claims "Profile DEFAULT successfully configured"
4. Next command: CLI tries to read the token from Cred Mgr → returns **EOF** or "no configuration file found"
5. You're stuck

**Workaround:** write `~/.databrickscfg` manually. See `auth-and-credentials.md` for the syntax.

### 2. POST requests return EOF

Any `databricks <command> --json '{...}'` POST request fails with `EOF` even when the JSON is valid. This affects:
- `databricks catalogs create --json '{...}'`
- `databricks schemas create --json '{...}'`
- `databricks api post /some/endpoint` (sometimes)

**Workaround:** use `databricks api get` for read operations, and do writes via the Databricks UI or via a Python notebook using `spark.sql(...)`. Don't trust the CLI for catalog/schema/table creation.

### 3. Two CLI versions in PATH

If you installed via `winget`, you have:
- `C:\Users\<user>\AppData\Local\Microsoft\WinGet\Packages\Databricks.DatabricksCLI_Microsoft.Winget.Source_8wekyb3d8bbwe\databricks.exe` (v1.3.0)
- `C:\Users\<user>\.local\bin\databricks.exe` (v0.18.0, default in PATH)

Both work, but v0.18.0 doesn't have some v1.3.0 commands. To avoid the "Executing CLI v1.3.0" warning, use the absolute path to v1.3.0:

```bash
DB="/c/Users/<user>/AppData/Local/Microsoft/WinGet/Packages/Databricks.DatabricksCLI_Microsoft.Winget.Source_8wekyb3d8bbwe/databricks.exe"
$DB auth profiles
```

Or add an alias to `~/.bashrc`:
```bash
alias db='/c/Users/<user>/AppData/Local/Microsoft/WinGet/Packages/Databricks.DatabricksCLI_Microsoft.Winget.Source_8wekyb3d8bbwe/databricks.exe'
```

### 4. `auth_type = pat` config doesn't always work

Setting `auth_type = pat` in `~/.databrickscfg` is supposed to force PAT auth, but the CLI sometimes ignores it and tries OIDC anyway, then fails with "cannot configure default credentials".

**Workaround:** omit `auth_type` entirely. Let the CLI auto-detect from the presence of a `token` field. The config that works:

```ini
[DEFAULT]
host = https://dbc-xxx.cloud.databricks.com
token = dapi...
```

(Without `auth_type`.)

### 5. `databricks sql execute` doesn't exist in v1.3.0

There's no top-level `databricks sql execute` command. To run SQL, use:
- SQL Editor in the UI (recommended)
- A Python notebook with `spark.sql("...")`
- The Databricks SDK for Python in a script

## When the CLI is the right tool

Despite the bugs, the CLI works for:
- `databricks catalogs list` (GET, works)
- `databricks schemas list <catalog>` (GET, works)
- `databricks volumes list <catalog>.<schema>` (GET, works)
- `databricks api get /api/2.0/...` (GET only)
- `databricks auth profiles` (table output, works)

For everything else, **use the UI or a Python notebook**.

## Diagnostic recipe when something fails

1. Check the CLI version: `databricks --version`
2. Try with `--log-level=debug` to see what the CLI is doing under the hood
3. Check `~/.databrickscfg` exists and has only one `[DEFAULT]` block
4. Check the host is the workspace-specific URL, not `community.cloud.databricks.com` (the generic alias)
5. If all else fails, run via UI or notebook

## When to give up on the CLI entirely

If the user is on Free Edition 2026+ and only needs to:
- Run SQL (DDL/DQL)
- Upload files
- Read file contents
- Check workspace state

…do everything via the UI or Python notebooks. The CLI is only useful for **automated workflows** (CI/CD, scripted refreshes) — and Free Edition doesn't have a clean way to authenticate those anyway.

## Reference

- [Databricks CLI installation](https://docs.databricks.com/en/dev-tools/cli/install.html)
- [Authentication for the Databricks CLI](https://docs.databricks.com/en/dev-tools/cli/authentication.html)
