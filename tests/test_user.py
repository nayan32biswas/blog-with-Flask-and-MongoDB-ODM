from datetime import datetime, timedelta
from app.user.auth import Auth
from app.user.models import User
from tests.conftest import get_header, get_user

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
        "/api/v1/update-me",
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


def test_token_validation(client) -> None:
    # Try to get me without token
    response = client.get("/api/v1/me")
    assert response.status_code == 401

    exp = datetime.utcnow() + timedelta(hours=1)
    invalid_access_token = Auth.create_token({}, exp=exp)
    invalid_refresh_token = Auth.create_token({}, exp=exp)
    response = client.get(
        "/api/v1/me", headers={"Authorization": f"Bearer {invalid_access_token}"}
    )
    assert response.status_code == 401
    response = client.get(
        "/api/v1/me", headers={"Authorization": f"Bearer {invalid_refresh_token}"}
    )
    assert response.status_code == 401


def test_change_password(client) -> None:
    _ = User.delete_many({"username": NEW_USERNAME})
    payload = {"current_password": "str", "new_password": "str"}

    response = client.post(
        "/api/v1/registration",
        json={
            "username": NEW_USERNAME,
            "password": NEW_PASS,
            "full_name": NEW_FULL_NAME,
        },
    )

    response = client.post(
        "/api/v1/token",
        json={"username": NEW_USERNAME, "password": NEW_PASS},
    )
    assert response.status_code == 200

    access_token = response.json.get("access_token")
    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    updated_pass = "updated-pass"

    payload = {"current_password": NEW_PASS, "new_password": updated_pass}
    response = client.post("/api/v1/change-password", json=payload, headers=headers)

    assert response.status_code == 200

    response = client.post(
        "/api/v1/token",
        json={"username": NEW_USERNAME, "password": NEW_PASS},
    )
    assert response.status_code == 401, "User should get error with new password"

    _ = User.delete_many({"username": NEW_USERNAME})


def test_user_public_profile(client) -> None:
    user = get_user()
    response = client.get(f"/api/v1/users/{user.username}")

    assert response.status_code == 200
    assert response.json.get("username") == user.username, "'username' does not match"
