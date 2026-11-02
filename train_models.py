"""
train_models.py  -  your project-2.ipynb converted into one script (+ the extra pieces the pipeline needs).

Run from the VS Code terminal (venv active, inside the project folder):
    python train_models.py
    python train_models.py path/to/other_dataset.csv

What it does
  1. Loads the dataset and prepares X / y                      (notebook cells 0-2)
  2. Builds the preprocessing + 4 models and compares them     (cells 3-9)
  3. Picks the best model, saves it                            (cells 10-11)
  4. Trains the 0-100 score model (regressor)                  (new)
  5. Creates SHAP plot, per-class report, cross-validation     (new)
Everything printed is also saved in the results/ folder, so you never have to re-run before the review.
"""
import os
import sys
import warnings

import joblib
import matplotlib
matplotlib.use("Agg")                      # draw to files instead of opening windows
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (ConfusionMatrixDisplay, accuracy_score, classification_report, f1_score,
                             mean_absolute_error, precision_score, r2_score, recall_score)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier, XGBRegressor

warnings.filterwarnings("ignore")
CSV = sys.argv[1] if len(sys.argv) > 1 else "SMB_Cyber_Risk_Dataset_10000_Rows.csv"
RESULTS = "results"
os.makedirs(RESULTS, exist_ok=True)

# ------------------------------------------------------------------ 1. load + prepare
df = pd.read_csv(CSV)
print("Dataset shape:", df.shape)
print("\nMissing values (non-zero only):\n", df.isnull().sum()[df.isnull().sum() > 0])
print("\nRisk level distribution:\n", df["risk_level"].value_counts())

X = df.drop(columns=["risk_level", "cyber_risk_score"])
y = df["risk_level"]
X["backup_frequency"] = X["backup_frequency"].fillna("Unknown")      # NaN means "no backups"

# ------------------------------------------------------------------ 2. preprocessing + split
numeric_cols = X.select_dtypes(include="number").columns
categorical_cols = [c for c in X.columns if c not in set(numeric_cols)]      # everything that is not a number

preprocessor = ColumnTransformer([
    ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_cols),
    ("num", StandardScaler(), list(numeric_cols)),                   # scaling fixes Logistic Regression's convergence warning
])

le = LabelEncoder()
y_encoded = le.fit_transform(y)                                      # Critical=0, High=1, Low=2, Medium=3
X_train, X_test, y_train, y_test = train_test_split(
    X, y_encoded, test_size=0.20, random_state=42, stratify=y_encoded)
print("\nTrain:", X_train.shape, " Test:", X_test.shape)

# ------------------------------------------------------------------ 3. four models (all use encoded labels)
def make(classifier):
    return Pipeline([("preprocessor", clone(preprocessor)), ("classifier", classifier)])

models = {
    "Logistic Regression": make(LogisticRegression(max_iter=3000, C=2.0, class_weight="balanced")),
    "Decision Tree": make(DecisionTreeClassifier(random_state=42, class_weight="balanced",
                                                 max_depth=16, min_samples_split=5)),
    "Random Forest": make(RandomForestClassifier(n_estimators=300, max_depth=20, random_state=42,
                                                 class_weight="balanced", n_jobs=-1)),
    "XGBoost": make(XGBClassifier(n_estimators=300, max_depth=8, learning_rate=0.08,
                                  random_state=42, eval_metric="mlogloss")),
}

rows = []
for name, model in models.items():
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    rows.append({
        "Model": name,
        "Accuracy": accuracy_score(y_test, pred),
        "Precision (weighted)": precision_score(y_test, pred, average="weighted", zero_division=0),
        "Recall (weighted)": recall_score(y_test, pred, average="weighted", zero_division=0),
        "F1 (weighted)": f1_score(y_test, pred, average="weighted", zero_division=0),
        "F1 (macro)": f1_score(y_test, pred, average="macro", zero_division=0),   # treats the rare 'Low' class fairly
    })
    print(f"trained {name}")

results_df = pd.DataFrame(rows).round(4)
results_df.to_csv(f"{RESULTS}/model_comparison.csv", index=False)
print("\nMODEL COMPARISON\n", results_df.to_string(index=False))

# ------------------------------------------------------------------ 4. best model: report, confusion matrix, importance
best_name = results_df.loc[results_df["F1 (weighted)"].idxmax(), "Model"]
best_model = models[best_name]
best_pred = best_model.predict(X_test)
print("\nBest model:", best_name)

report = classification_report(y_test, best_pred, target_names=le.classes_, zero_division=0)
print("\nPER-CLASS REPORT\n", report)
open(f"{RESULTS}/classification_report.txt", "w").write(f"Best model: {best_name}\n\n{report}")

ConfusionMatrixDisplay.from_predictions(le.inverse_transform(y_test), le.inverse_transform(best_pred),
                                        xticks_rotation=45)
plt.title(f"Confusion Matrix - {best_name}")
plt.tight_layout()
plt.savefig(f"{RESULTS}/confusion_matrix.png", dpi=200)
plt.close()

clf = best_model.named_steps["classifier"]
names = best_model.named_steps["preprocessor"].get_feature_names_out()
if hasattr(clf, "feature_importances_"):
    imp = clf.feature_importances_
else:
    imp = np.mean(np.abs(clf.coef_), axis=0)
importance = pd.DataFrame({"Feature": names, "Importance": imp}).sort_values("Importance", ascending=False)
importance.to_csv(f"{RESULTS}/feature_importance.csv", index=False)
print("\nTop 10 features:\n", importance.head(10).to_string(index=False))

# 5-fold cross-validation (shows the result is not a lucky split)
cv = StratifiedKFold(5, shuffle=True, random_state=42)
cv_scores = cross_val_score(clone(best_model), X, y_encoded, cv=cv, scoring="f1_macro")
print(f"\n5-fold CV macro-F1 ({best_name}): {cv_scores.mean():.4f} +/- {cv_scores.std():.4f}")
open(f"{RESULTS}/cross_validation.txt", "w").write(f"{best_name} 5-fold macro-F1: {cv_scores.mean():.4f} +/- {cv_scores.std():.4f}\n")

joblib.dump(best_model, "cyber_risk_best_model_10k.pkl")
joblib.dump(le, "label_encoder.pkl")

# ------------------------------------------------------------------ 5. 0-100 score model + SHAP
score_model = Pipeline([
    ("preprocessor", clone(preprocessor)),
    ("regressor", XGBRegressor(n_estimators=300, max_depth=6, learning_rate=0.08, random_state=42)),
])
score_model.fit(X_train, df.loc[X_train.index, "cyber_risk_score"])
score_pred = score_model.predict(X_test)
mae = mean_absolute_error(df.loc[X_test.index, "cyber_risk_score"], score_pred)
r2 = r2_score(df.loc[X_test.index, "cyber_risk_score"], score_pred)
print(f"\nScore model  MAE: {mae:.2f}   R2: {r2:.4f}")
open(f"{RESULTS}/score_model_metrics.txt", "w").write(f"MAE: {mae:.2f}\nR2: {r2:.4f}\n")
joblib.dump(score_model, "score_model.pkl")

pre = score_model.named_steps["preprocessor"]
Xt = pre.transform(X_test.iloc[:1000])
Xt = Xt.toarray() if hasattr(Xt, "toarray") else Xt
shap_values = shap.TreeExplainer(score_model.named_steps["regressor"]).shap_values(Xt)
shap.summary_plot(shap_values, Xt, feature_names=pre.get_feature_names_out(), show=False, max_display=15)
plt.tight_layout()
plt.savefig(f"{RESULTS}/shap_summary.png", dpi=200, bbox_inches="tight")
plt.close()

print(f"\nDONE. Models saved in this folder; plots and tables saved in ./{RESULTS}/")
