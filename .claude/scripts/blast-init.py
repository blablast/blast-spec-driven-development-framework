#!/usr/bin/env python3
"""
blast init — scaffold a new blast project from claude_code-template.

Usage:
    python blast-init.py <project-name> [--here] [--no-git] [--branch=BRANCH] [--from=URL]

Examples:
    python blast-init.py my-app                    # Creates ./my-app/ with blast scaffold
    python blast-init.py my-app --here             # Scaffolds into ./my-app already created
    python blast-init.py . --here                  # Scaffolds blast into the current directory
    python blast-init.py my-app --no-git           # Skip git init
    python blast-init.py my-app --branch=main      # Use main branch from template repo
    python blast-init.py my-app --from=URL         # Use a fork/mirror as template source

What it does:
    1. Validates target directory (must be empty or non-existent unless --here)
    2. git clones the template repo (default: github.com/blablast/claude_code-template) into target
    3. Removes the template's .git history
    4. Cleans personal artefacts (specs/*, INVENTORY entries, src/*, tests/*, .env, etc.)
    5. Resets steering files to clean stubs (product.md / tech.md / structure.md / INVENTORY.md)
    6. Creates a fresh .env from .env.example (with secrets blank)
    7. Initializes a fresh git repo (unless --no-git)
    8. Prints next-step guidance

Dependencies:
    Python 3.10+ (stdlib only — no pip install needed)
    git (must be on PATH)

One-liner install:
    curl -sSL https://raw.githubusercontent.com/blablast/claude_code-template/main/.claude/scripts/blast-init.py | python3 - my-app
"""

from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_TEMPLATE = "https://github.com/blablast/claude_code-template.git"
DEFAULT_BRANCH = "main"

# Files/dirs to wipe (project-specific cruft from template author's own development)
WIPE_PATHS = [
    ".blast/specs/",
    ".blast/steering/INVENTORY.md",
    ".blast/steering/RESEARCH.md",
    ".blast/knowledge/research/",
    ".blast/knowledge/decisions/",
    ".blast/knowledge/references/",
    "src/",
    "tests/",
    "CHANGELOG.md",
    "memory/",
    ".env",
    "r_and_d/",
    "MANIFEST.md",  # framework distribution metadata; user-project does not ship the framework
]
# Empty dirs to re-create after wipe (blast-internal structure that agents expect)
PLACEHOLDER_DIRS = [
    ".blast/specs/",
    ".blast/knowledge/research/",
    ".blast/knowledge/decisions/",
    ".blast/knowledge/references/",
]


# Marker prepended to every stub steering file so /blast:steering can deterministically
# detect "fresh scaffold from blast init" and route to Bootstrap Mode (ask user) instead
# of Sync Mode (infer from filesystem — which would surface CLAUDE.md/CONSTITUTION.md
# as if they were project description). Steward agent grep's for this marker.
BLAST_STUB_MARKER = "<!-- BLAST_STUB: fresh scaffold from `blast init` — replace this content via /blast:steering Bootstrap Mode -->"

# Steering files to reset to clean stubs (rather than wipe)
RESET_STEERING = {
    ".blast/steering/product.md": """# Product

## Purpose
{{PROJECT_NAME}} — describe what this project does and who it's for.

## Core Capabilities
- (define after first feature ships)

## Invariants
- (rules that must always hold — populate via /blast:complete retrospection)

## AI Guidance (domain-facing)
- (populated from validate-* findings over time)
""",
    ".blast/steering/tech.md": """# Tech

## Stack Fingerprint
- Language: (set on first /blast:steering)
- Runtime: (set on first /blast:steering)
- Package manager: (set on first /blast:steering)

## Allowed Dependencies
- (whitelist — first-class libs you've vetted)

## Canonical Commands
```bash
install: (e.g. pip install -e . / npm install)
test: (e.g. pytest -v / npm test)
lint: (e.g. ruff check / npm run lint)
typecheck: (e.g. mypy . / tsc --noEmit)
smoke: (e.g. python -c "import yourpkg")
```

## Gotchas
- (populated from incidents and lessons over time)

## Security Patterns
- URL query-string redaction at log boundaries (allowlist of safe params; redact api_key/access_token/key/secret/sig/signature by default)
- Header value sanitization before logging — strip CR/LF/control chars (CWE-117 mitigation)
- (project-specific patterns added over time)

## AI Guidance (project)
- (populated from impl/validation findings over time)
""",
    ".blast/steering/structure.md": """# Structure

## Application Code
- Pattern: `src/{module}.py` for simple features (one module per feature, flat namespace)
- Pattern: `src/{module}/` subpackage when feature delivers >3 classes OR has distinct sync/async lanes

## Tests
- Tests in `tests/`, no `__init__.py` (pytest rootdir discovery)
- Pattern: `tests/test_{feature}.py` for simple; `tests/test_{feature}/test_*.py` subdirectory ONLY if >5 test files for same feature

## Spec Artifacts
- `.blast/specs/{feature}/` — spec.json, requirements.md, design.md, tasks.md, debates/, validation/, security/

## Scripts
- `.claude/scripts/` for project automation
- `.claude/hooks/` for SDK-level enforcement
- `.claude/mcp/` for MCP server bridges
""",
    ".blast/steering/INVENTORY.md": """# INVENTORY

> Cross-spec component registry. Populated by `/blast:complete`. Do not edit by hand.

## Shipped Features

(none yet — first /blast:complete will add an entry)

## Component Registry

| Component | Type | Feature | Description |
|---|---|---|---|

## Cross-Spec Dependencies

(none yet)

## Deprecations

(none yet)
""",
}



# Targeted substitutions applied to CLAUDE.md during scaffold.
# Each entry: (old_substring, new_template_with_{{PROJECT_NAME}}).
# The original template has author-specific framing ("blast by Błażej Strus") that
# would be confusing in a fresh user project. We swap user-visible top + footer with
# project-neutral wording while keeping the universal blast operating manual sections
# (Pipeline / Smart Routing / Model routing / hooks / Multi-LLM / etc.) unchanged.
CLAUDE_TEMPLATE_PATCHES = [
    (
        """# blast — Spec-Driven Development by Błażej Strus

> **blast** = Błażej Strus' AI Development Life Cycle.
> Mój system, moje zasady, mój flow.""",
        """# {{PROJECT_NAME}} — AI instructions

> **{{PROJECT_NAME}}** uses blast — Spec-Driven Development for Claude Code.
> Spec-first. Quality-enforced. No chaos.

## Project Context

<!-- BLAST_STUB: filled by /blast:steering Bootstrap (fresh-scaffold) -->
- **Purpose**: (describe what {{PROJECT_NAME}} does and who it's for — first /blast:steering will fill this)
- **Stack**: (set on first /blast:steering)
- **Repo**: (link or local path)""",
    ),
    (
        """blast to moje podejście do programowania z AI — uporządkowane, ale bez kija w dupie.
Każda ficzerka przechodzi przez jasne fazy: od pomysłu, przez specyfikację, aż po kod.
Nie piszemy kodu w ciemno. Najpierw wiemy CO, potem JAK, a dopiero wtedy lecimy z implementacją.""",
        """blast forces order on AI-assisted development: every feature passes through clear phases — from idea, through specification, to code.
Code is never the first artifact. First you know WHAT, then HOW, then you implement.""",
    ),
    (
        "*blast by Błażej Strus — bo programowanie powinno mieć flow, nie chaos.*",
        "*Powered by blast — spec-driven AI development. See `.blast/CONSTITUTION.md` for governance principles.*",
    ),
]


def apply_claude_template(dest: Path, project_name: str) -> None:
    """Substitute author-specific framing in CLAUDE.md with project-neutral wording."""
    claude_md = dest / "CLAUDE.md"
    if not claude_md.exists():
        log("CLAUDE.md not found in scaffold; skipping template patch.", "warn")
        return

    content = claude_md.read_text(encoding="utf-8")
    applied = 0
    for old, new in CLAUDE_TEMPLATE_PATCHES:
        if old in content:
            content = content.replace(old, new.replace("{{PROJECT_NAME}}", project_name))
            applied += 1
        else:
            log(f"CLAUDE.md template patch missed (template may have drifted): {old[:60]!r}", "warn")

    claude_md.write_text(content, encoding="utf-8")
    log(f"Templated CLAUDE.md ({applied}/{len(CLAUDE_TEMPLATE_PATCHES)} substitutions, project_name={project_name}).", "ok")


def log(msg: str, level: str = "info") -> None:
    prefixes = {"info": "->", "ok": "[ok]", "warn": "[warn]", "err": "[err]"}
    stream = sys.stderr if level == "err" else sys.stdout
    print(f"{prefixes.get(level, '·')} {msg}", file=stream)


def run_git(args: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, check=check, capture_output=True, text=True)




def _rmtree_force(path: Path) -> None:
    """shutil.rmtree that survives Windows read-only files (git pack .idx, .pack).

    Git on Windows writes pack files with the read-only attribute. shutil.rmtree
    refuses to delete read-only files without an error callback that clears the
    attr and retries. Python 3.12 deprecated `onerror` in favor of `onexc`; we
    support both for compatibility with older runtimes.
    """
    def _clear_readonly_and_retry(func, p, exc_info):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except Exception:
            pass

    try:
        # Python 3.12+
        shutil.rmtree(path, onexc=_clear_readonly_and_retry)
    except TypeError:
        # Python <3.12
        shutil.rmtree(path, onerror=_clear_readonly_and_retry)


def validate_target(target: Path, here: bool) -> None:
    if here:
        if target.exists() and any(target.iterdir()):
            allowed = {".git"}
            non_allowed = [p.name for p in target.iterdir() if p.name not in allowed]
            if non_allowed:
                log(
                    f"--here used but {target} contains: {non_allowed[:5]}. "
                    f"blast init will not overwrite. Move or delete first.",
                    "err",
                )
                sys.exit(2)
    else:
        if target.exists() and any(target.iterdir()):
            log(f"Target {target} exists and is not empty. Use --here, or pick a fresh dir.", "err")
            sys.exit(2)


def clone_template(template_url: str, branch: str, dest: Path) -> None:
    log(f"Cloning template from {template_url} (branch: {branch})...")
    parent = dest.parent
    parent.mkdir(parents=True, exist_ok=True)
    proc = run_git(["clone", "--depth=1", "--branch", branch, template_url, str(dest)], check=False)
    if proc.returncode != 0:
        log(f"git clone failed: {proc.stderr}", "err")
        sys.exit(proc.returncode)
    log("Template cloned.", "ok")


def remove_template_git(dest: Path) -> None:
    git_dir = dest / ".git"
    if git_dir.exists():
        _rmtree_force(git_dir)
        log("Removed template .git/ history.", "ok")


def wipe_personal_artefacts(dest: Path) -> None:
    wiped = []
    for rel in WIPE_PATHS:
        path = dest / rel
        if path.exists():
            if path.is_dir():
                _rmtree_force(path)
            else:
                path.unlink()
            wiped.append(rel)
    if wiped:
        log(f"Wiped {len(wiped)} personal artefact paths.")




def ensure_placeholder_dirs(dest: Path) -> None:
    """Re-create empty blast-internal dirs with .gitkeep so fresh scaffold is structurally complete.

    Some dirs are removed by wipe_personal_artefacts() (they held the template author's content),
    but agents and slash commands expect them to exist as empty hosts for new artefacts. The first
    /blast:init / /blast:research would mkdir them anyway, but having them present from the start
    avoids confusion and makes git track the structure via .gitkeep stubs.
    """
    created = []
    for rel in PLACEHOLDER_DIRS:
        d = dest / rel
        d.mkdir(parents=True, exist_ok=True)
        gitkeep = d / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.write_text("", encoding="utf-8")
        created.append(rel)
    log(f"Ensured {len(created)} placeholder dirs (.gitkeep markers).", "ok")

def reset_steering(dest: Path, project_name: str) -> None:
    for rel, content in RESET_STEERING.items():
        path = dest / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        # Prepend stub marker so /blast:steering Bootstrap detection works
        body = content.replace("{{PROJECT_NAME}}", project_name)
        path.write_text(f"{BLAST_STUB_MARKER}\n{body}", encoding="utf-8")
    log(f"Reset {len(RESET_STEERING)} steering files to clean stubs (with BLAST_STUB markers for Bootstrap detection).", "ok")


def create_env_from_example(dest: Path) -> None:
    src = dest / ".env.example"
    dst = dest / ".env"
    if not src.exists():
        log(".env.example not found; skipping .env scaffold.", "warn")
        return
    if dst.exists():
        log(".env already exists; not overwriting.", "warn")
        return
    shutil.copy(src, dst)
    log("Created .env from .env.example (populate secrets manually).", "ok")


def init_fresh_git(dest: Path) -> None:
    run_git(["init", "-b", "main"], cwd=dest, check=False)
    run_git(["add", "-A"], cwd=dest, check=False)
    proc = run_git(["commit", "-m", "Initial blast scaffold"], cwd=dest, check=False)
    if proc.returncode != 0:
        log("git commit failed (likely no user.email configured); skipping initial commit.", "warn")
    else:
        log("Initialized fresh git repo with initial commit.", "ok")


def print_next_steps(dest: Path, project_name: str) -> None:
    print()
    print("=" * 60)
    print(f"  blast scaffold ready: {project_name}")
    print("=" * 60)
    print()
    print(f"Project location: {dest.absolute()}")
    print()
    print("Next steps:")
    print()
    print(f"  cd {dest}")
    print()
    print("  # 1. Populate secrets if you'll use multi-LLM debate:")
    print("  #    edit .env -> set GEMINI_API_KEY (for JURY_3_FLASH3 third juror)")
    print("  #    set BLAST_OLLAMA_UBUNTU if you have a local Ollama host")
    print()
    print("  # 2. Open in Claude Code (or your IDE) and run:")
    print("  /blast:steering           # review/customize steering for your project")
    print("  /blast:init <feature>     # initialize first feature spec")
    print('  /blast:full "<desc>" --auto --research --validate')
    print()
    print("  # 3. Read .blast/CONSTITUTION.md to understand the operating principles.")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="blast init — scaffold a new blast project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("project_name", help="Project directory name (or '.' with --here)")
    parser.add_argument("--here", action="store_true", help="Scaffold into existing directory")
    parser.add_argument("--no-git", action="store_true", help="Skip fresh git init")
    parser.add_argument("--branch", default=DEFAULT_BRANCH, help=f"Template branch (default: {DEFAULT_BRANCH})")
    parser.add_argument("--from", dest="template_url", default=DEFAULT_TEMPLATE,
                        help=f"Template repo URL (default: {DEFAULT_TEMPLATE})")

    args = parser.parse_args()

    if args.project_name == ".":
        target = Path.cwd()
        project_name = target.name
        is_here = True
    elif args.here:
        target = Path.cwd() / args.project_name
        project_name = args.project_name
        is_here = True
    else:
        target = Path.cwd() / args.project_name
        project_name = args.project_name
        is_here = False

    log(f"Project: {project_name}")
    log(f"Target: {target}")
    log(f"Template: {args.template_url} ({args.branch})")
    print()

    validate_target(target, is_here)

    if is_here:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_clone = Path(tmp) / "clone"
            clone_template(args.template_url, args.branch, tmp_clone)
            remove_template_git(tmp_clone)
            target.mkdir(parents=True, exist_ok=True)
            for item in tmp_clone.iterdir():
                dest_item = target / item.name
                if dest_item.exists():
                    log(f"Skipping existing {item.name}", "warn")
                    continue
                shutil.move(str(item), str(dest_item))
            log("Scaffold contents moved into existing directory.", "ok")
    else:
        clone_template(args.template_url, args.branch, target)
        remove_template_git(target)

    wipe_personal_artefacts(target)
    ensure_placeholder_dirs(target)
    reset_steering(target, project_name)
    apply_claude_template(target, project_name)
    create_env_from_example(target)

    if not args.no_git:
        init_fresh_git(target)

    print_next_steps(target, project_name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
