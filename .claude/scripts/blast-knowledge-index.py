#!/usr/bin/env python3
"""
blast-knowledge-index — simple keyword-frequency index over .blast/knowledge/.

MVP: builds a sqlite-backed inverted index (no embeddings — pragmatic).
Research agent can query for "find docs mentioning X, Y, Z" in O(log n) time.

Future: swap for FAISS + sentence-transformers for semantic search when
knowledge base grows beyond 100 entries.

Usage:
  python .claude/scripts/blast-knowledge-index.py --build
  python .claude/scripts/blast-knowledge-index.py --search "qwen vs claude"
  python .claude/scripts/blast-knowledge-index.py --stats
"""
from __future__ import annotations
import argparse
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
KNOWLEDGE = ROOT / ".blast" / "knowledge"
INDEX_DB = ROOT / ".blast" / ".session-state" / "knowledge-index.sqlite"

STOPWORDS = {"this", "that", "with", "from", "have", "were", "been", "they",
             "their", "them", "these", "than", "into", "when", "what", "which",
             "would", "should", "could", "while", "after", "before", "about",
             "where", "which", "who", "whom", "while", "until", "since"}


def tokenize(text: str) -> list[str]:
    return [w for w in re.findall(r"\b[a-z][a-z0-9_-]{2,}\b", text.lower())
            if w not in STOPWORDS]


def build_index() -> dict:
    INDEX_DB.parent.mkdir(parents=True, exist_ok=True)
    if INDEX_DB.exists():
        INDEX_DB.unlink()
    conn = sqlite3.connect(INDEX_DB)
    conn.execute("CREATE TABLE docs (id INTEGER PRIMARY KEY, path TEXT UNIQUE, title TEXT, content TEXT)")
    conn.execute("CREATE TABLE terms (term TEXT, doc_id INTEGER, count INT)")
    conn.execute("CREATE INDEX idx_terms_term ON terms(term)")
    if not KNOWLEDGE.exists():
        conn.commit()
        conn.close()
        return {"docs": 0, "terms": 0}
    n_docs = 0
    n_terms = 0
    for md in KNOWLEDGE.rglob("*.md"):
        if md.name == "README.md":
            continue
        text = md.read_text(encoding="utf-8")
        title_m = re.match(r"^#\s+(.+)$", text, re.MULTILINE)
        title = title_m.group(1) if title_m else md.stem
        cur = conn.execute("INSERT INTO docs (path, title, content) VALUES (?, ?, ?)",
                           (str(md.relative_to(ROOT)), title, text))
        doc_id = cur.lastrowid
        n_docs += 1
        counts = Counter(tokenize(text))
        for term, count in counts.items():
            conn.execute("INSERT INTO terms (term, doc_id, count) VALUES (?, ?, ?)",
                         (term, doc_id, count))
            n_terms += 1
    conn.commit()
    conn.close()
    return {"docs": n_docs, "terms": n_terms}


def search(query: str, top_k: int = 10) -> list[dict]:
    if not INDEX_DB.exists():
        return []
    terms = tokenize(query)
    if not terms:
        return []
    conn = sqlite3.connect(INDEX_DB)
    placeholders = ",".join("?" * len(terms))
    rows = conn.execute(
        f"""SELECT d.path, d.title, SUM(t.count) AS score
            FROM terms t JOIN docs d ON d.id = t.doc_id
            WHERE t.term IN ({placeholders})
            GROUP BY d.id ORDER BY score DESC LIMIT ?""",
        (*terms, top_k),
    ).fetchall()
    conn.close()
    return [{"path": r[0], "title": r[1], "score": r[2]} for r in rows]


def stats() -> dict:
    if not INDEX_DB.exists():
        return {"_status": "no index built; run --build"}
    conn = sqlite3.connect(INDEX_DB)
    n_docs = conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
    n_terms = conn.execute("SELECT COUNT(DISTINCT term) FROM terms").fetchone()[0]
    n_postings = conn.execute("SELECT COUNT(*) FROM terms").fetchone()[0]
    conn.close()
    return {"docs": n_docs, "unique_terms": n_terms, "total_postings": n_postings}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--build", action="store_true")
    p.add_argument("--search", metavar="QUERY")
    p.add_argument("--stats", action="store_true")
    p.add_argument("--top-k", type=int, default=10)
    args = p.parse_args()
    if args.build:
        result = build_index()
        print(f"✓ Index built: {result['docs']} docs, {result['terms']} term postings")
    elif args.search:
        results = search(args.search, args.top_k)
        if not results:
            print("No matches.")
            return 0
        print(f"Top {len(results)} matches for '{args.search}':\n")
        for r in results:
            print(f"  [{r['score']:>4}] {r['title']}")
            print(f"         {r['path']}")
    elif args.stats:
        import json
        print(json.dumps(stats(), indent=2))
    else:
        p.print_help()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
