"""blast-steering-digest.py — generated digest + staleness check."""

import subprocess
import sys
import time

from conftest import SCRIPTS

GEN = SCRIPTS / "blast-steering-digest.py"


def run(cwd, *args):
    return subprocess.run([sys.executable, str(GEN), *args],
                          capture_output=True, text=True, timeout=30, cwd=str(cwd))


def make_project(tmp_path):
    steering = tmp_path / ".blast" / "steering"
    steering.mkdir(parents=True)
    (steering / "tech.md").write_text(
        "# Tech\n## Stack\n- Python 3.11\n## Gotchas\n- reuse httpx clients\n",
        encoding="utf-8")
    (steering / "product.md").write_text(
        "# Product\n## Invariants\n- totals must balance\n", encoding="utf-8")
    return steering


def test_generates_digest_with_verbatim_sections(tmp_path):
    steering = make_project(tmp_path)
    assert run(tmp_path).returncode == 0
    digest = (steering / "steering-digest.md").read_text(encoding="utf-8")
    assert "GENERATED" in digest
    assert "reuse httpx clients" in digest          # gotcha copied verbatim
    assert "totals must balance" in digest           # invariant copied verbatim
    assert "full file: `.blast/steering/tech.md`" in digest


def test_check_fresh_then_stale(tmp_path):
    steering = make_project(tmp_path)
    run(tmp_path)
    assert run(tmp_path, "--check").returncode == 0   # fresh
    time.sleep(1.1)
    (steering / "tech.md").touch()
    assert run(tmp_path, "--check").returncode == 1   # stale after source change
