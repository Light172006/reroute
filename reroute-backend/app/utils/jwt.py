import json
from datetime import datetime, timezone
from typing import Dict, Optional

import jwt
from pydantic_settings import BaseSettings

from app.core.config import settings

def create_token(payload: Dict) -> str:
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_access_token(payload: Dict) -> str:
    return create_token(payload)

def create_refresh_token(payload: Dict) -> str:
    return create_token(payload)

def decode_token(token: str, key: str) -> Optional[Dict]:
    try:
        return jwt.decode(token, key, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        return None
