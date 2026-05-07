#!/usr/bin/env python3
"""
blast-autotune — auto-tune agent prompts based on outcomes (SCAFFOLD).

Status: scaffold only. Full implementation = serious research project.

Approach (when implemented — high-level design):

1. Outcome tracking
   For each subagent invocation, record:
     - prompt version hash (which agent.md was active)
     - input characteristics (spec phase, complexity proxy, codebase size)
     - output verdict + downstream consequences (did user revert? next phase failed?)

2. Pattern detection
   Per (subagent, prompt_version):
     - Cluster failures by category (bad-EARS, missed-component, false-positive...)
     - Identify systematic bias (e.g. "Atlas always over-engineers when
       requirements has >5 ACs")

3. Prompt deltas (THE HARD PART)
   Generate prompt patches that target identified bias:
     - Insertion: "WEAKNESS YOU MUST WATCH FOR: when requirements >5 ACs..."
     - Constitutional refinement (manual review still needed)

4. Eval gate
   Use blast-eval.py to test patched prompt vs baseline. Promote only if
   stat-sig improvement.

5. Promotion
   Update `.claude/agents/blast/{agent}.md` frontmatter `version` field.
   Old version archived in `.blast/eval/variants/`.

Why scaffold only:
- Requires eval dataset (item 6 dependency)
- Step 3 = LLM-driven prompt generation, fragile, easy to over-fit
- Better wait until blast has 100+ shipped specs + 50+ caught regressions

Currently: stub. Re-evaluate after blast hits maturity threshold.

Usage (planned):
  python blast-autotune.py --analyze {agent}      # find bias patterns
  python blast-autotune.py --suggest {agent}      # propose prompt patches
  python blast-autotune.py --promote {agent} v2   # adopt patched version
"""
from __future__ import annotations
import sys


def main():
    print("blast-autotune: SCAFFOLD only.")
    print()
    print("Full implementation requires:")
    print("  1. Eval dataset (run blast-eval.py --scaffold first)")
    print("  2. 100+ shipped specs for pattern detection samples")
    print("  3. Manual review of suggested prompt patches before promote")
    print()
    print("Status: deferred until blast has eval infrastructure + maturity.")
    print("See .blast/eval/README.md for the path forward.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
