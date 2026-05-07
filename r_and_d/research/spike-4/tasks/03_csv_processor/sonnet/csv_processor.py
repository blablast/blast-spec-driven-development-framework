import csv
import re


def process_csv(path: str, schema: dict) -> dict:
    valid_rows = []
    errors = []
    total = 0

    try:
        f = open(path, newline="", encoding="utf-8")
    except (FileNotFoundError, OSError) as e:
        return {
            "valid_rows": [],
            "errors": [{"row_num": 0, "field": None, "issue": str(e)}],
            "summary": {"total": 0, "valid": 0, "errors": 1},
        }

    with f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=1):
            if all(v.strip() == "" for v in row.values()):
                continue

            total += 1
            row_errors = []

            for field, rules in schema.items():
                raw = row.get(field, "")
                value = raw.strip() if raw else ""
                required = rules.get("required", False)
                ftype = rules.get("type", "str")

                if value == "":
                    if required:
                        row_errors.append({"row_num": row_num, "field": field, "issue": "required field missing"})
                    continue

                if ftype == "int":
                    try:
                        value = int(value)
                    except ValueError:
                        row_errors.append({"row_num": row_num, "field": field, "issue": f"cannot coerce to int: {raw!r}"})
                        continue
                    if "min" in rules and value < rules["min"]:
                        row_errors.append({"row_num": row_num, "field": field, "issue": f"value {value} below min {rules['min']}"})
                    if "max" in rules and value > rules["max"]:
                        row_errors.append({"row_num": row_num, "field": field, "issue": f"value {value} above max {rules['max']}"})
                elif ftype == "str":
                    if "min_len" in rules and len(value) < rules["min_len"]:
                        row_errors.append({"row_num": row_num, "field": field, "issue": f"length {len(value)} below min_len {rules['min_len']}"})
                    if "regex" in rules and not re.match(rules["regex"], value):
                        row_errors.append({"row_num": row_num, "field": field, "issue": f"value {value!r} does not match regex"})

            if row_errors:
                errors.extend(row_errors)
            else:
                coerced = {}
                for field, rules in schema.items():
                    raw = row.get(field, "")
                    value = raw.strip() if raw else ""
                    if value == "":
                        coerced[field] = value
                        continue
                    if rules.get("type") == "int":
                        coerced[field] = int(value)
                    else:
                        coerced[field] = value
                valid_rows.append(coerced)

    valid = len(valid_rows)
    return {
        "valid_rows": valid_rows,
        "errors": errors,
        "summary": {"total": total, "valid": valid, "errors": total - valid},
    }