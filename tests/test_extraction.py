"""Offline (rule-based) extraction must satisfy every labelled case in test_cases.json."""
import json

import pytest

from rakshascore import paths, pipeline as P

CASES = json.loads(paths.DEFAULT_TEST_CASES.read_text(encoding="utf-8"))
POOR = {"poor", "weak", "low", "no", "none", "never"}


def matches(have, want):
    if want == "POOR":
        return have is not None and str(have).lower() in POOR
    if isinstance(want, (int, float)):
        return have is not None and abs(float(have) - float(want)) < 0.5
    return have == want


@pytest.mark.parametrize("case", CASES, ids=[c["text"][:45] for c in CASES])
def test_rule_based_extraction(case):
    found, method = P.extract_factors(case["text"], use_llm=False)
    assert method == "rule-based fallback"
    for field, want in case["expected"].items():
        assert matches(found.get(field), want), f"{field}: expected {want!r}, got {found.get(field)!r}"


def test_validation_drops_unknown_values():
    clean = P._validate({"mfa_enabled": "Definitely", "industry": "Retail", "employee_count": 999999})
    assert "mfa_enabled" not in clean
    assert clean["industry"] == "Retail"
    assert clean["employee_count"] == P.NUM["employee_count"]["max"]
