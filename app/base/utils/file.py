import logging
import os
from datetime import datetime
from typing import Optional, Tuple
from uuid import uuid4

from werkzeug.datastructures import FileStorage

from app.base.config import BASE_DIR, MEDIA_ROOT

from .string import base64, rand_slug_str

logger = logging.getLogger(__name__)


def get_name_and_extension(filename: Optional[str]) -> Tuple[str, str]:
    if filename is None:
        return "", ""
    name_list = filename.split(".")
    if len(name_list) >= 2:
        return ".".join(name_list[0:-1]), name_list[-1]
    return "", ""


def get_folder_path(root_folder: str) -> str:
    base64_month = base64(datetime.now().strftime("%Y%m"))
    # now = datetime.now().strftime("%Y%m%d%H%M%S%f")
    return f"{root_folder}/{base64_month}"


def get_unique_file_name(ext: str) -> str:
    return f"{uuid4().hex}{rand_slug_str(6)}.{ext}"


def save_file(uploaded_file: FileStorage, root_folder: str = "image") -> str:
    if not uploaded_file:
        return ""
    _, ext = get_name_and_extension(uploaded_file.filename)
    folder_location = f"{MEDIA_ROOT}/{get_folder_path(root_folder)}"

    if not os.path.exists(folder_location):
        os.makedirs(folder_location)

    file_location = f"{folder_location}/{get_unique_file_name(ext)}"
    try:
        with open(file_location, "wb+") as file_object:
            file_object.write(uploaded_file.read())
        file_path = file_location.split(f"{BASE_DIR}")[-1]
        return file_path
    except Exception:
        return ""
