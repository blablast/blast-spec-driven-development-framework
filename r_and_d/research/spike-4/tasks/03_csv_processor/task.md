# Task 03 — CSV Validator/Processor

Implement a CSV processor with validation and error aggregation in `csv_processor.py`.

## Spec

```python
def process_csv(path: str, schema: dict) -> dict:
    """
    Parse CSV file, validate each row against schema, aggregate errors.

    schema example:
        {
            "name": {"type": "str", "required": True, "min_len": 1},
            "age": {"type": "int", "required": True, "min": 0, "max": 150},
            "email": {"type": "str", "required": False, "regex": r"^[^@]+@[^@]+\\.[^@]+$"},
        }

    Returns:
        {
            "valid_rows": [list of dicts that passed],
            "errors": [list of {"row_num": N, "field": "...", "issue": "..."} ],
            "summary": {"total": int, "valid": int, "errors": int},
        }
    """
```

## Requirements

- Use `csv` stdlib module
- Skip blank rows, count them in summary
- Validate type coercion (e.g., "25" → int 25)
- Handle missing file gracefully (return error in result, don't crash)
- Pure stdlib only

## Acceptance criteria

All tests in `tests.py` must pass.
