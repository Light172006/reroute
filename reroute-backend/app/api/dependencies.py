from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.auth_service import AuthService
from app.db.models import User
from app.db.session import get_db

security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    auth = AuthService(db)
    payload = auth.decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id_raw = payload.get("sub")
    if not user_id_raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    import uuid
    try:
        user_id = uuid.UUID(str(user_id_raw))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_optional_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional),
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Resolves current user if token is provided via Authorization header or query param.
    Does not raise 403/401 if unauthenticated (returns None).
    """
    raw_token = None
    if credentials:
        raw_token = credentials.credentials
    elif token:
        raw_token = token
    elif "authorization" in request.headers:
        auth_hdr = request.headers["authorization"]
        if auth_hdr.lower().startswith("bearer "):
            raw_token = auth_hdr[7:].strip()
        else:
            raw_token = auth_hdr.strip()

    if not raw_token:
        return None

    try:
        auth = AuthService(db)
        payload = auth.decode_token(raw_token)
        if payload is None:
            return None
        return await db.get(User, payload.get("sub"))
    except Exception:
        return None
