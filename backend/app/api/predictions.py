from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_executor, settings_dep
from app.db.session import get_session
from app.ml.registry import get_predictor, model_status
from app.models import City, Prediction, User
from app.schemas.prediction import PredictionRequest
from app.services import prediction_service

router = APIRouter(prefix="/api/predictions", tags=["predictions"])


def _profile_dict(user: User) -> dict:
    p = user.profile
    if p is None:
        return {}
    return {"age": p.age, "is_outdoor_worker": p.is_outdoor_worker, "activity_level": p.activity_level}


@router.get("/model-status")
def get_model_status(settings=Depends(settings_dep)):
    """Is a real trained model connected, or are predictions DEMO output?"""
    return model_status(settings.model_path)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_prediction(body: PredictionRequest, user: User = Depends(get_current_user), session: Session = Depends(get_session),
                      db=Depends(get_executor), settings=Depends(settings_dep)):
    predictor = get_predictor(settings.model_path)
    result = prediction_service.run_prediction(db, predictor, body.city_id, body.horizon_days, _profile_dict(user))
    row = Prediction(
        user_id=user.user_id, city_id=body.city_id, target_date=result["target_date"], horizon_days=body.horizon_days,
        model_name=result["model"]["name"], model_version=result["model"]["version"], is_demo=result["model"]["is_demo"],
        risk_score=result["risk"]["score"], risk_category=result["risk"]["category"],
        personal_score=result["personal"]["personal_score"], personal_category=result["personal"]["personal_category"],
        expected_temp_max_c=result["expected"].get("temp_max_c"), heatwave_probability=result["heatwave_probability"],
        confidence=result["confidence"], details=result)
    session.add(row)
    session.commit()
    session.refresh(row)
    return {"prediction_id": row.prediction_id, "created_at": row.created_at, **result}


@router.get("/history")
def history(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), user: User = Depends(get_current_user),
            session: Session = Depends(get_session)):
    total = session.scalar(select(func.count()).select_from(Prediction).where(Prediction.user_id == user.user_id)) or 0
    rows = session.execute(
        select(Prediction, City.name).select_from(Prediction).join(City, City.city_id == Prediction.city_id)
        .where(Prediction.user_id == user.user_id).order_by(Prediction.created_at.desc())
        .limit(page_size).offset((page - 1) * page_size)).all()
    items = [{"prediction_id": p.prediction_id, "created_at": p.created_at, "city": name, "city_id": p.city_id,
              "target_date": p.target_date, "horizon_days": p.horizon_days, "risk_score": p.risk_score,
              "risk_category": p.risk_category, "personal_score": p.personal_score, "personal_category": p.personal_category,
              "model_name": p.model_name, "model_version": p.model_version, "is_demo": p.is_demo,
              "expected_temp_max_c": p.expected_temp_max_c,
              "recommendation": ((p.details or {}).get("recommendations") or [None])[0]} for p, name in rows]
    return {"page": page, "page_size": page_size, "total": total, "items": items}


@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
def clear_history(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Deletes only the signed-in user's own prediction history."""
    session.execute(delete(Prediction).where(Prediction.user_id == user.user_id))
    session.commit()
