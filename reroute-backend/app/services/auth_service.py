from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Optional
import uuid

from passlib.context import CryptContext
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import User
from app.utils.jwt import create_access_token, create_refresh_token, decode_token

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    #  User persistence helpers
    # ------------------------------------------------------------------
    async def get_user_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create_user(
        self,
        email: str,
        password: str,
        display_name: str,
        home_currency: str = "INR",
        units: str = "metric",
    ) -> User:
        """Persist a new user, but never store the raw password."""
        hashed_pw = pwd_context.hash(password)
        now = datetime.now(tz=UTC)
        user_id = uuid.uuid4()

        stmt = (
            insert(User)
            .values(
                id=user_id,
                email=email,
                password_hash=hashed_pw,
                display_name=display_name,
                home_currency=home_currency,
                units=units,
                created_at=now,
                updated_at=now,
            )
            .returning(User)
        )

        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one()

    # ------------------------------------------------------------------
    #  JWT helpers – create a fresh pair
    # ------------------------------------------------------------------
    async def get_tokens(self, user: User) -> dict:
        now = datetime.now(tz=UTC)
        access_payload = {
            "sub": str(user.id),
            "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            "iat": int(now.timestamp()),
            "jti": str(uuid.uuid4()),
        }
        refresh_payload = {
            "sub": str(user.id),
            "exp": now + timedelta(days=7),
            "iat": int(now.timestamp()),
            "jti": str(uuid.uuid4()),
        }

        access_token = create_access_token(access_payload)
        refresh_token = create_refresh_token(refresh_payload)

        return {"access_token": access_token, "refresh_token": refresh_token}

    # ------------------------------------------------------------------
    #  Verify credentials
    # ------------------------------------------------------------------
    async def validate_user(self, email: str, password: str) -> Optional[User]:
        user = await self.get_user_by_email(email)
        if user and pwd_context.verify(password, user.password_hash):
            return user
        return None

    # ------------------------------------------------------------------
    #  Refresh flow – returns new pair
    # ------------------------------------------------------------------
    async def refresh_tokens(self, refresh_token: str) -> Optional[dict]:
        payload = decode_token(refresh_token, settings.SECRET_KEY)
        if payload is None:
            return None
        user_id = payload.get("sub")
        if user_id is None:
            return None
        user = await self.db.get(User, user_id)
        if user is None:
            return None
        return await self.get_tokens(user)

    # ------------------------------------------------------------------
    #  Decodes any valid token using the system key
    # ------------------------------------------------------------------
    def decode_token(self, token: str) -> Optional[dict]:
        return decode_token(token, settings.SECRET_KEY)
