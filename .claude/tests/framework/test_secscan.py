"""blast-secscan.py — deterministic Phase-1 security scanner."""

import json
import subprocess
import sys

from conftest import SCRIPTS

SCAN = SCRIPTS / "blast-secscan.py"


def scan(*args, cwd=None):
    return subprocess.run([sys.executable, str(SCAN), *args, "--json"],
                          capture_output=True, text=True, timeout=60, cwd=cwd)


def write(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_hardcoded_secret_is_critical_exit2(tmp_path):
    f = tmp_path / "app.py"
    write(f, 'API_KEY = "sk-live-abcd1234efgh"\n')
    r = scan(str(f))
    assert r.returncode == 2
    findings = json.loads(r.stdout)
    assert any(x["severity"] == "CRITICAL" and x["category"] == "secrets" for x in findings)


def test_dangerous_python_patterns_high(tmp_path):
    f = tmp_path / "app.py"
    write(f, "import os, subprocess, yaml\n"
             "os.system('ls ' + user)\n"
             "yaml.load(data)\n"
             "subprocess.run(cmd, shell=True)\n"
             'q = f"SELECT * FROM t WHERE id={uid}"\n')
    findings = json.loads(scan(str(f)).stdout)
    cats = {x["category"] for x in findings}
    assert {"command-injection", "deserialization", "sql-injection"} <= cats
    assert all(x["severity"] in ("HIGH", "MEDIUM") for x in findings)  # no false CRITICAL


def test_secret_in_test_file_downgraded_to_low(tmp_path):
    f = tmp_path / "tests" / "test_app.py"
    write(f, 'API_KEY = "sk-test-fixture-000"\n')
    r = scan(str(f))
    assert r.returncode == 0  # LOW never blocks
    findings = json.loads(r.stdout)
    assert findings and findings[0]["severity"] == "LOW"


def test_clean_file_exit0_empty(tmp_path):
    f = tmp_path / "clean.py"
    write(f, "import os\nKEY = os.environ.get('API_KEY')\n")
    r = scan(str(f))
    assert r.returncode == 0 and json.loads(r.stdout) == []


def test_changed_scope_catches_staged_secret(tmp_path):
    """Regression: --changed must include STAGED files (pre-push gate hole)."""
    def git(*a):
        subprocess.run(["git", *a], cwd=tmp_path, capture_output=True, check=False)
    (tmp_path / ".blast").mkdir()   # marks project root for the scanner
    git("init", "-q"); git("config", "user.email", "t@t"); git("config", "user.name", "t")
    write(tmp_path / "app.py", "print('hi')\n")
    git("add", "-A"); git("commit", "-qm", "init")
    write(tmp_path / "app.py", "print('hi')\nTOKEN = \"sk-live-9999deadbeef\"\n")
    git("add", "app.py")  # staged, not committed
    r = scan("--changed", cwd=str(tmp_path))
    assert r.returncode == 2
