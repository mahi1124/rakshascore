# RakshaScore pipeline - build steps

Folder layout (put all files in ONE folder together with your CSV and the .pkl files):
```
SMB_Cyber_Risk_Dataset_10000_Rows.csv     <- your dataset
cyber_risk_best_model_10k.pkl             <- already saved by your notebook
label_encoder.pkl, score_model.pkl        <- created in STEP 1
schema.json                               <- created in STEP 2
pipeline.py, app.py, evaluate_extraction.py, test_cases.json
```

## STEP 0 - Install
```
pip install -r requirements.txt
```

## STEP 1 - Train everything with ONE command (replaces running the notebook)
```
python train_models.py
```
This is your notebook converted to a script, plus the score model, SHAP plot, per-class report and cross-validation.
It saves the 3 model files here and all tables/plots in `results/` (model_comparison.csv, classification_report.txt,
confusion_matrix.png, shap_summary.png, cross_validation.txt, feature_importance.csv, score_model_metrics.txt).
(`notebook_additions.py` is only needed if you prefer to keep working inside the notebook.)

## STEP 2 - Build the schema
```
python build_schema.py SMB_Cyber_Risk_Dataset_10000_Rows.csv
```
Creates `schema.json` (allowed values + defaults for all 37 columns).

## STEP 3 - Test the pipeline without an LLM
```
python -c "import pipeline as P; f,m=P.extract_factors('We do not use MFA and backups are monthly'); print(m,f)"
```
Uses the rule-based fallback. Works offline.

## STEP 4 - Turn on the LLM (optional but recommended)
```
setx ANTHROPIC_API_KEY "your-key"        (Windows - reopen the terminal)
export ANTHROPIC_API_KEY="your-key"      (Mac/Linux)
```
Optional: `LLM_MODEL` environment variable to change the model (default claude-haiku-5-5).
Using another provider? Edit only the `call_llm()` function in pipeline.py.

## STEP 5 - Run the dashboard
```
streamlit run app.py
```

## STEP 6 - Evaluate (this becomes your "Output Analysis" slide)
1. Add 20-30 cases to `test_cases.json` (text + expected values, using YOUR dataset's real labels).
2. `python evaluate_extraction.py` (rule-based) and `python evaluate_extraction.py --llm --repeat 3` (LLM + consistency).
3. Compare: LLM vs rule-based accuracy, and both vs manual entry time.

## Things to say honestly in the review
- Only fields mentioned in the text are "extracted"; the rest use the most common dataset value and are labelled "assumed".
- Labels come from a synthetic formula, so high accuracy shows the model learned that formula, not real-world validity.
- Check `cyber_risk_score` direction: this code assumes HIGHER = MORE RISK. If your dataset is the reverse, flip the SHAP sign in `explain()`.
