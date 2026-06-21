#!/usr/bin/env python3
"""
Validate ICM workspace conventions.

Enforces (from _core/CONVENTIONS.md and the upstream ICM paper):

1. CONTEXT.md files <= 80 lines
2. Reference files (in references/ folders) <= 200 lines
3. No em dashes anywhere in our own files (use -- or - instead)
4. Every empty output/ folder has a .gitkeep
5. Template files (under _templates/) MAY contain {{}} -- this is expected
6. Active workspaces (everywhere else) MUST have NO unresolved {{}} -- setup must have run
7. Every stage CONTEXT.md has Inputs / Process / Outputs headings
8. Every .yaml file under _config/ parses

Bundled skills (anything under any skills/ folder) are exempt from em-dash
checks because they are third-party reference material copied verbatim.

Run from repo root:
    python .github/scripts/validate_icm.py

Exit code: 0 = pass, 1 = fail.
"""

import os
import re
import sys
import yaml
from pathlib import Path

# ---------- Configuration ----------

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_EXTS = {".md", ".py", ".yaml", ".yml"}
PLACEHOLDER_RE = re.compile(r"\{\{[A-Z][A-Z0-9_]*_[A-Z0-9_]+\}\}")  # requires underscore (real ICM placeholders)
EM_DASH_RE = re.compile("\u2014")  # the actual em dash character

# The literal word {{PLACEHOLDERS}} appears in docs explaining the placeholder
# system. It is not a real placeholder to be filled.
PLACEHOLDER_DOC_EXAMPLE = "{{PLACEHOLDERS}}"


def is_in_skills(path: Path) -> bool:
    """Bundled skills are third-party reference material copied verbatim.
    Exempt them from em-dash and convention checks."""
    return "skills" in path.relative_to(REPO_ROOT).parts


def is_in_icm_reference(path: Path) -> bool:
    """The _templates/icm-reference/ folder is a clone of the upstream repo.
    Skip it entirely -- it has its own conventions and we don't own it."""
    parts = path.relative_to(REPO_ROOT).parts
    return "icm-reference" in parts


def is_in_template(path: Path) -> bool:
    """Anything under _templates/databricks-pipeline/ is a template."""
    parts = path.relative_to(REPO_ROOT).parts
    if len(parts) >= 2 and parts[0] == "_templates" and parts[1] == "databricks-pipeline":
        return True
    return False


def is_setup_questionnaire(path: Path) -> bool:
    """The setup questionnaire is the SOURCE of placeholders, not a target."""
    return path.name == "questionnaire.md" and "setup" in path.relative_to(REPO_ROOT).parts


def is_setup_gotchas_doc(path: Path) -> bool:
    """The Free Edition gotchas doc documents placeholder-like strings as text."""
    return path.name == "databricks-free-edition-gotchas.md"


# ---------- Checks ----------


def line_count_check() -> list[str]:
    """CONTEXT.md <=80L, reference files <=200L."""
    issues = []
    for f in REPO_ROOT.rglob("*"):
        if not f.is_file() or f.suffix not in SCAN_EXTS:
            continue
        if is_in_icm_reference(f):
            continue
        rel = f.relative_to(REPO_ROOT)
        try:
            content = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        lines = content.count("\n") + 1

        if f.name == "CONTEXT.md" and lines > 80:
            issues.append(f"CONTEXT.md too long ({lines} lines > 80): {rel}")
        elif "/references/" in str(rel) and f.suffix == ".md" and lines > 200:
            issues.append(f"Reference file too long ({lines} lines > 200): {rel}")
    return issues


def em_dash_check() -> list[str]:
    """No em dashes in our own files. Bundled skills are exempt."""
    issues = []
    for f in REPO_ROOT.rglob("*"):
        if not f.is_file() or f.suffix not in {".md", ".py"}:
            continue
        if is_in_skills(f):
            continue
        if is_in_icm_reference(f):
            continue
        rel = f.relative_to(REPO_ROOT)
        try:
            content = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if EM_DASH_RE.search(content):
            count = len(EM_DASH_RE.findall(content))
            issues.append(f"Em dash found ({count}x): {rel}")
    return issues


def gitkeep_check() -> list[str]:
    """Every empty output/ folder must have .gitkeep."""
    issues = []
    for f in REPO_ROOT.rglob("output"):
        if not f.is_dir():
            continue
        if is_in_icm_reference(f):
            continue
        entries = [e for e in f.iterdir() if not e.name.startswith(".")]
        has_gitkeep = (f / ".gitkeep").exists()
        if not entries and not has_gitkeep:
            rel = f.relative_to(REPO_ROOT)
            issues.append(f"Empty output/ without .gitkeep: {rel}")
    return issues


def active_workspace_placeholder_check() -> list[str]:
    """Active workspaces (everywhere except _templates/) MUST have NO {{}}.

    A leftover {{}} means someone forgot to run `setup` on a new dataset."""
    issues = []
    for f in REPO_ROOT.rglob("*"):
        if not f.is_file() or f.suffix not in SCAN_EXTS:
            continue
        if is_in_template(f):
            continue  # templates are allowed to have {{}}
        if is_in_icm_reference(f):
            continue
        if is_setup_questionnaire(f):
            continue
        if is_setup_gotchas_doc(f):
            continue
        rel = f.relative_to(REPO_ROOT)
        try:
            content = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        hits = set(PLACEHOLDER_RE.findall(content))
        hits.discard(PLACEHOLDER_DOC_EXAMPLE)
        if hits:
            issues.append(f"Unresolved placeholders {sorted(hits)}: {rel}")
    return issues


def stage_shape_check() -> list[str]:
    """Every stage CONTEXT.md has Inputs / Process / Outputs headings."""
    issues = []
    for f in REPO_ROOT.rglob("CONTEXT.md"):
        if "/stages/" not in str(f):
            continue
        if is_in_icm_reference(f):
            continue
        rel = f.relative_to(REPO_ROOT)
        try:
            content = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        missing = [h for h in ("## Inputs", "## Process", "## Outputs") if h not in content]
        if missing:
            issues.append(f"Stage CONTEXT.md missing sections {missing}: {rel}")
    return issues


def yaml_check() -> list[str]:
    """Every .yaml / .yml file under _config/ parses."""
    issues = []
    for f in REPO_ROOT.rglob("*"):
        if not f.is_file() or f.suffix not in {".yaml", ".yml"}:
            continue
        if "/_config/" not in str(f):
            continue
        if is_in_icm_reference(f):
            continue
        rel = f.relative_to(REPO_ROOT)
        try:
            content = f.read_text(encoding="utf-8")
            yaml.safe_load(content)
        except yaml.YAMLError as e:
            issues.append(f"Invalid YAML in {rel}: {e}")
        except UnicodeDecodeError:
            continue
    return issues


def main() -> int:
    checks = [
        ("Line count (CONTEXT.md <=80, references <=200)", line_count_check),
        ("Em dash avoidance (bundled skills exempt)", em_dash_check),
        ("Empty output/ folders have .gitkeep", gitkeep_check),
        ("Active workspaces have NO unresolved {{}}", active_workspace_placeholder_check),
        ("Every stage CONTEXT.md has Inputs/Process/Outputs", stage_shape_check),
        ("_config/*.yaml is valid YAML", yaml_check),
    ]

    report_lines = []
    total_issues = 0
    failed_checks = 0

    for name, check_fn in checks:
        issues = check_fn()
        status = "PASS" if not issues else f"FAIL ({len(issues)} issues)"
        report_lines.append(f"[{status}] {name}")
        for issue in issues[:20]:  # cap per-check output
            report_lines.append(f"    - {issue}")
        if len(issues) > 20:
            report_lines.append(f"    ... and {len(issues) - 20} more")
        if issues:
            total_issues += len(issues)
            failed_checks += 1

    print("\n".join(report_lines))

    (REPO_ROOT / ".icm-validation-report.txt").write_text(
        "\n".join(report_lines), encoding="utf-8"
    )

    print(f"\n=== Summary: {total_issues} issue(s) across {failed_checks}/{len(checks)} check(s) ===")
    return 1 if total_issues > 0 else 0


if __name__ == "__main__":
    sys.exit(main())