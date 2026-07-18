"""Shared fixtures for blast framework tests.

These tests exercise the framework's OWN hooks and scripts (not a user project).
They live under .claude/tests/ so `blast init` does not wipe them (its WIPE_PATHS
removes only the project-level `tests/` dir).

Run from repo root:  pytest .claude/tests -q
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

# .claude/tests/framework/conftest.py → repo root is 3 parents up
REPO_ROOT = Path(__file__).resolve().parents[3]
HOOKS = REPO_ROOT / ".claude" / "hooks"
SCRIPTS = REPO_ROOT / ".claude" / "scripts"


def run_hook(hook: str, event: dict, env: dict | None = None) -> subprocess.CompletedProcess:
    """Feed a Claude Code hook event (JSON on stdin) to a hook script."""
    import os
    full_env = {**os.environ, **(env or {})}
    return subprocess.run(
        [sys.executable, str(HOOKS / hook)],
        input=json.dumps(event), capture_output=True, text=True, timeout=30, env=full_env,
    )


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """Minimal blast project: routing with privacy patterns + two specs."""
    steering = tmp_path / ".blast" / "steering"
    steering.mkdir(parents=True)
    (steering / "llm-routing.md").write_text(
        "# routing\n\n.env* llm=local-only\nsecrets/** llm=local-only\n",
        encoding="utf-8",
    )
    for feat, extra in [("secret-feat", {"privacy": "local-only"}), ("open-feat", {})]:
        d = tmp_path / ".blast" / "specs" / feat
        d.mkdir(parents=True)
        (d / "spec.json").write_text(
            json.dumps({"feature_name": feat, **extra}), encoding="utf-8"
        )
    return tmp_path
