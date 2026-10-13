"""
Educational heat-safety content. This is general information, NOT medical advice.
No hospital names, phone numbers or distances are invented here.
"""
from __future__ import annotations

from typing import Any

DISCLAIMER = ("This is general educational guidance, not medical advice. If you or someone else may be seriously ill, "
              "call your local emergency number immediately (112 is India's national emergency number; "
              "108 is an ambulance service in many states - confirm what applies where you are).")

BY_CATEGORY = {
    "Low": [
        "Normal precautions: carry water and drink regularly through the day.",
        "Wear light, loose clothing and use sun protection outdoors.",
    ],
    "Moderate": [
        "Drink water often, even if you are not thirsty.",
        "Plan strenuous outdoor activity for early morning or evening.",
        "Take breaks in shade or air-conditioning and check on elderly neighbours.",
    ],
    "High": [
        "Avoid strenuous outdoor activity between about 11:00 and 16:00.",
        "Drink fluids regularly (oral rehydration solution if you sweat a lot); avoid alcohol and very sugary drinks.",
        "Never leave children or pets in a parked vehicle.",
        "Know the signs of heat exhaustion and heatstroke (below).",
    ],
    "Extreme": [
        "Stay indoors in the coolest place available during the hottest hours; postpone non-essential outdoor activity.",
        "Outdoor workers should have frequent shaded rest breaks and a buddy system.",
        "Check on infants, older adults, pregnant women and people with chronic illness more than once a day.",
        "Seek medical help early if symptoms of heat illness appear.",
    ],
}

VULNERABLE = [
    "Infants and young children heat up faster and cannot always say they feel unwell.",
    "Adults aged 60+ may have a weaker thirst response and often take medicines that affect heat tolerance.",
    "Pregnant women and people with heart, kidney or respiratory conditions should discuss heat plans with their doctor.",
    "People living alone should arrange for someone to check on them during hot spells.",
]

OUTDOOR_WORK = [
    "Schedule heavy work for cooler hours and rotate tasks.",
    "Take short, frequent rest breaks in shade; drink about a cup of water every 15-20 minutes when working in heat.",
    "Wear a wide-brimmed hat and light, breathable clothing.",
    "Watch co-workers for confusion, dizziness or unusual behaviour.",
]

HEAT_ILLNESS = {
    "heat_exhaustion": {
        "signs": ["Heavy sweating", "Weakness or fatigue", "Dizziness, headache, nausea", "Cool, clammy skin", "Muscle cramps"],
        "actions": ["Move to a cool place and lie down", "Loosen clothing and cool the skin with water or wet cloths",
                    "Sip water or oral rehydration solution", "Seek medical help if symptoms last more than about an hour or worsen"],
    },
    "heatstroke": {
        "signs": ["Body temperature of about 40 °C or higher", "Confusion, slurred speech, seizures or unconsciousness",
                  "Hot, red skin (sweating may stop)", "Rapid pulse and breathing"],
        "actions": ["This is a medical emergency - call your local emergency number now",
                    "Move the person to shade or a cool place and cool them quickly (cool water, wet cloths, fanning)",
                    "Do not force fluids on someone who is confused or unconscious"],
    },
}

HYDRATION_COOLING = [
    "Drink water regularly through the day; urine should be pale yellow.",
    "Cool showers or wet cloths on the neck, wrists and face help lower body temperature.",
    "Keep curtains closed on sun-facing windows by day; use fans only as a supplement when it is very hot.",
    "Eat light meals; avoid heavy, oily food in the hottest hours.",
]


def recommendations_for(category: str | None, profile: dict[str, Any] | None = None) -> list[str]:
    if not category:
        return ["No heat-risk category is available, so no tailored guidance can be shown."]
    recs = list(BY_CATEGORY.get(category, []))
    p = profile or {}
    age = p.get("age")
    if category in ("Moderate", "High", "Extreme"):
        if p.get("is_outdoor_worker"):
            recs.append("You work outdoors: schedule heavy work for early morning, take shaded breaks, and keep water with you.")
        if age is not None and (age >= 60 or age <= 5):
            recs.append("Because of your age group, avoid heat exposure at midday and ask someone to check on you during hot spells.")
        if p.get("activity_level") == "high":
            recs.append("Reduce exercise intensity or move it indoors / to early morning.")
    return recs


def full_guidance() -> dict[str, Any]:
    return {"disclaimer": DISCLAIMER, "by_category": BY_CATEGORY, "vulnerable_groups": VULNERABLE,
            "outdoor_work": OUTDOOR_WORK, "heat_illness": HEAT_ILLNESS, "hydration_and_cooling": HYDRATION_COOLING}
