"""Parse a YAML-like config file into a dict."""
import re
from pathlib import Path


def parse_config(path: str) -> dict:
    """Load and parse the config file at the given path.

    Supports lines like `key: value` with simple type coercion (int, float,
    bool). Lines starting with `#` and blank lines are skipped.
    """
    config: dict = {}
    try:
        text = Path(path).read_text()
    except Exception:
        return config

    for line_num, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        try:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()

            # Type coercion
            if value.isdigit():
                config[key] = int(value)
            elif re.match(r"^-?\d+\.\d+$", value):
                config[key] = float(value)
            elif value.lower() in ("true", "false"):
                config[key] = value.lower() == "true"
            else:
                config[key] = value
        except Exception:
            pass  # ignore malformed lines

    return config


def merge_configs(base_path: str, override_path: str) -> dict:
    """Merge two configs, override wins on conflicts."""
    base = parse_config(base_path)
    override = parse_config(override_path)
    base.update(override)
    return base
