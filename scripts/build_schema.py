"""Read the dataset and write config/schema.json (allowed values + defaults per column).

The LLM prompt, input validation and the dashboard all read this file, so they always
match the dataset.

Usage:
    python scripts/build_schema.py [path/to/dataset.csv]
"""
import argparse
import json

import _bootstrap  # noqa: F401  (makes `rakshascore` importable)
import pandas as pd

from rakshascore import paths

TARGETS = ["risk_level", "cyber_risk_score"]


def build_schema(csv_path):
    df = pd.read_csv(csv_path)
    df["backup_frequency"] = df["backup_frequency"].fillna("Unknown")   # NaN means "no backups"
    X = df.drop(columns=TARGETS)

    schema = {"columns": list(X.columns), "categorical": {}, "numeric": {}}
    for c in X.columns:
        if X[c].dtype == object or str(X[c].dtype).startswith("str"):
            counts = X[c].value_counts()
            schema["categorical"][c] = {"values": [str(v) for v in counts.index],
                                        "default": str(counts.index[0])}   # most common value
        else:
            schema["numeric"][c] = {"min": float(X[c].min()), "max": float(X[c].max()),
                                    "default": float(X[c].median())}

    # Is a higher cyber_risk_score MORE risky? Compare the safest and riskiest tier.
    means = df.groupby("risk_level")["cyber_risk_score"].mean()
    order = [t for t in ["Low", "Medium", "High", "Critical"] if t in means.index]
    schema["score_higher_is_riskier"] = bool(means[order[-1]] > means[order[0]])
    print("Higher score means more risk:", schema["score_higher_is_riskier"])

    paths.SCHEMA_PATH.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print("schema.json written:", len(schema["categorical"]), "categorical,",
          len(schema["numeric"]), "numeric columns")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Build config/schema.json from the dataset.")
    ap.add_argument("csv", nargs="?", default=str(paths.DEFAULT_DATASET), help="dataset CSV")
    build_schema(ap.parse_args().csv)
