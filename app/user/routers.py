import logging
from datetime import datetime
from typing import Any

from flask import Blueprint, Response, g

from app.base.utils import parse_json, update_partially
from app.base.utils.query import get_object_or_404
from app.base.utils.response import ExType, custom_response, http_exception
from app.user.auth import Auth
from app.user.schemas import (
    ChangePasswordIn,
    PublicUserProfile,
    Registration,
    TokenIn,
    UpdateAccessTokenIn,
    UserIn,
    UserOut,
)

from .models import User

user_api = Blueprint("user_api", __name__, url_prefix="/api/v1")
logger = logging.getLogger(__name__)


@user_api.post("/registration")
def create() -> Response:
    res_data = parse_json(Registration)

    if User.exists({"username": res_data.username}):
        raise http_exception(
            status=400,
            code=ExType.USERNAME_EXISTS,
            detail="Username already exists.",
        )

    try:
        hash_password = Auth.get_password_hash(res_data.password)
        user = User(
            username=res_data.username,
            full_name=res_data.full_name,
            joining_date=datetime.utcnow(),
            password=hash_password,
            random_str=User.new_random_str(),
        ).create()
    except Exception as ex:
        logger.warning(f"Raise error while creating user error:{ex}")
        raise http_exception(
            status=400,
            code=ExType.AUTHENTICATION_ERROR,
            detail="Something wrong try again",
        ) from ex

    return custom_response(UserOut.from_orm(user).dict(), 201)


def token_response(username: str, password: str) -> Any:
    user = Auth.authenticate_user(username, password)
    if not user or user.is_active is False:
        raise http_exception(
            status=401,
            code=ExType.AUTHENTICATION_ERROR,
            detail="Incorrect username or password",
        )
    access_token = Auth.create_access_token(user)
    refresh_token = Auth.create_refresh_token(user)
    user.update(raw={"$set": {"last_login": datetime.utcnow()}})
    return {
        "token_type": "Bearer",
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


@user_api.post("/token")
def login() -> Response:
    data = parse_json(TokenIn)

    response_data = token_response(data.username, data.password)
    return custom_response(response_data, 200)


@user_api.post("/update-access-token")
def update_access_token() -> Response:
    data = parse_json(UpdateAccessTokenIn)

    access_token = Auth.create_access_token_from_refresh_token(data.refresh_token)
    return custom_response({"access_token": access_token})


@user_api.post("/change-password")
@Auth.auth_required
def change_password() -> Any:
    data = parse_json(ChangePasswordIn)

    user = g.user
    if not user.password or not Auth.verify_password(
        data.current_password, user.password
    ):
        raise http_exception(
            status=400,
            code=ExType.AUTHENTICATION_ERROR,
            field="current_password",
            detail="Password did not match",
        )

    hash_password = Auth.get_password_hash(data.new_password)

    user.update(raw={"$set": {"password": hash_password}})
    return custom_response({"message": "Password changed successfully."})


@user_api.get("/me")
@Auth.auth_required
def ger_me() -> Response:
    return custom_response(UserOut.from_orm(g.user).dict(), 200)


@user_api.patch("/update-me")
@Auth.auth_required
def update_user() -> Response:
    user_data = parse_json(UserIn)

    user = g.user
    user = update_partially(user, user_data)
    user.update()
    return custom_response(UserOut.from_orm(user).dict(), 200)


@user_api.put("/logout-from-all-device")
@Auth.auth_required
def logout_from_all_device() -> Response:
    user = g.user
    user.random_str = User.new_random_str()
    user.update()
    return custom_response({"message": "Logged out."}, 200)


@user_api.get("/users/<string:username>")
def ger_user_public_profile(username: str) -> Any:
    public_user = get_object_or_404(User, filter={"username": username})
    return custom_response(PublicUserProfile.from_orm(public_user).dict())
