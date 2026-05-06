---
description: "Cross-spec dependency graph + status dashboard — wszystkie specy w jednym widoku"
allowed-tools: Read, Glob, Bash
argument-hint: [feature-name]  (no arg = all specs; with arg = focused on that feature + neighbors)
---

# blast:graph — Status klastra specy

Pokazuje ASCII graph + tabelę wszystkich specy w `.blast/specs/`. Bez wywoływania subagenta — czysta analiza JSON. Szybkie (<1s).

## Parse Arguments

Parse `$ARGUMENTS`:
- Empty → mode = `all` (pokaż wszystkie specy)
- Single token (kebab-case) → mode = `focused`, target = ten feature + jego dependencies + dependents

## Execution

Use Bash tool to run inline Python:

```bash
python3 - <<'PYEOF'
import json
import sys
from pathlib import Path

specs_dir = Path(".blast/specs")
if not specs_dir.exists():
    print("⚠ No .blast/specs/ directory yet. Run /blast:init first.")
    sys.exit(0)

# Discover all spec.json files (top-level + evolutions)
specs = {}
evolutions_by_parent = {}

for spec_json in specs_dir.glob("*/spec.json"):
    feature_dir = spec_json.parent
    feature = feature_dir.name
    try:
        data = json.loads(spec_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"⚠ {feature}: spec.json malformed ({e})")
        continue
    specs[feature] = data

    # Discover evolutions
    evos_dir = feature_dir / "evolutions"
    if evos_dir.exists():
        evolutions_by_parent[feature] = []
        for evo_dir in sorted(evos_dir.iterdir()):
            if evo_dir.is_dir():
                evo_spec = evo_dir / "spec.json"
                if evo_spec.exists():
                    try:
                        evo_data = json.loads(evo_spec.read_text(encoding="utf-8"))
                        evolutions_by_parent[feature].append({
                            "dir": evo_dir.name,
                            "data": evo_data,
                        })
                    except json.JSONDecodeError:
                        pass

if not specs:
    print("ℹ No specs found in .blast/specs/. Use /blast:init to create one.")
    sys.exit(0)

# === Mode handling ===
mode = "all"
target = None
# (Slash command will pass argument string; here we assume Bash got it via env or inline)
# In practice slash command should set TARGET env var if argument provided.
import os
target_env = os.environ.get("BLAST_GRAPH_TARGET", "").strip()
if target_env:
    mode = "focused"
    target = target_env

# === Filter specs if focused ===
if mode == "focused" and target:
    if target not in specs:
        print(f"⚠ Feature '{target}' not found in .blast/specs/. Available:")
        for s in sorted(specs.keys()):
            print(f"  - {s}")
        sys.exit(1)
    
    # Find dependencies + dependents of target
    target_data = specs[target]
    target_deps = set(target_data.get("dependencies", []))
    target_provides = set(target_data.get("provides", []))
    
    related = {target}
    for fname, data in specs.items():
        if fname == target:
            continue
        # Is fname a dependency of target?
        if any(p in target_deps for p in data.get("provides", [])):
            related.add(fname)
        # Is fname a dependent on target?
        if any(p in target_provides for p in data.get("dependencies", [])):
            related.add(fname)
    
    specs = {k: v for k, v in specs.items() if k in related}

# === Status table ===
print("=" * 90)
title = f"blast specs status" + (f" (focused on '{target}' + neighbors)" if mode == "focused" else " (all)")
print(title)
print("=" * 90)
print()

# Collect rows
rows = []
for fname, data in sorted(specs.items()):
    phase = data.get("phase", "?")
    status = data.get("status", "?")
    provides = data.get("provides", []) or []
    deps = data.get("dependencies", []) or []
    
    # Approval state
    approvals = data.get("approvals", {})
    if "evolution" in approvals:
        # Evolution spec
        appr = "evo:" + ("✓" if approvals["evolution"].get("approved") else "✗")
    else:
        # Standard spec
        r = "✓" if approvals.get("requirements", {}).get("approved") else "✗"
        d = "✓" if approvals.get("design", {}).get("approved") else "✗"
        t = "✓" if approvals.get("tasks", {}).get("approved") else "✗"
        appr = f"r{r} d{d} t{t}"
    
    is_tiny = data.get("tiny") is True
    is_evo = data.get("parent_feature") is not None
    
    tags = []
    if is_tiny: tags.append("tiny")
    if is_evo: tags.append(f"evo→{data.get('parent_feature')}")
    
    rows.append({
        "name": fname,
        "phase": phase,
        "status": status,
        "approvals": appr,
        "provides": ", ".join(provides[:3]) + ("..." if len(provides) > 3 else ""),
        "deps": ", ".join(deps[:3]) + ("..." if len(deps) > 3 else ""),
        "tags": " ".join(tags),
    })

# Print table
col_widths = {
    "name": max(20, max((len(r["name"]) for r in rows), default=4)),
    "phase": max(20, max((len(r["phase"]) for r in rows), default=5)),
    "status": max(11, max((len(r["status"]) for r in rows), default=6)),
    "approvals": 12,
    "provides": 24,
    "deps": 24,
    "tags": 16,
}

def line(items, widths):
    return " | ".join(s.ljust(widths[k]) for k, s in items)

header = [("name", "Feature"), ("phase", "Phase"), ("status", "Status"), ("approvals", "Approvals"), ("provides", "Provides"), ("deps", "Deps"), ("tags", "Tags")]
print(line(header, col_widths))
print("-" * (sum(col_widths.values()) + 3 * len(col_widths)))
for r in rows:
    print(line([(k, r[k]) for k, _ in header], col_widths))

# === Evolutions section ===
if any(evolutions_by_parent.get(f) for f in specs):
    print()
    print("Evolutions:")
    print("-" * 90)
    for parent, evos in evolutions_by_parent.items():
        if parent not in specs or not evos:
            continue
        for evo in evos:
            d = evo["data"]
            ed = evo["dir"]
            phase = d.get("phase", "?")
            etype = d.get("evolution_type", "?")
            merged = d.get("merged_into_parent_at")
            merged_marker = "✓ merged" if merged else "○ active"
            print(f"  {parent}/evolutions/{ed}  | phase={phase}  type={etype}  {merged_marker}")

# === Dependency graph (ASCII) ===
print()
print("Dependency graph:")
print("-" * 90)

# Build edges: each spec depends on others' provides
all_provides = {}
for fname, data in specs.items():
    for p in (data.get("provides") or []):
        all_provides[p] = fname

# For each spec, draw arrows from deps
edges = []  # (from_feature, to_feature, via_provided_item)
for fname, data in specs.items():
    for dep in (data.get("dependencies") or []):
        from_feature = all_provides.get(dep)
        if from_feature and from_feature != fname:
            edges.append((from_feature, fname, dep))

if not edges:
    print("  (no inter-spec dependencies declared)")
else:
    print()
    # Group by source
    by_source = {}
    for src, dst, via in edges:
        by_source.setdefault(src, []).append((dst, via))
    for src in sorted(by_source.keys()):
        print(f"  {src}")
        for dst, via in sorted(by_source[src]):
            print(f"    └─ provides → {via} → {dst}")

# === Summary footer ===
print()
print("=" * 90)
total = len(specs)
shipped = sum(1 for r in rows if r["status"] == "shipped")
active = sum(1 for r in rows if r["status"] == "active")
planning = sum(1 for r in rows if r["status"] == "planning")
deprecated = sum(1 for r in rows if r["status"] == "deprecated")
evo_count = sum(len(e) for e in evolutions_by_parent.values())
print(f"Total: {total} specs | shipped: {shipped} | active: {active} | planning: {planning} | deprecated: {deprecated} | evolutions: {evo_count}")
print()
print("Hint: focused view → /blast:graph <feature-name>")
PYEOF
```

## Safety & Fallback

- **Brak `.blast/specs/`**: graceful "no specs yet" message
- **Malformed spec.json**: skip + warn that one (don't crash whole report)
- **Empty argument**: show all
- **Invalid argument**: list available + exit
