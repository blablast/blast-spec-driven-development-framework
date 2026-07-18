"""blast-lint-gate.py — fail-open by default (loudly), fail-closed in strict mode."""

import json

from conftest import run_hook

HOOK = "blast-lint-gate.py"


def gated_event(project, feature="feat", agent="spec-tasks-agent"):
    d = project / ".blast" / "specs" / feature
    d.mkdir(parents=True, exist_ok=True)
    (d / "spec.json").write_text(json.dumps({"tiny": False}), encoding="utf-8")
    return {"cwd": str(project), "tool_name": "Task",
            "tool_input": {"subagent_type": agent, "prompt": f"Feature: {feature}\n\nwork"}}


def test_missing_linter_allows_but_warns(tmp_path):
    r = run_hook(HOOK, gated_event(tmp_path))
    assert r.returncode == 0
    assert "LINT GATE INACTIVE" in r.stderr  # loud, not silent


def test_missing_linter_blocks_in_strict_mode(tmp_path):
    r = run_hook(HOOK, gated_event(tmp_path), env={"BLAST_LINT_STRICT": "1"})
    assert r.returncode == 2
    assert "HARD BLOCK" in r.stderr


def test_tiny_spec_exempt_even_in_strict(tmp_path):
    ev = gated_event(tmp_path)
    spec = tmp_path / ".blast" / "specs" / "feat" / "spec.json"
    spec.write_text(json.dumps({"tiny": True}), encoding="utf-8")
    r = run_hook(HOOK, ev, env={"BLAST_LINT_STRICT": "1"})
    assert r.returncode == 0


def test_ungated_agent_passes(tmp_path):
    r = run_hook(HOOK, gated_event(tmp_path, agent="general-purpose"),
                 env={"BLAST_LINT_STRICT": "1"})
    assert r.returncode == 0


def test_bypass_marker(tmp_path):
    ev = gated_event(tmp_path)
    ev["tool_input"]["prompt"] += "\nLint-bypass: true"
    r = run_hook(HOOK, ev, env={"BLAST_LINT_STRICT": "1"})
    assert r.returncode == 0
