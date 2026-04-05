from collections.abc import Callable
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext
from passlib.exc import UnknownHashError
from jwt import ExpiredSignatureError, InvalidTokenError

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .models import User


security = HTTPBearer(auto_error=False)
settings = get_settings()
password_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return password_context.hash(password)


def verify_password(plain_password: str, stored_password: str) -> bool:
    try:
        return password_context.verify(plain_password, stored_password)
    except UnknownHashError:
        return False
    except ValueError:
        return False


def _build_token(*, user: User, secret: str, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.username,
        "role": user.role,
        "type": token_type,
        "iss": settings.jwt_issuer,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, secret, algorithm=settings.jwt_algorithm)


def build_access_token(user: User) -> str:
    return _build_token(
        user=user,
        secret=settings.jwt_access_secret_key,
        token_type="access",
        expires_delta=timedelta(minutes=settings.jwt_access_token_ttl_minutes),
    )


def build_refresh_token(user: User) -> str:
    return _build_token(
        user=user,
        secret=settings.jwt_refresh_secret_key,
        token_type="refresh",
        expires_delta=timedelta(days=settings.jwt_refresh_token_ttl_days),
    )


def decode_token(token: str, *, expected_type: str, secret: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
        )
    except ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired") from exc
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    if payload.get("type") != expected_type:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    return payload


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    payload = decode_token(
        credentials.credentials,
        expected_type="access",
        secret=settings.jwt_access_secret_key,
    )
    username = payload.get("sub")
    role = payload.get("role")
    if not username or not role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    user = db.scalar(select(User).where(User.username == username, User.role == role))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown user token")
    return user


def require_role(*roles: str) -> Callable:
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return dependency
