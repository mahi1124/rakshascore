"""Single source of truth for every filesystem location used by the project."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
MODELS_DIR = ROOT / "models"
RESULTS_DIR = ROOT / "results"
TESTS_DIR = ROOT / "tests"

SCHEMA_PATH = CONFIG_DIR / "schema.json"
CLF_PATH = MODELS_DIR / "cyber_risk_best_model_10k.pkl"
LABEL_ENCODER_PATH = MODELS_DIR / "label_encoder.pkl"
SCORE_MODEL_PATH = MODELS_DIR / "score_model.pkl"

DEFAULT_DATASET = DATA_DIR / "SMB_Cyber_Risk_Dataset_10000_Rows.csv"
DEFAULT_TEST_CASES = TESTS_DIR / "test_cases.json"
ENV_PATH = ROOT / ".env"
