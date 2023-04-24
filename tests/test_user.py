from app.user.models import User
from tests.conftest import get_header

from .data import users

NEW_USERNAME = "username-exists"
NEW_PASS = "new-pass"
NEW_FULL_NAME = "Full Name"


def test_registration_and_auth(client):
    _ = User.delete_many({"username": NEW_USERNAME})

    response = client.post(
        "/api/v1/registration",
        json={
            "username": NEW_USERNAME,
            "password": NEW_PASS,
            "full_name": NEW_FULL_NAME,
        },
    )
    assert response.status_code == 201

    response = client.post(
        "/api/v1/token", json={"username": NEW_USERNAME, "password": NEW_PASS}
    )
    assert response.status_code == 200
    assert response.json["access_token"]

    _ = User.delete_many({"username": NEW_USERNAME})


def test_duplicate_registration(client):
    _ = User.delete_many({"username": NEW_USERNAME})

    response = client.post(
        "/api/v1/registration",
        json={
            "username": NEW_USERNAME,
            "password": NEW_PASS,
            "full_name": NEW_FULL_NAME,
        },
    )
    assert response.status_code == 201

    response = client.post(
        "/api/v1/registration",
        json={
            "username": NEW_USERNAME,
            "password": NEW_PASS,
            "full_name": NEW_FULL_NAME,
        },
    )
    assert response.status_code == 400

    _ = User.delete_many({"username": NEW_USERNAME})


def test_update_access_token(client):
    response = client.post(
        "api/v1/token",
        json={"username": users[0]["username"], "password": users[0]["password"]},
    )
    assert response.status_code == 200

    response = client.post(
        "/api/v1/update-access-token",
        json={"refresh_token": response.json["refresh_token"]},
    )
    assert response.status_code == 200


def test_get_me(client):
    response = client.get("/api/v1/me", headers=get_header(client))
    assert response.status_code == 200
    assert response.json["username"] == users[0]["username"]


def test_update_user(client):
    new_full_name = "New Name"
    response = client.patch(
        "/api/v1/update-user",
        json={"full_name": new_full_name},
        headers=get_header(client),
    )

    assert response.status_code == 200
    assert response.json["full_name"] == new_full_name
    assert response.json["username"] == users[0]["username"]


def test_logout_from_all_device(client):
    response = client.post(
        "/api/v1/token",
        json={"username": users[0]["username"], "password": users[0]["password"]},
    )
    access_token = response.json["access_token"]
    refresh_token = response.json["refresh_token"]
    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    response = client.get("/api/v1/me", headers=headers)
    assert response.status_code == 200

    response = client.put("/api/v1/logout-from-all-device", headers=headers)
    assert response.status_code == 200

    response = client.get("/api/v1/me", headers=headers)
    assert response.status_code == 401

    response = client.post(
        "/api/v1/update-access-token", json={"refresh_token": refresh_token}
    )
    assert response.status_code == 403
