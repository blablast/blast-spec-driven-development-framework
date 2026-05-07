#!/usr/bin/env python3
"""Track shipped specs counter for periodic auto-learn trigger.

Maintained at .blast/.session-state/learn-counter.json:
{
  "shipped_count": 12,
  "last_learn_run": "2026-05-07T12:34:56Z",
  "next_learn_at": 15  # shipped_count milestone for next auto-learn
}

Usage:
  python .claude/scripts/blast-shipped-counter.py increment
  python .claude/scripts/blast-shipped-counter.py should-run
  python .claude/scripts/blast-shipped-counter.py reset
"""
from __future__ import annotations
import json
import sys
import datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
STATE = ROOT / ".blast" / ".session-state" / "learn-counter.json"
CADENCE = 5  # auto-learn every N shipped specs


def load() -> dict:
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"shipped_count": 0, "last_learn_run": None, "next_learn_at": CADENCE}


def save(data: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def main():
    if len(sys.argv) < 2:
        print(json.dumps(load(), indent=2))
        return 0
    cmd = sys.argv[1]
    data = load()
    if cmd == "increment":
        data["shipped_count"] += 1
        save(data)
        print(json.dumps(data, indent=2))
    elif cmd == "should-run":
        # Returns 0 (yes) if shipped_count >= next_learn_at, 1 otherwise
        return 0 if data["shipped_count"] >= data["next_learn_at"] else 1
    elif cmd == "reset":
        # Mark learn run completed, set next milestone
        data["last_learn_run"] = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
        data["next_learn_at"] = data["shipped_count"] + CADENCE
        save(data)
        print(json.dumps(data, indent=2))
    elif cmd == "status":
        print(json.dumps(data, indent=2))
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
