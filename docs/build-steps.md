# RakshaScore build steps (legacy notes)

> These are the original step-by-step notes, kept for reference. The canonical, up-to-date
> instructions live in [`../README.md`](../README.md). Paths below reflect the reorganized
> layout.

## Layout

```
config/schema.json                        <- created in step 2
data/SMB_Cyber_Risk_Dataset_10000_Rows.csv
models/cyber_risk_best_model_10k.pkl      <- created by train_models.py
models/label_encoder.pkl                  <- created by train_models.py
models/score_model.pkl                    <- created by train_models.py
results/                                  <- metrics, plots and tables
app.py, src/rakshascore/, scripts/, tests/
```

## Step 0 - Install

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
```

## Step 1 - Train everything with one command

```bash
python scripts/train_models.py
```

This is the notebook converted to a script, plus the score model, SHAP plot, per-class report
and cross-validation. It saves the three model files in `models/` and all tables/plots in
`results/` (`model_comparison.csv`, `classification_report.txt`, `confusion_matrix.png`,
`shap_summary.png`, `cross_validation.txt`, `feature_importance.csv`,
`score_model_metrics.txt`). `notebooks/notebook_additions.py` is only needed if you prefer to
keep working inside the notebook.

## Step 2 - Build the schema

```bash
python scripts/build_schema.py data/SMB_Cyber_Risk_Dataset_10000_Rows.csv
```

Creates `config/schema.json` (allowed values + defaults for all 37 columns).

## Step 3 - Test the pipeline without an LLM

```bash
python -c "from rakshascore import pipeline as P; f,m=P.extract_factors('We do not use MFA and backups are monthly'); print(m,f)"
```

Uses the rule-based fallback. Works offline.

## Step 4 - Turn on the LLM (optional)

Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY` or `GEMINI_API_KEY`.
Use `LLM_PROVIDER=ollama` to run a local model. You can also paste a Gemini key in the sidebar.

## Step 5 - Run the dashboard

```bash
streamlit run app.py
```

*(or double-click `run.bat` on Windows)*

## Step 6 - Evaluate (the "Output Analysis" slide)

1. Add 20-30 cases to `tests/test_cases.json` (text + expected values from your dataset).
2. `python scripts/evaluate_extraction.py` (rule-based) and
   `python scripts/evaluate_extraction.py --llm --repeat 3` (LLM + consistency).
3. Compare LLM vs rule-based accuracy, and both vs manual entry time.

## Things to say honestly in the review

- Only fields mentioned in the text are "extracted"; the rest use the most common dataset
  value and are labelled "assumed".
- Labels come from a synthetic formula, so high accuracy shows the model learned that formula,
  not real-world validity.
- Check the `cyber_risk_score` direction: this code assumes HIGHER = MORE RISK. If your dataset
  is the reverse, `config/schema.json` records it and the pipeline flips signs automatically.
