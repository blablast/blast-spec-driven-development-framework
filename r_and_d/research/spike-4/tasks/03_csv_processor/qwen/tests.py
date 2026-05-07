"""Tests for Task 03 — CSV Processor."""
import os
import tempfile
import pytest
from csv_processor import process_csv


@pytest.fixture
def schema():
    return {
        "name": {"type": "str", "required": True, "min_len": 1},
        "age": {"type": "int", "required": True, "min": 0, "max": 150},
        "email": {"type": "str", "required": False, "regex": r"^[^@]+@[^@]+\.[^@]+$"},
    }


def write_csv(content):
    fd, path = tempfile.mkstemp(suffix=".csv", text=True)
    with os.fdopen(fd, "w", newline="") as f:
        f.write(content)
    return path


def test_all_valid(schema):
    path = write_csv("name,age,email\nAlice,30,alice@example.com\nBob,25,bob@test.io\n")
    try:
        result = process_csv(path, schema)
        assert result["summary"]["total"] == 2
        assert result["summary"]["valid"] == 2
        assert result["summary"]["errors"] == 0
        assert len(result["valid_rows"]) == 2
        assert result["valid_rows"][0]["age"] == 30  # type-coerced to int
    finally:
        os.unlink(path)


def test_invalid_age(schema):
    path = write_csv("name,age,email\nAlice,abc,a@b.c\nBob,200,b@c.d\n")
    try:
        result = process_csv(path, schema)
        assert result["summary"]["errors"] >= 2
        assert any(e["field"] == "age" for e in result["errors"])
    finally:
        os.unlink(path)


def test_missing_required(schema):
    path = write_csv("name,age,email\n,30,a@b.c\nBob,,b@c.d\n")
    try:
        result = process_csv(path, schema)
        assert result["summary"]["errors"] >= 2
    finally:
        os.unlink(path)


def test_invalid_email(schema):
    path = write_csv("name,age,email\nAlice,30,not-an-email\n")
    try:
        result = process_csv(path, schema)
        assert any(e["field"] == "email" for e in result["errors"])
    finally:
        os.unlink(path)


def test_optional_email_missing_ok(schema):
    path = write_csv("name,age,email\nAlice,30,\n")
    try:
        result = process_csv(path, schema)
        assert result["summary"]["valid"] == 1
    finally:
        os.unlink(path)


def test_missing_file_graceful(schema):
    result = process_csv("/nonexistent/path/file.csv", schema)
    assert "errors" in result
    assert result["summary"]["valid"] == 0
