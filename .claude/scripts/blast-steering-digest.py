#!/usr/bin/env python3
"""
blast-steering-digest — condense .blast/steering/*.md into one short digest.

Problem (§5): "Read the entire .blast/steering/ directory" appears in ~6 agents;
in a mature project that's 1–2k lines re-tokenized 7–8× per pipeline. This script
emits a single `.blast/steering/steering-digest.md` (~150–250 lines) that phases
can read FIRST, pulling the full file only when they need to drill down.

Deterministic, 0 tokens, no LLM. Extraction per source file:
  - every H2/H3 heading (the file's shape at a glance), and
  - VERBATIM copies of a curated set of high-signal sections (gotchas, incidents,
    invariants, AI guidance, canonical commands, component registry) — the stuff
    design/impl/validate actually need — with a pointer back to the full file.

Usage:
  blast-steering-digest.py            # regenerate the digest
  blast-steering-digest.py --check    # exit 1 if digest is stale vs sources (CI)

The digest is GENERATED — never hand-edit it; edit the source steering files and
re-run. `steering-agent` (Cartographer) regenerates it on sync.
"""

from __future__ import annotations

import sys
from pathlib import Path

STEERING = Path(".blast/steering")
DIGEST_NAME = "steering-digest.md"

# Source files in reading order. Missing files are skipped silently.
SOURCES = ["product.md", "tech.md", "structure.md", "INVENTORY.md",
           "RESEARCH.md", "lessons.md", "llm-routing.md", "cost-policy.md"]

# Section headings whose BODY is copied verbatim into the digest (case-insensitive
# substring match on the heading text). These are the high-signal, frequently-needed bits.
VERBATIM_SECTIONS = [
    "gotcha", "incident", "invariant", "ai guidance", "ai collaboration",
    "canonical command", "component registry", "cross-spec", "conventions",
    "stack", "constraints", "decisions",
]

MAX_VERBATIM_LINES = 40   # cap per copied section so one huge table can't bloat the digest


def project_root() -> Path:
    p = Path.cwd()
    if (p / ".blast").exists():
        return p
    return Path(__file__).resolve().parent.parent.parent


def split_sections(text: str):
    """Yield (level, heading, body_lines) for each ## / ### section."""
    lines = text.splitlines()
    cur_head = None
    cur_level = 0
    body: list[str] = []
    for ln in lines:
        s = ln.rstrip()
        if s.startswith("### "):
            if cur_head is not None:
                yield cur_level, cur_head, body
            cur_head, cur_level, body = s[4:].strip(), 3, []
        elif s.startswith("## "):
            if cur_head is not None:
                yield cur_level, cur_head, body
            cur_head, cur_level, body = s[3:].strip(), 2, []
        else:
            if cur_head is not None:
                body.append(ln)
    if cur_head is not None:
        yield cur_level, cur_head, body


def digest_for(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    out = [f"### {path.name}", ""]
    headings: list[str] = []
    verbatim: list[str] = []
    for level, head, body in split_sections(text):
        indent = "  " if level == 3 else ""
        headings.append(f"- {indent}{head}")
        low = head.lower()
        if any(key in low for key in VERBATIM_SECTIONS):
            trimmed = [b for b in body if b.strip()][:MAX_VERBATIM_LINES]
            if trimmed:
                verbatim.append(f"#### {head}  ·  ({path.name})")
                verbatim.extend(trimmed)
                if len([b for b in body if b.strip()]) > MAX_VERBATIM_LINES:
                    verbatim.append(f"> …(truncated — see `.blast/steering/{path.name}`)")
                verbatim.append("")
    if headings:
        out.append("**Sections:**")
        out.extend(headings)
        out.append("")
    out.extend(verbatim)
    out.append(f"→ full file: `.blast/steering/{path.name}`")
    out.append("")
    return out


def build(root: Path) -> str:
    steer = root / STEERING
    parts = [
        "# Steering Digest (GENERATED — do not edit)",
        "",
        "Condensed view of `.blast/steering/*.md`. Read THIS first; open the full file",
        "only to drill down. Regenerate with `python3 .claude/scripts/blast-steering-digest.py`",
        "(the steering-agent does this on sync). Source of truth is always the full files.",
        "",
        "---",
        "",
    ]
    found = 0
    for name in SOURCES:
        p = steer / name
        if p.exists():
            found += 1
            parts.extend(digest_for(p))
            parts.append("---")
            parts.append("")
    # any steering .md not in the canonical list (custom project files)
    if steer.exists():
        known = set(SOURCES) | {DIGEST_NAME}
        for p in sorted(steer.glob("*.md")):
            if p.name not in known and "security-report" not in p.name:
                found += 1
                parts.extend(digest_for(p))
                parts.append("---")
                parts.append("")
    if not found:
        parts.append("_(no steering files found — run `/blast:steering` first)_")
    return "\n".join(parts).rstrip() + "\n"


def source_mtime(root: Path) -> float:
    steer = root / STEERING
    m = 0.0
    for p in steer.glob("*.md") if steer.exists() else []:
        if p.name == DIGEST_NAME:
            continue
        try:
            m = max(m, p.stat().st_mtime)
        except OSError:
            pass
    return m


def main() -> int:
    root = project_root()
    digest_path = root / STEERING / DIGEST_NAME
    if "--check" in sys.argv:
        if not digest_path.exists():
            print("[steering-digest] STALE: digest missing", file=sys.stderr)
            return 1
        if digest_path.stat().st_mtime < source_mtime(root):
            print("[steering-digest] STALE: sources newer than digest — regenerate", file=sys.stderr)
            return 1
        print("[steering-digest] fresh")
        return 0
    content = build(root)
    try:
        digest_path.write_text(content, encoding="utf-8")
    except OSError as e:
        print(f"[steering-digest] ERROR: cannot write digest ({e})", file=sys.stderr)
        return 1
    lines = content.count("\n")
    print(f"[steering-digest] wrote {digest_path} ({lines} lines)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        print(f"[steering-digest] ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
