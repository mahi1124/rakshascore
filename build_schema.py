"""STEP 2 - Reads your CSV and writes schema.json (allowed values + defaults per column).
The LLM prompt, the validation and the dashboard all read this file, so they always match your dataset.
Usage:  python build_schema.py SMB_Cyber_Risk_Dataset_10000_Rows.csv
"""
import json, sys
import pandas as pd

CSV = sys.argv[1] if len(sys.argv) > 1 else "SMB_Cyber_Risk_Dataset_10000_Rows.csv"
TARGETS = ["risk_level", "cyber_risk_score"]

df = pd.read_csv(CSV)
df["backup_frequency"] = df["backup_frequency"].fillna("Unknown")   # same fix as your notebook
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

# Is a higher cyber_risk_score MORE risky? Compare average score of the safest vs riskiest tier.
means = df.groupby("risk_level")["cyber_risk_score"].mean()
order = [t for t in ["Low", "Medium", "High", "Critical"] if t in means.index]
schema["score_higher_is_riskier"] = bool(means[order[-1]] > means[order[0]])
print("Higher score means more risk:", schema["score_higher_is_riskier"])

json.dump(schema, open("schema.json", "w"), indent=2)
print("schema.json written:", len(schema["categorical"]), "categorical,", len(schema["numeric"]), "numeric columns")