import logging
import os

from flask import Blueprint, Response, request, send_file
from mongodb_odm.connection import get_client

from app.base.config import MEDIA_ROOT
from app.base.utils.file import save_file
from app.base.utils.response import ExType, custom_response, http_exception
from app.user.auth import Auth

base_api = Blueprint("base", __name__, url_prefix="")
logger = logging.getLogger(__name__)


@base_api.get("/")
def index() -> Response:
    try:
        get_client().admin.command("ping")
    except Exception as e:
        logger.critical(f"Mongo Server not available. Error{e}")
        raise http_exception(
            status=400, code=ExType.INTERNAL_SERVER_ERROR, detail="Database Error"
        ) from e
    return custom_response({"message": "Welcome to the blog post api!"}, 200)


@base_api.post("/api/v1/upload-image")
@Auth.auth_required
def create_upload_image() -> Response:
    if "image" not in request.files:
        raise http_exception(
            status=400, code=ExType.VALIDATION_ERROR, detail="Invalid image"
        )
    file = request.files["image"]
    image_path = save_file(file, root_folder="image")
    return custom_response({"image_path": image_path}, 201)


@base_api.get("/media/<path:file_path>")
@Auth.auth_optional
def get_image(file_path: str) -> Response:
    file_path = f"{MEDIA_ROOT}/{file_path}"
    if os.path.isfile(file_path):
        return send_file(file_path)
        # return send_from_directory(MEDIA_ROOT, file_path)

    else:
        raise http_exception(
            status=400,
            code=ExType.OBJECT_NOT_FOUND,
            detail="file not found",
        )
