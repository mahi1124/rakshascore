# RakshaScore

**AI-assisted cyber risk assessment and remediation planning for small and medium businesses.**

RakshaScore turns a 37-question security questionnaire into a 0-100 risk score, a risk tier,
a per-answer SHAP explanation, a prioritised 30/60/90-day remediation roadmap, and a
print-ready management report. Answers can be typed manually or pre-filled from a free-text
description of the business using an LLM (Anthropic, Google Gemini, or a local Ollama model).
Without an API key the whole application still works offline using rule-based extraction and
template narratives.

---

## Features

| | |
|---|---|
| **Assessment** | Control-based questionnaire across 11 domains (identity, network, endpoint, patching, backup, governance, awareness, data, monitoring, third parties, profile). |
| **Scoring** | XGBoost classifier for the risk tier and an XGBoost regressor for the 0-100 score. |
| **Explanation** | SHAP values aggregated back to individual questions; waterfall view plus plain-language driver analysis. |
| **Remediation** | Every gap is re-scored by changing the answer, giving a *modelled* score reduction rather than a guess. |
| **What-if simulator** | Tick planned actions and the score recalculates live. |
| **Reports** | Executive HTML report (print to PDF), control register (CSV) and raw assessment data (JSON). |
| **AI intake** | Free-text description to questionnaire pre-fill, with a schema-validated JSON contract. |
| **Offline first** | Rule-based extraction and template narratives when no LLM is configured. |

---

## Project structure

```
.
├── app.py                       # Streamlit entry point (all six pages)
├── run.bat                      # one-click Windows setup + launch
├── pyproject.toml               # package metadata, dependencies, pytest config
├── requirements.txt
├── config/
│   └── schema.json              # allowed values, defaults and score direction
├── data/
│   └── SMB_Cyber_Risk_Dataset_10000_Rows.csv
├── models/
│   ├── cyber_risk_best_model_10k.pkl
│   ├── label_encoder.pkl
│   └── score_model.pkl
├── results/                     # generated metrics, plots and reports
├── scripts/
│   ├── build_schema.py          # regenerate config/schema.json from the dataset
│   ├── train_models.py          # train, compare and persist all models
│   └── evaluate_extraction.py   # extraction accuracy / consistency benchmark
├── src/rakshascore/
│   ├── paths.py                 # single source of truth for file locations
│   ├── pipeline.py              # extraction, prediction, SHAP, recommendations
│   └── insights.py              # knowledge base, narratives, HTML report
├── tests/                       # pytest suite + labelled extraction cases
├── notebooks/                   # original exploratory notebook
├── docs/                        # build notes + presentation generator and assets
└── archive/                     # unrelated student exercises and images
```

---

## Requirements

- Python **3.10+** (developed against 3.12)
- Windows, macOS or Linux
- No GPU required

---

## Quick start (Windows)

Double-click **`run.bat`**. It creates `.venv`, installs dependencies, installs the package in
editable mode, trains the models if they are missing, and launches the dashboard.

## Manual setup

```bash
# 1. Create and activate a virtual environment
py -3.12 -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS / Linux

# 2. Install dependencies and the package itself
python -m pip install -r requirements.txt
python -m pip install -e .

# 3. (Only if models/ is empty) train the models
python scripts/train_models.py

# 4. Launch the dashboard
streamlit run app.py
```

The app opens at <http://localhost:8501>.

---

## Configuration

Copy `.env.example` to `.env` and uncomment **one** provider:

```dotenv
# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-haiku-5-5

# Google Gemini (free tier)
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash

# Local Ollama
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2
```

You can also paste a Gemini key into the sidebar at runtime; it is kept in memory only.
`.env` is git-ignored — never commit real credentials.

---

## Usage

| Page | What it does |
|---|---|
| **Assessment** | Answer the controls; the score updates live. Optionally paste a description and pre-fill. |
| **Dashboard** | Executive view: score, tier, coverage, top SHAP drivers, domain summary. |
| **Score Explanation** | Waterfall of how each answer moved the score, with plain-language analysis. |
| **Remediation** | 30/60/90-day roadmap plus a what-if simulator. |
| **Reports** | Download the HTML report, CSV register and JSON data. |
| **Methodology** | Pipeline description, model metrics and limitations. |

---

## Training and evaluation

```bash
# Retrain on the bundled dataset (or a compatible CSV)
python scripts/train_models.py
python scripts/train_models.py path/to/other_dataset.csv

# Rebuild the questionnaire schema from a dataset
python scripts/build_schema.py

# Measure extraction quality against labelled cases
python scripts/evaluate_extraction.py
python scripts/evaluate_extraction.py --llm --repeat 3
```

Trained artefacts are written to `models/`; metrics and plots to `results/`.

## Tests

```bash
python -m pytest
```

The suite covers schema consistency, rule-based extraction against every labelled case,
scoring/SHAP invariants, remediation planning, and report rendering.

## Presentation

`RakshaScore_Presentation.pptx` is a 15-slide project deck with speaker notes, covering the
problem, architecture, model results, explainability, engineering and limitations.

```bash
# Rebuild it after changing the slides or screenshots
python docs/presentation/build_deck.py
```

Screenshots and the QR code live in `docs/presentation/assets/`; edit `build_deck.py` to
change the wording or layout.

---

## Dataset and model notes

- The bundled dataset is **synthetic**, generated from published small-business breach
  statistics. High accuracy shows the model learned the generator's scoring logic, not
  real-world predictive power.
- Answers are self-reported and framework mappings (CIS Controls v8, ISO/IEC 27001:2022,
  NIST CSF) are indicative, not a compliance assessment.
- A higher `cyber_risk_score` is treated as riskier; `config/schema.json` stores this as
  `score_higher_is_riskier` and the pipeline flips signs automatically if a dataset is reversed.
- Model binaries are committed so the dashboard runs out of the box. Delete them and rerun
  `scripts/train_models.py` if you change the dataset.

---

## Contributing

1. Fork the repository and create a feature branch (`feat/short-description`).
2. Keep changes consistent with the `src/rakshascore` package layout and add tests.
3. Run `python -m pytest` before opening a pull request.
4. Use conventional commit messages (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`).

Please do not commit datasets containing personal data, API keys, or `.env` files.

---

## License

Released under the [MIT License](LICENSE).
