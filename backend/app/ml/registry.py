"""Chooses the predictor: a real model if MODEL_PATH points to a loadable file, otherwise the DEMO predictor."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from app.ml.base import Predictor
from app.ml.demo_predictor import DemoClimatologyPredictor

_state: dict[str, Any] = {"predictor": None, "status": None, "key": None}


def get_predictor(model_path: str = "") -> Predictor:
    if _state["predictor"] is not None and _state["key"] == model_path:
        return _state["predictor"]
    predictor: Predictor
    status: dict[str, Any]
    if model_path and Path(model_path).is_file():
        try:
            import joblib  # optional dependency (pip install joblib scikit-learn)

            from app.ml.sklearn_predictor import SklearnPredictor

            model = joblib.load(model_path)
            predictor = SklearnPredictor(model, name=Path(model_path).stem)
            status = {"mode": "trained", "model_name": predictor.name, "model_version": predictor.version,
                      "message": "A user-supplied model is loaded. Its accuracy has not been validated by this application."}
        except Exception as exc:  # fall back safely; the app must keep working
            predictor = DemoClimatologyPredictor()
            status = {"mode": "demo", "model_name": predictor.name, "model_version": predictor.version,
                      "message": f"Model file could not be loaded ({type(exc).__name__}: {exc}). Using the demo predictor."}
    else:
        predictor = DemoClimatologyPredictor()
        why = "MODEL_PATH is not set." if not model_path else f"MODEL_PATH file not found: {model_path}"
        status = {"mode": "demo", "model_name": predictor.name, "model_version": predictor.version,
                  "message": f"No trained model connected ({why}) - predictions come from the DEMO climatology baseline."}
    status.update({"confidence_available": False, "accuracy_metrics": None})
    _state.update({"predictor": predictor, "status": status, "key": model_path})
    return predictor


def model_status(model_path: str = "") -> dict[str, Any]:
    get_predictor(model_path)
    return _state["status"]
