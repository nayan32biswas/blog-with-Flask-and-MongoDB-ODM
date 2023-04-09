import logging
import os
from functools import lru_cache
from typing import Any, Dict, Generator

import pytest
from mongodb_odm import disconnect

from app.base import config
from app.user.models import User

from app.app import create_app
from .data import populate_dummy_data, users

logger = logging.getLogger(__name__)


@pytest.fixture()
def app() -> Generator:
    app = create_app()
    app.config.update({"TESTING": True})

    if not User.exists({"username": users[0]["username"]}):
        populate_dummy_data()

    yield app
    # clean_data()

    disconnect()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()


@lru_cache(maxsize=None)
def get_user() -> User:
    return User.get({"username": users[0]["username"]})


@lru_cache(maxsize=None)
def get_token(client) -> str:
    response = client.post(
        "/api/v1/token",
        json={"username": users[0]["username"], "password": users[0]["password"]},
    )
    assert response.status_code == 200
    return str(response.json["access_token"])


@lru_cache(maxsize=None)
def get_header(client) -> Dict[str, Any]:
    token = get_token(client)
    return {
        "Authorization": f"Bearer {token}",
    }


def get_test_file_path() -> str:
    print(config.BASE_DIR)
    return os.path.join(config.BASE_DIR, "tests/files")
