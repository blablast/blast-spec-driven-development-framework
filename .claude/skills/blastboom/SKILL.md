---
name: blastboom
description: Compress Markdown documents for LLM consumption. Reduce tokens ~60-75% while preserving all technical meaning. Triggers: "compress this doc", "blastboom this file", "/blastboom <file>", invocation from blast agents for external content ingestion.
---

Transform .md input into token-dense .md output. Target: another LLM reads compressed version, extracts identical facts/requirements/instructions as from original.

## Preserve verbatim

- Code blocks (```...```)
- Inline code (`...`)
- File paths, URLs, identifiers, version numbers
- Quoted error messages
- Numeric values, dates, limits
- Normative keywords: MUST, SHOULD, MAY, MUST NOT (RFC 2119)
- Frontmatter (YAML between ---)

## Compress aggressively

- Articles (a/an/the)
- Filler (just/really/basically/actually/simply/essentially)
- Pleasantries and meta-commentary ("as we discussed", "it's worth noting")
- Transitional phrases ("furthermore", "in addition", "that being said")
- Redundant restatement (if X said in heading, don't repeat in first paragraph)
- Passive → active ("the file is created by" → "creates")
- Multi-word phrases → single word where unambiguous

## Preserve structure

- Heading hierarchy (# ## ###) — LLMs use for chunking
- List vs prose distinction — don't flatten lists to prose
- Tables — keep as tables
- Order of information

## Preserve semantics

- Causal relations: keep "because" / "due to" as arrows → only when cause→effect is obvious
- Conditionals: "if X then Y" stays explicit, do not compress to "X → Y"
- Contrast: "but" / "however" / "unlike" must survive — losing them inverts meaning
- Enumeration vs sequence: numbered list = order matters, bullets = doesn't

## Output contract

- Same filename semantics, `.md` output
- Heading IDs stable (for cross-references)
- No new information added
- No rewording that shifts meaning, even if shorter
- If ambiguous whether to cut, keep it

## Example

Input:
> ## Authentication
> The authentication middleware is responsible for checking that the JWT token sent by the client in the Authorization header has not expired. If the token is expired, the middleware should return a 401 Unauthorized response. It's worth noting that the current implementation uses `<` instead of `<=` for the expiry comparison, which means tokens are considered valid for one second past their actual expiry time.

Output:
> ## Authentication
> Middleware checks JWT expiry from Authorization header. Expired → return 401. Current impl uses `<` not `<=` for expiry check — tokens valid 1s past expiry.

Reduction: ~65%. Preserved: all facts, code operators, status code, header name, bug description.

## Refuse to compress

- Legal text, licenses, contracts
- Quoted external content (attribution requires verbatim)
- Examples where verbosity is the point (teaching material showing a bad pattern)
- Files under 500 tokens (overhead not worth it — compression-call itself costs ~200 tokens)
- blast framework files: `.blast/steering/*`, `.blast/specs/*/spec.json`, `.blast/specs/*/{requirements,design,tasks}.md`, `.claude/agents/**`, `.claude/commands/**`, `.blast/settings/rules/*`, `.blast/settings/templates/*` — these need determinism and human review, not compression

## Safe-use targets in blast

blast agents MAY invoke blastboom before writing to these paths:

- `.blast/specs/{feature}/requirements.md` — only the `## Source Material` block (imported from `--source` flag), not the generated requirements themselves
- `.blast/knowledge/research/{feature}.md` — research summaries from external sources
- `.blast/knowledge/references/{technology}.md` — saved docs, API specs, articles
- Pre-read pass on `--source` file before embedding into requirements.md

Trigger condition: content ≥500 tokens AND origin is external (web, PDF, user-provided brief). Never compress content authored by blast agents themselves.
