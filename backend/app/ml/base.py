"""Prediction interface. Any predictor (demo or real) must follow this contract."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional, Protocol


@dataclass
class PredictionResult:
    model_name: str
    model_version: str
    is_demo: bool
    target_date: str
    horizon_days: int
    score: Optional[int]                                  # 0-100 heat-risk / severity score
    expected: dict[str, Optional[float]] = field(default_factory=dict)  # temp_max_c, temp_min_c, apparent_max_c
    heatwave_probability: Optional[float] = None          # ONLY if a real model produced it
    confidence: Optional[float] = None                    # ONLY if the model has a meaningful confidence measure
    as_of_date: Optional[str] = None
    context: dict[str, Any] = field(default_factory=dict)  # extra labelled facts (e.g. historical frequency)
    notes: list[str] = field(default_factory=list)
    score_components: list[dict[str, Any]] = field(default_factory=list)
    missing_inputs: list[str] = field(default_factory=list)


class Predictor(Protocol):
    name: str
    version: str
    is_demo: bool

    def predict(self, db, city: dict[str, Any], target_date: date, horizon_days: int) -> PredictionResult: ...
