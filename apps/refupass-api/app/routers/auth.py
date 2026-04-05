from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import User
from ..schemas import LoginRequest, LoginResponse, RefreshTokenRequest
from ..security import build_access_token, build_refresh_token, decode_token
from ..config import get_settings


settings = get_settings()


router = APIRouter()


def _build_login_response(user: User) -> LoginResponse:
    return LoginResponse(
        access_token=build_access_token(user),
        refresh_token=build_refresh_token(user),
        role=user.role,
        display_name=user.display_name,
        ngo_name=user.ngo.name if user.ngo else None,
    )


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.scalar(select(User).options(joinedload(User.ngo)).where(User.username == payload.username))
    if not user or user.password != payload.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return _build_login_response(user)


@router.post("/auth/refresh", response_model=LoginResponse)
def refresh_session(payload: RefreshTokenRequest, db: Session = Depends(get_db)) -> LoginResponse:
    token_payload = decode_token(
        payload.refresh_token,
        expected_type="refresh",
        secret=settings.jwt_refresh_secret_key,
    )
    username = token_payload.get("sub")
    role = token_payload.get("role")
    if not username or not role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    user = db.scalar(select(User).options(joinedload(User.ngo)).where(User.username == username, User.role == role))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown user token")
    return _build_login_response(user)
