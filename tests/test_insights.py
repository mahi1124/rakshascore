"""Insight generation and the HTML report render completely in offline mode."""
from rakshascore import insights as I, pipeline as P


def default_record():
    return {c: (P.CAT[c]["default"] if c in P.CAT else P.NUM[c]["default"]) for c in P.COLUMNS}


def build_offline_insights():
    record = default_record()
    score, tier = P.predict(record)
    impacts = P.explain_all(record)
    ins = I.build_insights(record, score, tier, impacts, {"name": "Test Co"}, use_llm=False)
    return record, score, tier, ins


def test_offline_insights_are_complete():
    record, score, tier, ins = build_offline_insights()
    assert ins["executive_summary"]
    assert ins["source"].startswith("Template-generated")
    assert ins["register"]
    assert ins["domains"]
    assert ins["phases"]
    assert ins["projected"] <= score
    for d in ins["drivers"]:
        assert d["col"] in record


def test_waterfall_geometry_is_shared_and_bounded():
    _, score, _, ins = build_offline_insights()
    base, bars = I.waterfall_geometry(ins)
    assert bars[0]["delta"] is None
    assert bars[0]["width"] >= 0
    assert abs(base + sum(b["delta"] for b in bars[1:]) - score) < 1.5  # deltas are rounded
    assert all(0 <= b["left"] <= 100 for b in bars)


def test_report_html_contains_report_sections():
    _, score, tier, ins = build_offline_insights()
    report = I.report_html(
        {"org": "Test Co", "ref": "RS-TEST", "assessor": "QA", "scope": "All systems"},
        {"score": score, "tier": tier, "when": "today"},
        ins,
    )
    for needle in ("Cyber Risk Assessment Report", "Test Co", "Executive summary",
                   "Remediation roadmap", "Control register"):
        assert needle in report
