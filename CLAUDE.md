# ~/workspaces/ -- ICM Workspace Hub

This is the user's personal collection of ICM workspaces. Each subfolder is a self-contained workspace that follows the [Interpretable Context Methodology](https://github.com/RinDig/Interpreted-Context-Methdology).

## Folder Map

```
workspaces/
├── _templates/                              (reusable workspace templates -- duplicate these)
│   ├── databricks-pipeline/                 (Bronze/Silver/Gold + report)
│   └── icm-reference/                       (read-only clone of the upstream ICM repo)
├── <dataset-slug>-pipeline/                 (a duplicated template, configured for one dataset)
├── <other-workspace>/                       (any other ICM workspace)
└── CLAUDE.md                                (this file -- Layer 0 routing)
```

## Routing

When the user mentions any of the keywords below, jump to the indicated workspace.

| Keyword / Phrase | Go To |
|------------------|-------|
| "databricks pipeline", "medallion", "bronze/silver/gold", "ingest into databricks" | `_templates/databricks-pipeline/` (or the user's most recently duplicated `<dataset>-pipeline/`) |
| "ICM", "interpretable context methodology", "build a workspace", "stage contract" | `_templates/icm-reference/` (the upstream repo -- read-only reference) |
| "setup" inside any workspace | `<workspace>/setup/questionnaire.md` |
| "status" inside any workspace | scan `<workspace>/stages/*/output/` and render the ASCII pipeline diagram |

## Template vs Active Workspace

A **template** in `_templates/` is reusable: copy it for each new dataset or project.

An **active workspace** is a duplicated template with its setup filled in (no `{{}}` placeholders remaining). Each active workspace represents one specific dataset/project.

To create an active workspace from a template:

```bash
cp -r ~/workspaces/_templates/databricks-pipeline ~/workspaces/<dataset-slug>-pipeline
cd ~/workspaces/<dataset-slug>-pipeline
# Now ask the agent to run `setup`
```

## ICM Methodology Reminders

When working inside any ICM workspace, follow the rules in `_templates/icm-reference/_core/CONVENTIONS.md`:

- **Layered context loading**: each task loads 2-8k tokens, not everything
- **One stage, one job**: each stage's CONTEXT.md defines one transformation
- **Plain text as interface**: stage handoffs are markdown files in `output/` folders
- **Every output is an edit surface**: humans review between stages
- **Configure the factory, not the product**: `setup` runs once per workspace

## Hermes-specific Notes

- `~/.hermes/skills/databricks-free-edition/` is the live skill; `_templates/databricks-pipeline/skills/databricks-free-edition/` is the bundled copy that ships with the template
- The user's AGENTS.md in `~/AppData/Local/hermes/hermes-agent/` is the Hermes core's contribution guide -- do not edit it from here
- For Free Edition operational quirks, load `shared/databricks-free-edition-gotchas.md` first (cheaper than loading the full bundled skill)
- For full Free Edition operational knowledge (CLI commands, auth flows), load `skills/databricks-free-edition/SKILL.md`

## Adding a New Workspace Template

1. Create `~/workspaces/_templates/<name>/`
2. Follow the structure in `_templates/icm-reference/_core/CONVENTIONS.md` (Layer 0 CLAUDE.md, Layer 1 CONTEXT.md, etc.)
3. Add a routing entry above so the agent knows when to jump to it
4. Document the use case in this file