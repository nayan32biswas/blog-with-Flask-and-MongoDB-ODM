from .conftest import get_header, get_test_file_path


def test_file_upload(client):
    image_path = f"{get_test_file_path()}/atom.jpg"

    with open(image_path, "rb") as f:
        response = client.post(
            "/api/v1/upload-image",
            data={"image": f},
            headers=get_header(client),
            content_type="multipart/form-data",
        )
    assert response.status_code == 201
    assert response.json.get("image_path") is not None


# def test_file_upload(client):
#     response = client.post(
#         "/api/v1/upload-image",
#         data={"image": (io.BytesIO(b"some initial text data"), "atom.jpg")},
#         headers=get_header(client),
#         content_type="multipart/form-data",
#     )
#     assert response.status_code == 201
#     assert response.json.get("image_path") is not None
