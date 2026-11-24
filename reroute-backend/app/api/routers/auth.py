from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.auth_service import AuthService
from app.db.models import User
from app.api.schemas.auth import UserOut, TokenOut, TokenRefresh, SignupRequest, LoginRequest, AuthResponse
from app.api.dependencies import get_current_user
from app.db.session import get_db

router = APIRouter()


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    request: Request,
    payload: Optional[SignupRequest] = None,
    email: Optional[str] = Query(None),
    password: Optional[str] = Query(None),
    display_name: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    target_email = payload.email if payload else email
    target_password = payload.password if payload else password
    target_display_name = payload.display_name if payload else display_name

    if not target_email or not target_password:
        try:
            body = await request.json()
            if isinstance(body, dict):
                target_email = target_email or body.get("email")
                target_password = target_password or body.get("password")
                target_display_name = target_display_name or body.get("display_name")
        except Exception:
            pass

    if not target_email or not target_password or not target_display_name:
        raise HTTPException(status_code=400, detail="Missing required signup fields: email, password, display_name")

    target_email = str(target_email).strip().lower()
    target_password = str(target_password)
    target_display_name = str(target_display_name).strip()

    if len(target_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    auth = AuthService(db)
    if await auth.get_user_by_email(target_email):
        raise HTTPException(status_code=400, detail="Email already registered")
    user = await auth.create_user(target_email, target_password, target_display_name)
    tokens = await auth.get_tokens(user)
    user_out = UserOut.model_validate(user)
    return AuthResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        home_currency=user.home_currency,
        units=user.units,
        created_at=user.created_at,
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type="bearer",
        user=user_out,
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: Request,
    payload: Optional[LoginRequest] = None,
    email: Optional[str] = Query(None),
    password: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    target_email = payload.email if payload else email
    target_password = payload.password if payload else password

    if not target_email or not target_password:
        try:
            body = await request.json()
            if isinstance(body, dict):
                target_email = target_email or body.get("email")
                target_password = target_password or body.get("password")
        except Exception:
            pass

    if not target_email or not target_password:
        raise HTTPException(status_code=400, detail="Missing email or password")

    target_email = str(target_email).strip().lower()
    target_password = str(target_password)

    auth = AuthService(db)
    user = await auth.validate_user(target_email, target_password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect credentials")
    tokens = await auth.get_tokens(user)
    user_out = UserOut.model_validate(user)
    return AuthResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        home_currency=user.home_currency,
        units=user.units,
        created_at=user.created_at,
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type="bearer",
        user=user_out,
    )


@router.post("/refresh", response_model=TokenOut)
async def refresh(
    token_in: TokenRefresh,
    db: AsyncSession = Depends(get_db),
) -> TokenOut:
    auth = AuthService(db)
    tokens = await auth.refresh_tokens(token_in.refresh_token)
    if not tokens:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return tokens


@router.get("/me", response_model=UserOut)
async def me(
    current_user: User = Depends(get_current_user),
) -> User:
    return current_user
