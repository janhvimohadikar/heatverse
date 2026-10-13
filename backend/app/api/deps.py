"""Shared FastAPI dependencies: DB session, SQL executor, current user, admin guard."""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import decode_access_token
from app.db.executor import SAExecutor
from app.db.session import get_session
from app.models import User

bearer = HTTPBearer(auto_error=False)


def settings_dep() -> Settings:
    return get_settings()


def get_executor(session: Session = Depends(get_session)) -> SAExecutor:
    return SAExecutor(session)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: Session = Depends(get_session),
    settings: Settings = Depends(settings_dep),
) -> User:
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated.", headers={"WWW-Authenticate": "Bearer"})
    if creds is None:
        raise unauthorized
    payload = decode_access_token(creds.credentials, settings.secret_key)
    if not payload:
        raise unauthorized
    user = session.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise unauthorized
    return user  # role is read from the database on every request, never trusted from the token


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Administrator access required.")
    return user
