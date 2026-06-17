# Semble — code search dla blasta (setup)

[Semble](https://github.com/MinishLab/semble) to lokalna wyszukiwarka kodu dla agentów: zwraca trafne fragmenty kodu zużywając **~98% mniej tokenów niż grep+read**, działa w całości na CPU, bez API keys / GPU / usług zewnętrznych (MIT). blast używa jej do lokalizacji i eksploracji kodu w agentach (research, design, impl, review, security, validate-impl).

## Instalacja

Wymaga [`uv`](https://docs.astral.sh/uv/getting-started/installation/).

### MCP (zalecane — agenci blasta wołają `mcp__semble__*`)

```bash
claude mcp add semble -s user -- uvx --from "semble[mcp]" semble
# albo project-scope: merge wpisu `semble` z .blast/.mcp.json.snippet do root .mcp.json
```

Zrestartuj Claude Code (MCP czytane przy starcie). Toole: `search`, `find_related`.
Indeksowanie dokumentów/configów: dopisz `--content all` (lub `docs`/`config`) na końcu komendy serwera.

### CLI / Bash (fallback + indeksowanie)

```bash
uv tool install semble        # albo: pip install semble
semble index -o .blast/.session-state/semble-index
semble search "opis lub symbol" . --index .blast/.session-state/semble-index
semble find-related src/auth.py 42 .
```

`--content code|docs|config|all`. Ścieżka domyślnie `.`; akceptuje też URL gita.

## Jak blast tego używa

- Agenci mają nadane `mcp__semble__search` / `mcp__semble__find_related` we frontmatter `tools:` (analogicznie do `mcp__blast-llm-bridge__*`).
- Reguła: **semble** do wyszukiwania semantycznego / po symbolu; **grep** do wyczerpujących, dosłownych dopasowań.
- Indeks (tryb CLI) żyje w `.blast/.session-state/semble-index` (gitignored). Reindeksuj po większych zmianach kodu.
- Startup-check (`.claude/scripts/blast-mcp-check.py`, hook `SessionStart`) wykrywa brak Semble i wypisuje komendy instalacji.

## Privacy / koszt

100% lokalnie na CPU, zero wywołań zewnętrznych → przechodzi `blast-privacy-gate.py`, działa w privacy mode (`spec.json.privacy: local-only`). Koszt $0.

## Szybka weryfikacja

```bash
semble search "approval gate" .
```

Powinno wskazać `.claude/hooks/blast-approval-gate.py`.

Źródła: <https://github.com/MinishLab/semble> · <https://minish.ai/packages/semble/introduction/>
