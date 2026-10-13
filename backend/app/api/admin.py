from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_executor, require_admin, settings_dep
from app.db.session import get_session
from app.ml.registry import model_status
from app.models import Alert, AuditLog, City, Prediction, SafetyResource, User
from app.schemas.admin import AlertIn, SafetyResourceIn, UserUpdate
from app.services import analytics, historical

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def _audit(session: Session, actor: User, action: str, target: str | None = None):
    session.add(AuditLog(actor_user_id=actor.user_id, action=action, target=target))


@router.get("/overview")
def overview(session: Session = Depends(get_session), db=Depends(get_executor), settings=Depends(settings_dep)):
    count = lambda q: session.scalar(q) or 0  # noqa: E731
    since = (date.today() - timedelta(days=29)).isoformat()
    by_category = session.execute(select(Prediction.risk_category, func.count()).group_by(Prediction.risk_category)).all()
    by_city = session.execute(select(City.name, func.count()).select_from(Prediction).join(City, City.city_id == Prediction.city_id)
                              .group_by(City.name).order_by(func.count().desc())).all()
    per_day = session.execute(select(func.date(Prediction.created_at), func.count())
                              .where(func.date(Prediction.created_at) >= since).group_by(func.date(Prediction.created_at))
                              .order_by(func.date(Prediction.created_at))).all()
    try:
        coverage = historical.date_coverage(db)
        imports = db.rows("SELECT * FROM import_log ORDER BY import_id DESC LIMIT 5")
    except Exception:
        coverage, imports = None, []
    return {
        "users": {"total": count(select(func.count()).select_from(User)),
                  "admins": count(select(func.count()).select_from(User).where(User.role == "admin")),
                  "inactive": count(select(func.count()).select_from(User).where(User.is_active.is_(False)))},
        "predictions": {"total": count(select(func.count()).select_from(Prediction)),
                        "demo": count(select(func.count()).select_from(Prediction).where(Prediction.is_demo.is_(True))),
                        "by_category": [{"category": c or "Unknown", "count": n} for c, n in by_category],
                        "by_city": [{"city": c, "count": n} for c, n in by_city],
                        "per_day_last_30": [{"date": str(d), "count": n} for d, n in per_day]},
        "alerts_active": count(select(func.count()).select_from(Alert).where(Alert.is_active.is_(True))),
        "dataset": coverage, "import_history": imports, "model": model_status(settings.model_path),
        "services": {"live_weather_enabled": settings.live_weather_enabled, "hospital_lookup_enabled": settings.hospitals_enabled},
    }


@router.get("/import-status")
def import_status(db=Depends(get_executor)):
    return {"coverage": historical.date_coverage(db), "imports": db.rows("SELECT * FROM import_log ORDER BY import_id DESC"),
            "note": "Historical weather records are read-only in the application. Re-import with scripts/import_excel.py."}


@router.get("/data-quality")
def data_quality(db=Depends(get_executor)):
    return analytics.data_quality(db)


@router.get("/users")
def list_users(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), q: Optional[str] = None,
               session: Session = Depends(get_session)):
    base = select(User)
    if q:
        base = base.where(User.email.contains(q.strip().lower()))
    total = session.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = session.scalars(base.order_by(User.created_at.desc()).limit(page_size).offset((page - 1) * page_size)).all()
    return {"page": page, "page_size": page_size, "total": total,
            "items": [{"user_id": u.user_id, "email": u.email, "role": u.role, "is_active": u.is_active,
                       "created_at": u.created_at, "last_login_at": u.last_login_at,
                       "full_name": u.profile.full_name if u.profile else None} for u in rows]}


@router.patch("/users/{user_id}")
def update_user(user_id: int, body: UserUpdate, admin: User = Depends(require_admin), session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found.")
    if user.user_id == admin.user_id and (body.is_active is False or body.role == "user"):
        raise HTTPException(400, "You cannot deactivate or demote your own account.")
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.role is not None:
        user.role = body.role
    _audit(session, admin, "user.update", f"user:{user_id} {body.model_dump(exclude_none=True)}")
    session.commit()
    return {"user_id": user.user_id, "role": user.role, "is_active": user.is_active}


@router.get("/predictions")
def all_predictions(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), session: Session = Depends(get_session)):
    total = session.scalar(select(func.count()).select_from(Prediction)) or 0
    rows = session.execute(select(Prediction, City.name, User.email).select_from(Prediction).join(City, City.city_id == Prediction.city_id)
                           .join(User, User.user_id == Prediction.user_id).order_by(Prediction.created_at.desc())
                           .limit(page_size).offset((page - 1) * page_size)).all()
    return {"page": page, "page_size": page_size, "total": total,
            "items": [{"prediction_id": p.prediction_id, "created_at": p.created_at, "user": email, "city": city,
                       "target_date": p.target_date, "risk_score": p.risk_score, "risk_category": p.risk_category,
                       "is_demo": p.is_demo, "model_name": p.model_name} for p, city, email in rows]}


# ---- alerts ----------------------------------------------------------------
def _alert_out(a: Alert) -> dict:
    return {"alert_id": a.alert_id, "city_id": a.city_id, "level": a.level, "title": a.title, "message": a.message,
            "is_active": a.is_active, "starts_on": a.starts_on, "ends_on": a.ends_on, "created_at": a.created_at}


@router.get("/alerts")
def list_alerts(session: Session = Depends(get_session)):
    return {"items": [_alert_out(a) for a in session.scalars(select(Alert).order_by(Alert.created_at.desc()))]}


@router.post("/alerts", status_code=status.HTTP_201_CREATED)
def create_alert(body: AlertIn, admin: User = Depends(require_admin), session: Session = Depends(get_session), db=Depends(get_executor)):
    if body.city_id is not None:
        from app.services import cities as city_svc
        city_svc.get_city(db, body.city_id)
    a = Alert(**body.model_dump(), created_by=admin.user_id)
    session.add(a)
    _audit(session, admin, "alert.create", body.title)
    session.commit()
    session.refresh(a)
    return _alert_out(a)


@router.put("/alerts/{alert_id}")
def update_alert(alert_id: int, body: AlertIn, admin: User = Depends(require_admin), session: Session = Depends(get_session)):
    a = session.get(Alert, alert_id)
    if not a:
        raise HTTPException(404, "Alert not found.")
    for k, v in body.model_dump().items():
        setattr(a, k, v)
    _audit(session, admin, "alert.update", f"alert:{alert_id}")
    session.commit()
    return _alert_out(a)


@router.delete("/alerts/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert(alert_id: int, admin: User = Depends(require_admin), session: Session = Depends(get_session)):
    a = session.get(Alert, alert_id)
    if not a:
        raise HTTPException(404, "Alert not found.")
    session.delete(a)
    _audit(session, admin, "alert.delete", f"alert:{alert_id}")
    session.commit()


# ---- curated safety resources -------------------------------------------------
@router.get("/safety-resources")
def list_resources(session: Session = Depends(get_session)):
    return {"items": [{"resource_id": r.resource_id, "city_id": r.city_id, "name": r.name, "resource_type": r.resource_type,
                       "phone": r.phone, "address": r.address, "source_note": r.source_note}
                      for r in session.scalars(select(SafetyResource).order_by(SafetyResource.name))]}


@router.post("/safety-resources", status_code=status.HTTP_201_CREATED)
def create_resource(body: SafetyResourceIn, admin: User = Depends(require_admin), session: Session = Depends(get_session)):
    r = SafetyResource(**body.model_dump(), created_by=admin.user_id)
    session.add(r)
    _audit(session, admin, "resource.create", body.name)
    session.commit()
    session.refresh(r)
    return {"resource_id": r.resource_id}


@router.delete("/safety-resources/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resource(resource_id: int, admin: User = Depends(require_admin), session: Session = Depends(get_session)):
    r = session.get(SafetyResource, resource_id)
    if not r:
        raise HTTPException(404, "Resource not found.")
    session.delete(r)
    _audit(session, admin, "resource.delete", f"resource:{resource_id}")
    session.commit()


@router.get("/audit-log")
def audit_log(limit: int = Query(50, ge=1, le=200), session: Session = Depends(get_session)):
    rows = session.execute(select(AuditLog, User.email).select_from(AuditLog).outerjoin(User, User.user_id == AuditLog.actor_user_id)
                           .order_by(AuditLog.created_at.desc()).limit(limit)).all()
    return {"items": [{"audit_id": a.audit_id, "actor": email, "action": a.action, "target": a.target,
                       "created_at": a.created_at} for a, email in rows]}
