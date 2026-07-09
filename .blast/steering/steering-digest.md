# Steering Digest (GENERATED — do not edit)

Condensed view of `.blast/steering/*.md`. Read THIS first; open the full file
only to drill down. Regenerate with `python3 .claude/scripts/blast-steering-digest.py`
(the steering-agent does this on sync). Source of truth is always the full files.

---

### llm-routing.md

**Sections:**
- Default routing per agent
- Effort policy (budżet rozumowania per tier)
- Steering digest (§5 — czytaj skrót, nie cały katalog)
- Tiered impl routing (local-first)
-   lfm2.5 — mechanical lane (580 tok/s)
- Privacy patterns
- debate_config — declarative composition for `/blast:debate`
-   Trigger semantics
-   Compositions

→ full file: `.blast/steering/llm-routing.md`

---

### cost-policy.md

**Sections:**
- Soft warnings (active from day 1)
- Local LLM
- Manual override
- Hard limits — per-phase ceilings (warning_at / block_at)
-   Soft warnings (still active)
-   Free local-only mode (`spec.json.privacy: local-only`)

→ full file: `.blast/steering/cost-policy.md`

---
