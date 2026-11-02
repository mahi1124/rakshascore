"""config/schema.json must stay in sync with the shipped dataset."""
import json

import pandas as pd

from rakshascore import paths

TARGETS = {"risk_level", "cyber_risk_score"}


def load_schema():
    return json.loads(paths.SCHEMA_PATH.read_text(encoding="utf-8"))


def test_schema_columns_match_dataset():
    schema = load_schema()
    df = pd.read_csv(paths.DEFAULT_DATASET, nrows=5)
    expected = [c for c in df.columns if c not in TARGETS]
    assert schema["columns"] == expected


def test_categorical_and_numeric_partition_columns():
    schema = load_schema()
    cat, num = set(schema["categorical"]), set(schema["numeric"])
    assert not cat & num
    assert cat | num == set(schema["columns"])


def test_defaults_are_within_allowed_values():
    schema = load_schema()
    for name, spec in schema["categorical"].items():
        assert spec["default"] in spec["values"], name
    for name, spec in schema["numeric"].items():
        assert spec["min"] <= spec["default"] <= spec["max"], name
