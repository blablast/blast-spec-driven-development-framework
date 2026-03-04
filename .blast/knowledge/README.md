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
└── research/              ← wyniki researchów (auto-generowane)
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
