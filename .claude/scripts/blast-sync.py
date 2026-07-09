#!/usr/bin/env python3
"""
blast-sync — update an EXISTING blast project's framework files from this repo.

blast ships `init` (fresh scaffold) but has no `update`. This propagates framework
improvements into an existing project WITHOUT clobbering project-owned content
(your specs, your steering, your .env, your settings).

Run it FROM the framework repo (this file's repo); point it at your project:

  python .claude/scripts/blast-sync.py --into /path/to/my-project            # DRY-RUN (default)
  python .claude/scripts/blast-sync.py --into /path/to/my-project --apply     # do it (backs up)

Classification (source of truth: blast-init's WIPE/RESET lists):

  FRAMEWORK  → overwritten (old copy backed up under .blast/.sync-backups/<ts>/):
      .claude/{hooks,mcp,scripts,agents,commands,skills}, .blast/settings,
      .blast/{CONSTITUTION,CLAUDE.snippet,README}.md
  CUSTOMIZABLE → written as `<file>.new` sidecar (YOU merge — never auto-overwritten):
      .blast/steering/llm-routing.md, .blast/steering/cost-policy.md,
      .blast/.env.example, .blast/knowledge/references/*
  PROJECT-OWNED → never touched:
      .blast/specs, your steering (product/tech/structure/INVENTORY/RESEARCH/lessons),
      .blast/.env, .claude/settings*.json, CLAUDE.md, src, tests, .priv, .git, memory

Exit: 0 = ok (or dry-run), 1 = error, 2 = applied with sidecars needing manual merge.
"""

from __future__ import annotations

import argparse
import datetime as dt
import filecmp
import shutil
import sys
from pathlib import Path

FRAMEWORK_DIRS = [
    ".claude/hooks", ".claude/mcp", ".claude/scripts",
    ".claude/agents", ".claude/commands", ".claude/skills",
    ".blast/settings",
]
FRAMEWORK_FILES = [
    ".blast/CONSTITUTION.md", ".blast/CLAUDE.snippet.md", ".blast/README.md",
]
# Framework-provided but project-customizable → sidecar, never auto-overwrite.
CUSTOMIZABLE_FILES = [
    ".blast/steering/llm-routing.md", ".blast/steering/cost-policy.md", ".blast/.env.example",
]
CUSTOMIZABLE_DIRS = [".blast/knowledge/references"]

SKIP_NAMES = {"__pycache__"}
SKIP_SUFFIXES = {".pyc"}


def log(msg: str) -> None:
    print(msg)


def iter_files(root: Path):
    for p in sorted(root.rglob("*")):
        if p.is_dir():
            continue
        if any(part in SKIP_NAMES for part in p.parts):
            continue
        if p.suffix in SKIP_SUFFIXES:
            continue
        yield p


def main() -> int:
    ap = argparse.ArgumentParser(description="Update an existing blast project's framework files.")
    ap.add_argument("--into", required=True, help="path to the existing project to update")
    ap.add_argument("--from", dest="src", default=None, help="framework repo root (default: this repo)")
    ap.add_argument("--apply", action="store_true", help="perform changes (default: dry-run)")
    args = ap.parse_args()

    src = Path(args.src).resolve() if args.src else Path(__file__).resolve().parent.parent.parent
    dest = Path(args.into).resolve()

    if not (src / ".blast").exists():
        log(f"[blast-sync] ERROR: source {src} doesn't look like a blast repo (no .blast/)."); return 1
    if not dest.exists():
        log(f"[blast-sync] ERROR: target {dest} does not exist."); return 1
    if not (dest / ".blast").exists():
        log(f"[blast-sync] ERROR: target {dest} has no .blast/ — is it a blast project? Use blast-init for a fresh one."); return 1
    if src == dest:
        log("[blast-sync] ERROR: source and target are the same directory."); return 1

    mode = "APPLY" if args.apply else "DRY-RUN"
    ts = dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    backup_root = dest / ".blast" / ".sync-backups" / ts

    to_overwrite: list[tuple[Path, Path]] = []   # (src_file, rel)
    to_add: list[Path] = []                       # rel (new framework file)
    to_sidecar: list[Path] = []                   # rel (customizable, differs)
    unchanged = 0

    # collect framework source files
    fw_sources: list[Path] = []
    for d in FRAMEWORK_DIRS:
        sd = src / d
        if sd.exists():
            fw_sources.extend(iter_files(sd))
    for f in FRAMEWORK_FILES:
        sf = src / f
        if sf.is_file():
            fw_sources.append(sf)

    for sf in fw_sources:
        rel = sf.relative_to(src)
        df = dest / rel
        if not df.exists():
            to_add.append(rel)
        elif filecmp.cmp(sf, df, shallow=False):
            unchanged += 1
        else:
            to_overwrite.append((sf, rel))

    # customizable: sidecar if exists+differs, plain-add if missing
    cust_sources: list[Path] = []
    for f in CUSTOMIZABLE_FILES:
        sf = src / f
        if sf.is_file():
            cust_sources.append(sf)
    for d in CUSTOMIZABLE_DIRS:
        sd = src / d
        if sd.exists():
            cust_sources.extend(iter_files(sd))
    for sf in cust_sources:
        rel = sf.relative_to(src)
        df = dest / rel
        if not df.exists():
            to_add.append(rel)
        elif filecmp.cmp(sf, df, shallow=False):
            unchanged += 1
        else:
            to_sidecar.append(rel)

    # ---- report ----
    log(f"[blast-sync] {mode}  src={src}  →  dest={dest}")
    log(f"[blast-sync] framework: {len(to_add)} new, {len(to_overwrite)} updated, {unchanged} unchanged; "
        f"{len(to_sidecar)} customizable file(s) differ → sidecar.")
    for rel in to_add:
        log(f"  + add       {rel}")
    for _, rel in to_overwrite:
        log(f"  ~ update    {rel}   (backup → .blast/.sync-backups/{ts}/)")
    for rel in to_sidecar:
        log(f"  ⚠ sidecar   {rel}.new   (MERGE manually — your version kept)")

    if not args.apply:
        log("\n[blast-sync] DRY-RUN — nothing written. Re-run with --apply to perform the update.")
        log("[blast-sync] Project-owned files (specs, your steering, .env, settings, CLAUDE.md) are never touched.")
        return 0

    # ---- apply ----
    for sf, rel in to_overwrite:
        df = dest / rel
        bak = backup_root / rel
        bak.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(df, bak)
        shutil.copy2(sf, df)
    for rel in to_add:
        sf = src / rel
        df = dest / rel
        df.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(sf, df)
    for rel in to_sidecar:
        sf = src / rel
        df = dest / (str(rel) + ".new")
        df.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(sf, df)

    log(f"\n[blast-sync] APPLIED. {len(to_add)} added, {len(to_overwrite)} updated "
        f"(backups in .blast/.sync-backups/{ts}/), {len(to_sidecar)} sidecar(s) written.")
    if to_sidecar:
        log("[blast-sync] ACTION NEEDED — merge these into your versions, then delete the .new files:")
        for rel in to_sidecar:
            log(f"    diff {rel} {rel}.new")
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        print(f"[blast-sync] ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
