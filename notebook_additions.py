# STEP 1 - paste this as NEW CELLS at the END of your notebook (after the model-saving cell) and run it.
# It saves the two extra files the pipeline needs: label_encoder.pkl and score_model.pkl.

import joblib
from sklearn.base import clone
from sklearn.metrics import mean_absolute_error, r2_score, classification_report
from xgboost import XGBRegressor

# 1) Label encoder (needed to turn XGBoost's 0/1/2/3 back into Critical/High/Low/Medium)
joblib.dump(le, "label_encoder.pkl")

# 2) 0-100 score model (regressor on your cyber_risk_score column)
score_model = Pipeline([
    ("preprocessor", clone(preprocessor)),          # clone => independent copy, doesn't disturb other models
    ("regressor", XGBRegressor(n_estimators=300, max_depth=6, learning_rate=0.08, random_state=42))
])
score_model.fit(X_train, df.loc[X_train.index, "cyber_risk_score"])

pred_score = score_model.predict(X_test)
print("Score model  MAE:", round(mean_absolute_error(df.loc[X_test.index, "cyber_risk_score"], pred_score), 2),
      "| R2:", round(r2_score(df.loc[X_test.index, "cyber_risk_score"], pred_score), 4))
joblib.dump(score_model, "score_model.pkl")

# 3) Per-class report (puts the weak 'Low' class on display instead of hiding it in weighted averages)
print(classification_report(y_test_encoded, xgb_model.predict(X_test), target_names=le.classes_, zero_division=0))
