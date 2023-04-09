import logging

from flask import Blueprint

from app.base.utils.response import custom_response

base_api = Blueprint("base", __name__, url_prefix="/")
logger = logging.getLogger(__name__)


@base_api.get("/")
def index():
    return custom_response({"message": "Welcome to the blog post api!"}, 200)
