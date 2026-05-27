# Knowledge Base

Lokalna baza wiedzy projektu. Przeszukiwana PRZED internetem podczas `/blast:research`.

## Jak to działa

1. **Research agent czyta** — przed WebSearch sprawdza co już wiemy
2. **Research agent pisze** — po zakończeniu badań dorzuca wnioski jako nowy plik
3. **Ty piszesz** — wrzucaj tu artykuły, notatki, porównania, decyzje

## Struktura

```
knowledge/
├── README.md              ← ten plik
├── decisions/             ← decyzje architektoniczne (ADR)
├── references/            ← dokumentacja API, snippety, linki
├── research/              ← wyniki researchów (auto-generowane)
└── sota/                  ← curated SOTA recommendations per tech area (read by Pragmatist)
```

## Konwencje nazewnictwa

- `decisions/YYYY-MM-DD-{topic}.md` — np. `2026-03-04-auth-strategy.md`
- `references/{technology}.md` — np. `fastapi.md`, `react-query.md`
- `research/{feature-name}.md` — auto-generowane z `/blast:research`

## Format pliku

Każdy plik powinien mieć nagłówek:

```markdown
# {Tytuł}

**Źródło**: {URL lub "własne notatki"}
**Data**: {YYYY-MM-DD}
**Tagi**: {technologia, wzorzec, biblioteka...}

{treść}
```

Tagi pomagają agentowi w wyszukiwaniu relevantnych plików.


## Note about R&D content

Pliki **research/, decisions/** w tym katalogu są tworzone **per project**:
- `decisions/{date}-{topic}.md` — Twoje architektoniczne decyzje
- `research/{feature}.md` — output `/blast:research`
- `references/{tech}.md` — Twoje notatki / docs

Mój personal R&D (Twojego klona/template'a NIE dotyczy) leży w `.priv/` na repo root — strategic roadmap, spike validations, INVENTORY snapshot. Patrz `MANIFEST.md` dla pełnej klasyfikacji.
