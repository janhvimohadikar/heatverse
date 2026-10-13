from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, settings_dep
from app.core.config import Settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_session
from app.models import User, UserProfile
from app.schemas.auth import LoginRequest, SignupRequest, TokenOut, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])
_DUMMY_HASH = hash_password("not-a-real-password")  # keeps login timing similar for unknown emails


@router.post("/signup", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, session: Session = Depends(get_session), settings: Settings = Depends(settings_dep)):
    """Create a normal user account. Admin accounts can only be created with scripts/create_admin.py."""
    if session.scalar(select(User).where(User.email == body.email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")
    user = User(email=body.email, password_hash=hash_password(body.password), role="user")
    user.profile = UserProfile(full_name=body.full_name)
    session.add(user)
    session.commit()
    session.refresh(user)
    token = create_access_token(user.user_id, settings.secret_key, settings.access_token_minutes)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
def login(body: LoginRequest, session: Session = Depends(get_session), settings: Settings = Depends(settings_dep)):
    user = session.scalar(select(User).where(User.email == body.email))
    ok = verify_password(body.password, user.password_hash if user else _DUMMY_HASH)
    if not user or not ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been deactivated.")
    user.last_login_at = datetime.now(timezone.utc)
    session.commit()
    token = create_access_token(user.user_id, settings.secret_key, settings.access_token_minutes)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(_: User = Depends(get_current_user)):
    """Tokens are stateless; the client discards its token. (Documented limitation: no server-side revocation.)"""
    return None
