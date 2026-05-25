# ADR: `/blast:simplify` jako standalone komenda, nie tryb `review`

**Date**: 2026-05-25
**Status**: Accepted
**Tags**: pipeline, simplify, review, kiss, karpathy

## Context

Po przeglądzie SOTA (GitHub Spec Kit, Amazon Kiro, maj 2026) potwierdzono lukę całej kategorii: SDD złożoność *relokuje*, nie usuwa — żaden lider nie ma kroku „odejmij złożoność". blast ma filozofię (Rule 2 Simplicity first, code-principles KISS/YAGNI) i infrę (Verification Strategy), żeby taki krok zrobić sensownie.

Pytanie projektowe: czy redukcyjny post-impl pass powinien być osobną komendą `/blast:simplify`, czy trybem istniejącego `/blast:review --simplify`? `review` (Compass) już pokrywa KISS/DRY/YAGNI/dead-code/overengineering z `--fix`, więc istniało realne ryzyko duplikatu.

## Decision

Standalone komenda `/blast:simplify` + agent `simplify-agent` (persona Occam), Sonnet, opcjonalna faza `impl → [validate-impl] → [simplify] → complete`.

## Rationale

Kontrakt simplify jest jakościowo inny od review:
- **review** = szeroki audyt jakości (SOLID, docstringi, nazewnictwo, lint, scorecard) — *znajdź i zaraportuj*, `--fix` naprawia rzeczy lint/docs (additive/neutral).
- **simplify** = wąski, biased-to-subtract, **behavior-preserving** — *usuń + udowodnij* (re-run Verification Strategy, revert na czerwonych), metryka `LOC_DELTA`.

Bramka apply (baseline zielony → cięcie → re-verify → revert/keep) to transformacja, nie tryb przeglądu — mieszanie z review zaciemniłoby oba. Oś natywna #1 (spec-traceability/drift) korzysta z linkacji spec↔kod, której review nie eksploatuje. Agent jest cienki — importuje tylko 6 osi redukcyjnych, nie kopiuje scorecardu review.

Karpathy alignment: simplify = ramię egzekucyjne Rule 2 (pitfall „1000 lines when 100 would do"); Rule 3 (ochrona komentarzy + orphans-only) = jego hamulec bezpieczeństwa.

## Consequences

- +1 komenda, +1 agent (koszt utrzymania). Akceptowalny, bo agent cienki.
- **Kill-switch**: jeśli po 5 realnych użyciach pokrycie findingów z `review` przekroczy 70%, scalić simplify do flagi `review --simplify` i wycofać standalone. Mierzyć przez `/blast:learn --lessons`.
- Ryzyko że framework łamie własne Rule 2 dodając komendę — mitygowane opcjonalnością kroku (nigdy nie blokuje, `BLOCKING: false`) i zerowymi zmianami w istniejących fazach.
- Granica Rule 3: simplify jest jawnym „asked" do usuwania zastanego dead-code, ale tylko gdy (a) brak odniesienia do wymagania/taska, (b) Verification Strategy zielona po cięciu, (c) brak niezrozumianego komentarza.
