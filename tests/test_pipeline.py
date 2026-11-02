"""Scoring, SHAP attribution and remediation planning behave consistently."""
from rakshascore import pipeline as P


def default_record():
    return {c: (P.CAT[c]["default"] if c in P.CAT else P.NUM[c]["default"]) for c in P.COLUMNS}


def test_predict_returns_valid_score_and_tier():
    score, tier = P.predict(default_record())
    assert 0 <= score <= 100
    assert tier in set(P.LE.classes_)


def test_explain_all_covers_real_columns_and_sums_to_prediction():
    record = default_record()
    impacts = P.explain_all(record)
    assert impacts
    assert set(impacts) <= set(P.COLUMNS)
    total = P.base_value() + sum(impacts.values())
    assert abs(total - P.risk_score(record)) < 1.5


def test_best_fix_never_increases_the_score():
    record = default_record()
    for col in ("mfa_enabled", "backup_frequency", "patch_management"):
        value, score = P.best_fix(record, col)
        assert value in P.CAT[col]["values"]
        assert score <= P.risk_score(record)


def test_fix_plan_skips_immutable_fields_and_reports_positive_drops():
    plan = P.fix_plan(default_record(), top_k=4)
    for item in plan:
        assert item["column"] not in P.NOT_FIXABLE
        assert item["drop"] > 0
        assert item["to"] != item["from"]


def test_build_record_fills_defaults_and_tracks_assumptions():
    record, assumed = P.build_record({"mfa_enabled": "Yes"})
    assert record["mfa_enabled"] == "Yes"
    assert set(record) == set(P.COLUMNS)
    assert "mfa_enabled" not in assumed
    assert set(assumed) == set(P.COLUMNS) - {"mfa_enabled"}
