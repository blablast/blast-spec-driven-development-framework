"""blast-privacy-gate.py — the Constitution's privacy guarantees, tested.

Covers BOTH mechanisms:
  1. spec.json.privacy: local-only  → cloud blocked regardless of touched paths (P0 fix)
  2. touched privacy-flagged path   → later cloud reference blocked (original semantics)
"""

from conftest import run_hook

HOOK = "blast-privacy-gate.py"


def ev(project, tool_name, tool_input):
    return {"cwd": str(project), "tool_name": tool_name, "tool_input": tool_input}


# ── spec.json.privacy enforcement (P0) ────────────────────────────────────────

def test_local_only_spec_blocks_cloud_tool_in_prompt(project):
    """local-only spec + cloud tool referenced in prompt → block, NO touched paths needed."""
    r = run_hook(HOOK, ev(project, "Task",
        {"prompt": "Feature: secret-feat\n\nUse ask_gemini_3_flash_preview as juror"}))
    assert r.returncode == 2
    assert "local-only" in r.stderr


def test_local_only_spec_allows_local_tools(project):
    r = run_hook(HOOK, ev(project, "Task",
        {"prompt": "Feature: secret-feat\n\nUse ask_ubuntu_qwen36 and ask_win11_qwen3_coder"}))
    assert r.returncode == 0


def test_local_only_spec_blocks_later_direct_mcp_cloud_call(project):
    # activate the local-only spec…
    run_hook(HOOK, ev(project, "Task", {"prompt": "Feature: secret-feat\n\nimplement"}))
    # …then a direct MCP cloud call must be blocked
    r = run_hook(HOOK, ev(project, "mcp__blast-llm-bridge__ask_gemini_3_flash_preview",
                          {"prompt": "judge this"}))
    assert r.returncode == 2


def test_local_only_spec_allows_direct_mcp_local_call(project):
    run_hook(HOOK, ev(project, "Task", {"prompt": "Feature: secret-feat\n\nimplement"}))
    r = run_hook(HOOK, ev(project, "mcp__blast-llm-bridge__ask_ubuntu_qwen36", {"prompt": "x"}))
    assert r.returncode == 0


def test_open_spec_cloud_reference_allowed_when_nothing_touched(project):
    r = run_hook(HOOK, ev(project, "Task",
        {"prompt": "Feature: open-feat\n\nUse ask_gemini_3_flash_preview"}))
    assert r.returncode == 0


# ── original touched-path semantics still intact ─────────────────────────────

def test_touched_flagged_path_blocks_cloud_reference(project):
    r1 = run_hook(HOOK, ev(project, "Read", {"file_path": str(project / ".env")}))
    assert r1.returncode == 0  # the read itself is allowed, only remembered
    r2 = run_hook(HOOK, ev(project, "Task",
        {"prompt": "Feature: open-feat\n\nask_gemini_3_flash_preview"}))
    assert r2.returncode == 2


def test_gemini_pattern_is_external(project):
    """Regression: ask_gemini_* must match EXTERNAL patterns (was a bypass hole)."""
    run_hook(HOOK, ev(project, "Read", {"file_path": str(project / ".env")}))
    r = run_hook(HOOK, ev(project, "mcp__blast-llm-bridge__ask_gemini_3_flash_preview",
                          {"prompt": "x"}))
    assert r.returncode == 2


def test_no_patterns_no_privacy_spec_allows_everything(tmp_path):
    (tmp_path / ".blast" / "steering").mkdir(parents=True)
    (tmp_path / ".blast" / "steering" / "llm-routing.md").write_text("# empty\n")
    r = run_hook(HOOK, {"cwd": str(tmp_path), "tool_name": "Task",
                        "tool_input": {"prompt": "Feature: x\n\nask_gemini_3_flash_preview"}})
    assert r.returncode == 0
