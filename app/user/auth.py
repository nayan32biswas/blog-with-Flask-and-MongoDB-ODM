from enum import Enum
from typing import Any, Dict
from bson import ObjectId
import jwt
from datetime import datetime, timedelta
from flask import request, g
from functools import wraps
from pydantic import BaseModel
from werkzeug.security import generate_password_hash, check_password_hash

from app.base.utils.response import http_exception
from app.base import config
from .models import User


class TokenType(str, Enum):
    ACCESS = "ACCESS"
    REFRESH = "REFRESH"


class TokenData(BaseModel):
    id: str
    random_str: str
    token_type: TokenType


credentials_exception = http_exception(
    detail="Could not validate credentials", status=401
)


class Auth:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return check_password_hash(hashed_password, plain_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        return generate_password_hash(password)

    @staticmethod
    def create_token(data: Dict[str, Any], exp: datetime) -> str:
        data["iat"] = datetime.utcnow()
        data["exp"] = exp
        return jwt.encode(data, config.SECRET_KEY, algorithm=config.ALGORITHM)

    @staticmethod
    def create_access_token(user: User) -> str:
        token_data = {
            "id": str(user.id),
            "random_str": user.random_str,
            "token_type": TokenType.ACCESS,
        }
        expire = datetime.utcnow() + timedelta(
            minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        return Auth.create_token(token_data, exp=expire)

    @staticmethod
    def create_refresh_token(user: User) -> str:
        token_data = {
            "id": str(user.id),
            "random_str": user.random_str,
            "token_type": TokenType.REFRESH,
        }
        expire = datetime.utcnow() + timedelta(days=config.REFRESH_TOKEN_EXPIRE_DAYS)
        return Auth.create_token(token_data, exp=expire)

    @staticmethod
    def decode_token(token) -> TokenData:
        try:
            payload: Any = jwt.decode(
                token, config.SECRET_KEY, algorithms=[config.ALGORITHM]
            )
        except jwt.ExpiredSignatureError:
            raise credentials_exception
        except jwt.InvalidTokenError:
            raise credentials_exception
        id: str = payload.get("id")
        random_str: str = payload.get("random_str")
        token_type = payload.get("token_type")
        if id is None or random_str is None or token_type is None:
            raise credentials_exception
        return TokenData(id=id, random_str=random_str, token_type=token_type)

    @staticmethod
    def extract_token(headers) -> str:
        if not headers:
            raise http_exception(detail="Invalid headers", status=401)
        authorization_str = headers.get("Authorization")
        if not authorization_str:
            raise credentials_exception
        prefix, token = authorization_str.split(" ")
        if prefix != "Bearer" or not token:
            raise credentials_exception
        return token

    @staticmethod
    def create_access_token_from_refresh_token(refresh_token) -> str:
        token_data = Auth.decode_token(refresh_token)
        if token_data.token_type != TokenType.REFRESH.value:
            raise http_exception(detail="Invalid token", status=403)

        user = User.find_one(
            {"_id": ObjectId(token_data.id), "random_str": token_data.random_str}
        )
        if not user:
            raise credentials_exception

        return Auth.create_access_token(user)

    @staticmethod
    def auth_required(func):
        @wraps(func)
        def decorated_auth(*args, **kwargs):
            token = Auth.extract_token(request.headers)
            token_data = Auth.decode_token(token)
            if token_data.token_type != TokenType.ACCESS.value:
                raise credentials_exception
            user = User.find_one(
                {
                    "_id": ObjectId(token_data.id),
                    "random_str": token_data.random_str,
                }
            )
            if not user:
                raise credentials_exception

            g.user = user
            return func(*args, **kwargs)

        return decorated_auth

    @staticmethod
    def auth_optional(func):
        @wraps(func)
        def decorated_auth(*args, **kwargs):
            try:
                token = Auth.extract_token(request.headers)
            except Exception:
                return func(*args, **kwargs)

            token_data = Auth.decode_token(token)
            if token_data.token_type != TokenType.ACCESS.value:
                raise credentials_exception
            user = User.find_one(
                {
                    "_id": ObjectId(token_data.id),
                    "random_str": token_data.random_str,
                }
            )
            if not user:
                raise credentials_exception

            g.user = user
            return func(*args, **kwargs)

        return decorated_auth