from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import User
from ..schemas import LoginRequest, LoginResponse
from ..security import build_access_token


router = APIRouter()


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.scalar(select(User).options(joinedload(User.ngo)).where(User.username == payload.username))
    if not user or user.password != payload.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return LoginResponse(
        access_token=build_access_token(user),
        role=user.role,
        display_name=user.display_name,
        ngo_name=user.ngo.name if user.ngo else None,
    )
