from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    display_name: str
    home_currency: str = "INR"
    units: str = "metric"
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    id: Optional[UUID] = None
    email: Optional[EmailStr] = None
    display_name: Optional[str] = None
    home_currency: str = "INR"
    units: str = "metric"
    created_at: Optional[datetime] = None
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Optional[UserOut] = None

    model_config = ConfigDict(from_attributes=True)
