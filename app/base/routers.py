import logging

from flask import Blueprint, Response, request

from app.base.utils.file import save_file
from app.base.utils.response import custom_response, http_exception
from app.user.auth import Auth

base_api = Blueprint("base", __name__, url_prefix="")
logger = logging.getLogger(__name__)


@base_api.get("/")
def index() -> Response:
    return custom_response({"message": "Welcome to the blog post api!"}, 200)


@base_api.post("/api/v1/upload-image")
@Auth.auth_required
def create_upload_image() -> Response:
    if "image" not in request.files:
        raise http_exception(detail="Invalid image", status=400)
    file = request.files["image"]
    image_path = save_file(file, root_folder="image")
    return custom_response({"image_path": image_path}, 201)
