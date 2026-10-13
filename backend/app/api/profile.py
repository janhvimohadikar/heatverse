from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_executor
from app.db.session import get_session
from app.models import User, UserProfile
from app.schemas.profile import ProfileIn, ProfileOut
from app.services import cities as city_svc

router = APIRouter(prefix="/api/profile", tags=["profile"])


def _out(user: User) -> ProfileOut:
    p = user.profile
    return ProfileOut.model_validate({**{c: getattr(p, c) for c in ProfileIn.model_fields}, "email": user.email})


@router.get("", response_model=ProfileOut)
def get_profile(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    if user.profile is None:
        user.profile = UserProfile()
        session.commit()
    return _out(user)


@router.put("", response_model=ProfileOut)
def update_profile(body: ProfileIn, user: User = Depends(get_current_user), session: Session = Depends(get_session),
                   db=Depends(get_executor)):
    if body.home_city_id is not None:
        city_svc.get_city(db, body.home_city_id)  # 404 if it does not exist
    if user.profile is None:
        user.profile = UserProfile()
    for field in ProfileIn.model_fields:
        setattr(user.profile, field, getattr(body, field))
    session.commit()
    session.refresh(user)
    return _out(user)
