# Databricks notebook authoring — gotchas when committing .py to git

When you put a Databricks notebook (`.py`) under git for sync via Repos, two
non-Python quirks will trip you and your linter. Captured here from real
session pain (EduLake BR Phase 2, 2026-06-14).

## 1. The first line must be `# Databricks notebook source`

Without it, Databricks won't recognize the file as a notebook when you open it
from Repos (it shows as a plain Python file, not a runnable cell). Always add
this as line 1 of every notebook you commit.

```python
# Databricks notebook source
# My Notebook — does X
# COMMAND ----------

# Cell 1
print("hello")
```

## 2. `# COMMAND ----------` is a cell separator (Databricks magic)

It tells the Databricks runtime "the cell ends here, next thing is a new cell".
It does NOT trigger the Python interpreter. But many linters (ruff, pylint)
will flag it as weird. Linters also flag the `subprocess.run(...)` patterns
you end up using as a workaround for `dbutils.fs.open` not existing on
Free Edition 2026+.

**Mitigation:** in your `pyproject.toml`, exclude the notebook path from
Python linting with a per-file-ignores rule:

```toml
[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP"]
ignore = ["E501", "E402", "F821", "B007"]

[tool.ruff.lint.per-file-ignores]
# Databricks notebooks usam # COMMAND ---------- pra separar celulas e %pip install
# pra instalar dependencias em runtime -- nao e Python puro, linter deve ignorar.
"databricks/notebooks/**/*.py" = ["E402", "F821", "B007", "E999"]
```

The errors you'll hit and why they're ignored:

- `E999` (syntax) — raised by `# COMMAND ----------` and `%pip install`,
  which are not valid Python syntax
- `F821` (undefined name) — `dbutils`, `spark` are undefined in plain
  Python (they're injected by the Databricks runtime)
- `B007` (unused loop variable) — common in shell-wrapper patterns
- `E402` (module-level import not at top) — common in notebook cell order

## 3. `%pip install openpyxl` is a Databricks cell magic

It works inside a notebook cell, but if you copy/paste it into a plain `.py`
file in git, Python's parser rejects it as a `SyntaxError` on the `%`. If you
need the notebook file to also be valid Python (for tooling, linting,
testing), replace `%pip install` with:

```python
import subprocess
subprocess.run(["pip", "install", "openpyxl"], check=True, capture_output=True)
import openpyxl
```

This works in both Databricks runtime and plain Python. The trade-off is you
don't get the nice progress UI of `%pip install`, but you also don't break
linting.

## 4. `subprocess.run` vs `%pip install` — when to use which

- **Use `%pip install`** when the notebook is purely a Databricks artifact
  (lives in Repos, never run as plain Python). This gives a progress bar
  and installs to the notebook-scoped environment.
- **Use `subprocess.run(["pip", "install"])`** when the notebook is
  source-of-truth in git AND you want it to be testable/lintable from
  CI. This also works in Databricks runtime.

## 5. File extensions matter

`.py` files in `databricks/notebooks/` are treated as Databricks notebooks
by Repos. The `subprocess.run` call also runs in Databricks runtime (the
notebook kernel is just Python). Don't try to use `.ipynb` — Databricks
imports `.ipynb` but the diffs are unreadable in git, and you can't run
them in CI without `papermill` or similar.

## 6. Common patterns that work in Databricks runtime but break linter

| Pattern | Why it breaks linter | Workaround |
|---|---|---|
| `dbutils.fs.ls(...)` | `dbutils` undefined in plain Python | `F821` per-file-ignore |
| `spark.read.csv(...)` | `spark` undefined in plain Python | `F821` per-file-ignore |
| `# COMMAND ----------` | Not valid Python | `E999` per-file-ignore |
| `%pip install X` | `%` not valid Python | Use `subprocess.run(["pip", "install", "X"])` |
| `display(df)` | `display` is Databricks magic | `E999` if linter strict, otherwise fine |

## 7. Session-cost lesson learned

We tried three iterations on the same notebook in one session because of
these gotchas:

1. First version used `dbutils.fs.open(path, "rb")` — failed with
   `AttributeError: 'RemoteFsHandler' object has no attribute 'open'`
2. Second version used `spark.read.format("binaryFile").load(path)` —
   failed with `RESOURCE_EXHAUSTED` gRPC limit (600MB zip > 128MB limit)
3. Third version used `subprocess.run(["pip", "install", "openpyxl"])` +
   local `tempfile` + `dbutils.fs.cp` — finally worked

The third pattern is now in `templates/02_extract_uploads.py` as the
canonical "extract small files via Databricks notebook" pattern. For files
> 100MB, skip the notebook entirely and extract on the user's local
machine (see `templates/` README and the main SKILL.md "Robust extraction
pattern" section).
