"""
Configurable settings for the HEATVERSE heat-risk score and the heatwave-event definition.

IMPORTANT: this is an informational PROJECT metric. It is NOT an official government
heat warning (for official warnings see the India Meteorological Department, IMD).
Edit the numbers below to tune the metric; every value is used by the code and shown in the UI/docs.
"""

SCORING_VERSION = "1.0"

# Each component is converted to a 0-100 sub-score with linear scaling:
#     sub_score = clamp((value - low) / (high - low), 0, 1) * 100
# The final score is the weighted average of the AVAILABLE components
# (if a value is missing its weight is redistributed; the response lists what was missing).
COMPONENTS = {
    "temp_max_c": {"label": "Maximum temperature", "unit": "°C", "weight": 0.45, "low": 30.0, "high": 46.0},
    "apparent_max_c": {"label": "Apparent (feels-like) maximum temperature", "unit": "°C", "weight": 0.30, "low": 32.0, "high": 50.0},
    "temp_min_c": {"label": "Night-time minimum temperature", "unit": "°C", "weight": 0.10, "low": 22.0, "high": 32.0},
    "hot_day_streak": {"label": "Consecutive hot days", "unit": "days", "weight": 0.15, "low": 0.0, "high": 5.0},
}

# (lower bound, upper bound, label) -- applies to the SCORE, not to raw temperatures.
CATEGORIES = [
    (0, 24, "Low"),
    (25, 49, "Moderate"),
    (50, 74, "High"),
    (75, 100, "Extreme"),
]

CATEGORY_COLORS = {"Low": "#2F855A", "Moderate": "#D69E2E", "High": "#DD6B20", "Extreme": "#C53030"}

# A "hot day" is a day whose maximum temperature reaches this threshold.
HOT_DAY_THRESHOLD_C = 40.0
COASTAL_HOT_DAY_THRESHOLD_C = 37.0
COASTAL_CITIES = {"Mumbai", "Chennai"}

# Project definition of a heatwave EVENT (modelled on the IMD plains criteria, simplified):
#   a day counts as a heatwave day if Tmax >= hot-day threshold AND
#       (Tmax - monthly normal >= min_departure_c  OR  Tmax >= absolute_tmax_c)
#   an event is >= min_consecutive_days consecutive heatwave days.
#   "Severe" if departure >= severe_departure_c or Tmax >= severe_absolute_tmax_c on any day.
# The monthly normal is the 2000-2024 mean of Tmax for that city and calendar month (in-sample).
HEATWAVE = {
    "min_departure_c": 4.5,
    "severe_departure_c": 6.5,
    "absolute_tmax_c": 45.0,
    "severe_absolute_tmax_c": 47.0,
    "min_consecutive_days": 2,
}

# Heuristic personal-factor adjustments (project metric, not medical advice).
PERSONAL_ADJUSTMENTS = {
    "age_vulnerable": {"points": 10, "label": "Age 60+ or 5 and under"},
    "outdoor_worker": {"points": 8, "label": "Works outdoors"},
    "high_activity": {"points": 6, "label": "High physical activity"},
    "moderate_activity": {"points": 3, "label": "Moderate physical activity"},
}

SEASONS = {  # Indian meteorological seasons by calendar month
    12: "Winter", 1: "Winter", 2: "Winter",
    3: "Summer", 4: "Summer", 5: "Summer",
    6: "Monsoon", 7: "Monsoon", 8: "Monsoon", 9: "Monsoon",
    10: "Post-monsoon", 11: "Post-monsoon",
}

WMO_WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    95: "Thunderstorm",
}
