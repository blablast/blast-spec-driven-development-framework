#!/usr/bin/env python3
"""
blast-knowledge-index — hybrid (semantic + keyword) index over project knowledge.

Indexed sources:
  .blast/knowledge/**/*.md   (decisions, references, research, sota)
  .blast/steering/*.md       (INVENTORY, tech, product, structure — DRY queries)

Two retrieval modes, automatic:
  1. SEMANTIC — embeddings via local Ollama (BLAST_OLLAMA_UBUNTU, model
     BLAST_EMBED_MODEL, default nomic-embed-text). $0, private, on the 5090.
  2. KEYWORD — sqlite inverted index. Always built; the fallback when Ollama
     is unreachable or the embed model is missing.

Used by: spec-design-agent (Art. VII pre-design DRY check: "do we already have
this?"), spec-research-agent (read before WebSearch), /blast:learn.

NOTE: a 2026-05 global rename corrupted this script (SQL table named `.priv`),
which is why knowledge-index.sqlite sat empty — --build always crashed.

Usage:
  python .claude/scripts/blast-knowledge-index.py --build
  python .claude/scripts/blast-knowledge-index.py --search "http client retry"
  python .claude/scripts/blast-knowledge-index.py --stats
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sqlite3
import struct
import sys
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
KNOWLEDGE = ROOT / ".blast" / "knowledge"
STEERING = ROOT / ".blast" / "steering"
INDEX_DB = ROOT / ".blast" / ".session-state" / "knowledge-index.sqlite"

OLLAMA_URL = os.environ.get("BLAST_OLLAMA_UBUNTU", "http://192.168.5.60:11434")
EMBED_MODEL = os.environ.get("BLAST_EMBED_MODEL", "nomic-embed-text")

STOPWORDS = {"this", "that", "with", "from", "have", "were", "been", "they",
             "their", "them", "these", "than", "into", "when", "what", "which",
             "would", "should", "could", "while", "after", "before", "about",
             "where", "who", "whom", "until", "since"}


def tokenize(text: str) -> list[str]:
    return [w for w in re.findall(r"\b[a-z][a-z0-9_-]{2,}\b", text.lower())
            if w not in STOPWORDS]


def embed(text: str) -> list[float] | None:
    """Best-effort embedding via local Ollama. None on any failure (fallback to keyword)."""
    try:
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/embeddings",
            data=json.dumps({"model": EMBED_MODEL, "prompt": text[:8000]}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            vec = json.loads(resp.read()).get("embedding")
            return vec if isinstance(vec, list) and vec else None
    except Exception:
        return None


def _pack(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def _unpack(blob: bytes) -> list[float]:
    n = len(blob) // 4
    return list(struct.unpack(f"{n}f", blob))


def _cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


def iter_sources():
    if KNOWLEDGE.exists():
        for md in sorted(KNOWLEDGE.rglob("*.md")):
            if md.name != "README.md":
                yield md
    if STEERING.exists():
        for md in sorted(STEERING.glob("*.md")):
            yield md


def build_index() -> dict:
    INDEX_DB.parent.mkdir(parents=True, exist_ok=True)
    if INDEX_DB.exists():
        INDEX_DB.unlink()
    conn = sqlite3.connect(INDEX_DB)
    conn.execute("CREATE TABLE docs (id INTEGER PRIMARY KEY, path TEXT UNIQUE, title TEXT, content TEXT, embedding BLOB)")
    conn.execute("CREATE TABLE terms (term TEXT, doc_id INTEGER, count INT)")
    conn.execute("CREATE INDEX idx_terms_term ON terms(term)")
    n_docs = n_emb = 0
    for md in iter_sources():
        text = md.read_text(encoding="utf-8")
        title_m = re.match(r"^#\s+(.+)$", text, re.MULTILINE)
        title = title_m.group(1) if title_m else md.stem
        vec = embed(f"{title}\n\n{text}")
        cur = conn.execute(
            "INSERT INTO docs (path, title, content, embedding) VALUES (?, ?, ?, ?)",
            (str(md.relative_to(ROOT)), title, text, _pack(vec) if vec else None),
        )
        if vec:
            n_emb += 1
        doc_id = cur.lastrowid
        n_docs += 1
        for term, count in Counter(tokenize(text)).items():
            conn.execute("INSERT INTO terms (term, doc_id, count) VALUES (?, ?, ?)",
                         (term, doc_id, count))
    conn.commit()
    conn.close()
    return {"docs": n_docs, "embedded": n_emb}


def search(query: str, top_k: int = 10) -> list[dict]:
    if not INDEX_DB.exists():
        return []
    conn = sqlite3.connect(INDEX_DB)

    # Semantic first — only if the index has embeddings AND the query embeds
    has_emb = conn.execute("SELECT COUNT(*) FROM docs WHERE embedding IS NOT NULL").fetchone()[0]
    if has_emb:
        qvec = embed(query)
        if qvec:
            scored = []
            for path, title, blob in conn.execute(
                    "SELECT path, title, embedding FROM docs WHERE embedding IS NOT NULL"):
                scored.append({"path": path, "title": title,
                               "score": round(_cosine(qvec, _unpack(blob)), 4),
                               "mode": "semantic"})
            conn.close()
            return sorted(scored, key=lambda r: -r["score"])[:top_k]

    # Keyword fallback
    terms = tokenize(query)
    if not terms:
        conn.close()
        return []
    placeholders = ",".join("?" * len(terms))
    rows = conn.execute(
        f"""SELECT d.path, d.title, SUM(t.count) AS score
            FROM terms t JOIN docs d ON d.id = t.doc_id
            WHERE t.term IN ({placeholders})
            GROUP BY d.id ORDER BY score DESC LIMIT ?""",
        (*terms, top_k),
    ).fetchall()
    conn.close()
    return [{"path": r[0], "title": r[1], "score": r[2], "mode": "keyword"} for r in rows]


def stats() -> dict:
    if not INDEX_DB.exists():
        return {"_status": "no index built; run --build"}
    conn = sqlite3.connect(INDEX_DB)
    n_docs = conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
    n_emb = conn.execute("SELECT COUNT(*) FROM docs WHERE embedding IS NOT NULL").fetchone()[0]
    n_terms = conn.execute("SELECT COUNT(DISTINCT term) FROM terms").fetchone()[0]
    conn.close()
    return {"docs": n_docs, "embedded": n_emb, "unique_terms": n_terms,
            "embed_model": EMBED_MODEL, "ollama": OLLAMA_URL}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--build", action="store_true")
    p.add_argument("--search", metavar="QUERY")
    p.add_argument("--stats", action="store_true")
    p.add_argument("--top-k", type=int, default=10)
    args = p.parse_args()
    if args.build:
        r = build_index()
        mode = "semantic+keyword" if r["embedded"] else "keyword only (Ollama unreachable?)"
        print(f"Index built: {r['docs']} docs, {r['embedded']} embedded — {mode}")
    elif args.search:
        results = search(args.search, args.top_k)
        if not results:
            print("No matches.")
            return 0
        print(f"Top {len(results)} matches for '{args.search}' [{results[0]['mode']}]:\n")
        for r in results:
            print(f"  [{r['score']:>7}] {r['title']}")
            print(f"            {r['path']}")
    elif args.stats:
        print(json.dumps(stats(), indent=2))
    else:
        p.print_help()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
