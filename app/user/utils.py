import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional

import jwt
from bson import ObjectId
from passlib.context import CryptContext

from app.base.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    REFRESH_TOKEN_EXPIRE_DAYS,
    SECRET_KEY,
)
from app.base.utils.response import ExType, http_exception
from app.user.models import User

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenType(str, Enum):
    ACCESS = "ACCESS"
    REFRESH = "REFRESH"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def authenticate_user(username: str, password: str) -> Optional[User]:
    user = User.find_one({"username": username})
    if not user:
        return None
    if not user.password:
        return None
    if not verify_password(password, user.password):
        return None
    return user


def create_access_token(data: Dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "token_type": TokenType.ACCESS})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "token_type": TokenType.REFRESH})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


invalid_refresh_token = http_exception(
    status=403,
    code=ExType.PERMISSION_ERROR,
    detail="Invalid Refresh Token",
)


def create_access_token_from_refresh_token(refresh_token: str) -> str:
    if not refresh_token:
        raise invalid_refresh_token
    try:
        payload: Any = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        raise invalid_refresh_token
    token_type = payload.get("token_type")
    if token_type is None or token_type != TokenType.REFRESH:
        raise invalid_refresh_token

    user = User.find_one(
        {"_id": ObjectId(payload["id"]), "random_str": payload["random_str"]}
    )
    if not user:
        raise invalid_refresh_token

    access_token = create_access_token(
        data={
            "id": str(payload.get("id")),
            "random_str": str(payload.get("random_str")),
        }
    )
    return access_token


def provide_token(user_id: ObjectId) -> str:
    return create_access_token({"id": str(user_id)})
