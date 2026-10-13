"""
Feature contract for a REAL trained model.

If you train your own model, edit FEATURE_ORDER so it matches the columns your model was trained on,
then save the model with joblib and set MODEL_PATH in backend/.env (see docs/architecture.md).

The shipped SklearnPredictor expects:
  * a scikit-learn-compatible object with  predict_proba(X)  where X has the columns in FEATURE_ORDER and
    column 1 of the output is P(heatwave within the horizon).
Anything else needs a small adapter in ml/sklearn_predictor.py.
"""
FEATURE_ORDER = [
    "temp_max_c",
    "temp_min_c",
    "apparent_max_c",
    "temp_max_mean_3d",
    "temp_max_mean_7d",
    "precipitation_sum_7d_mm",
    "wind_speed_max_kmh",
    "month",
    "hot_day_streak",
]

VALID_RANGES = {  # used to validate inputs before they reach the model
    "temp_max_c": (-10, 60), "temp_min_c": (-20, 45), "apparent_max_c": (-20, 70),
    "temp_max_mean_3d": (-10, 60), "temp_max_mean_7d": (-10, 60),
    "precipitation_sum_7d_mm": (0, 2000), "wind_speed_max_kmh": (0, 250),
    "month": (1, 12), "hot_day_streak": (0, 400),
}
