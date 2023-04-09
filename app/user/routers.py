from datetime import datetime
import logging

from flask import Blueprint, g
from werkzeug.security import generate_password_hash

from app.base.utils import parse_json, update_partially
from app.base.utils.query import get_object_or_404
from app.base.utils.response import custom_response, http_exception
from app.user.auth import Auth
from app.user.schemas import Registration, TokenIn, UpdateAccessTokenIn, UserIn, UserOut

from .models import User

user_api = Blueprint("user_api", __name__, url_prefix="/api/v1")
logger = logging.getLogger(__name__)


@user_api.post("/registration")
def create():
    res_data = parse_json(Registration)

    if User.exists({"username": res_data.username}):
        raise http_exception(detail="Username already exists.", status=400)

    try:
        hash_password = generate_password_hash(res_data.password)
        user = User(
            username=res_data.username,
            full_name=res_data.full_name,
            joining_date=datetime.utcnow(),
            password=hash_password,
            random_str=User.new_random_str(),
        ).create()
    except Exception as ex:
        logger.warning(f"Raise error while creating user error:{ex}")
        return custom_response({"details": "Something wrong try again."}, 400)

    return custom_response(UserOut.from_orm(user).dict(), 200)


@user_api.post("/token")
def login():
    data = parse_json(TokenIn)

    user = get_object_or_404(User, {"username": data.username})
    if not user.password or not Auth.verify_password(data.password, user.password):
        raise http_exception(detail="Invalid credentials", status=401)

    access_token = Auth.create_access_token(user)
    refresh_token = Auth.create_refresh_token(user)

    user.update({"$set": {"last_login": datetime.utcnow()}})

    return custom_response(
        {"access_token": access_token, "refresh_token": refresh_token}, 200
    )


@user_api.post("/update-access-token")
def update_access_token():
    data = parse_json(UpdateAccessTokenIn)

    access_token = Auth.create_access_token_from_refresh_token(data.refresh_token)
    return custom_response({"access_token": access_token})


@user_api.put("/logout-from-all-device")
@Auth.auth_required
def logout_from_all_device():
    user = g.user
    user.random_str = User.new_random_str()
    user.update()
    return {"message": "Logged out."}


@user_api.get("/me")
@Auth.auth_required
def ger_me():
    return custom_response(UserOut.from_orm(g.user).dict(), 200)


@user_api.patch("/update-user")
@Auth.auth_required
def update_user():
    user_data = parse_json(UserIn)

    user = g.user
    user = update_partially(user, user_data)
    user.update()
    return custom_response(UserOut.from_orm(user).dict(), 200)
