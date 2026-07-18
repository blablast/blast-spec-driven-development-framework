"""blast-telemetry.py — §3 cost accounting: tiers, bridge scraping, record shape."""

import importlib.util
import json
import sys

from conftest import HOOKS, run_hook


def load_module():
    spec = importlib.util.spec_from_file_location("blast_telemetry", HOOKS / "blast-telemetry.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["blast_telemetry"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_sonnet_cost_estimate():
    t = load_module()
    c = t.estimate_cost("validate-impl-agent", 40000, 8000, "")
    assert c["model_tier"] == "sonnet"
    # 10k in * $2/M + 2k out * $10/M = 0.02 + 0.02
    assert abs(c["cost_usd"] - 0.04) < 1e-6
    assert c["cost_estimated"] is True


def test_opus_flagged_expensive():
    t = load_module()
    c = t.estimate_cost("spec-design-agent", 60000, 20000, "")
    assert c["model_tier"] == "opus" and c["expensive"] is True


def test_local_bridge_tokens_scraped_at_zero_dollars():
    t = load_module()
    rt = ("[qwen3-coder @ ubuntu | 512 tokens | 3.2s | 160.0 tok/s]\ncode\n"
          "[lfm2.5 @ ubuntu | 88 tokens | 0.2s | 440.0 tok/s]")
    c = t.estimate_cost("spec-tdd-impl-agent", 12000, 4000, rt)
    assert c["local_tokens"] == 600


def test_gemini_usage_adds_real_cost():
    t = load_module()
    rt = "[gemini-3-flash-preview @ gemini-api | in=2000 out=500]\nverdict"
    c = t.estimate_cost("security-audit-agent", 30000, 6000, rt)
    # sonnet est 0.03 + gemini real 0.00185
    assert abs(c["cost_usd"] - 0.03185) < 1e-5


def test_hook_writes_record_with_cost_fields(tmp_path):
    (tmp_path / ".blast").mkdir()
    ev = {"tool_name": "Task", "cwd": str(tmp_path),
          "tool_input": {"subagent_type": "validate-impl-agent",
                         "prompt": "Feature: demo\n" * 50, "description": "validate"},
          "tool_response": {"result": "ok\n---VERDICT---\nVERDICT: PASS\nBLOCKING: false\nFINDINGS: 0\n---END---"}}
    r = run_hook("blast-telemetry.py", ev)
    assert r.returncode == 0
    line = (tmp_path / ".blast" / "logs" / "agent-runs.jsonl").read_text().strip()
    rec = json.loads(line)
    assert rec["verdict"] == "PASS" and rec["model_tier"] == "sonnet"
    assert "cost_usd" in rec and rec["cost_estimated"] is True and "pricing_asof" in rec
