import io
import os
from PIL import Image
from fastapi.testclient import TestClient


def create_test_image(
    width: int = 400,
    height: int = 300,
    color: tuple = (255, 0, 0),
    img_format: str = "PNG",
) -> bytes:
    """Helper to create an in-memory image for upload testing."""
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format=img_format)
    return buf.getvalue()


def test_upload_image_unauthorized(client: TestClient):
    """Attempting upload without admin token should return 401 Unauthorized."""
    image_bytes = create_test_image()
    response = client.post(
        "/api/v1/uploads/image",
        files={"file": ("test.png", image_bytes, "image/png")},
    )
    assert response.status_code == 401


def test_upload_valid_image_png(client: TestClient, admin_token_headers: dict):
    """Uploading a valid PNG should convert to WebP and return 201 with metadata."""
    image_bytes = create_test_image(width=500, height=400, color=(0, 255, 0), img_format="PNG")
    response = client.post(
        "/api/v1/uploads/image",
        files={"file": ("pizza.png", image_bytes, "image/png")},
        headers=admin_token_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["url"].startswith("/static/uploads/")
    assert data["filename"].endswith(".webp")
    assert data["width"] == 500
    assert data["height"] == 400
    assert data["size_bytes"] > 0

    # Verify physical file existence and cleanup
    file_path = os.path.join("static", "uploads", data["filename"])
    assert os.path.exists(file_path)

    # Verify it can be served via static route
    static_resp = client.get(data["url"])
    assert static_resp.status_code == 200
    assert len(static_resp.content) == data["size_bytes"]

    if os.path.exists(file_path):
        os.remove(file_path)


def test_upload_valid_image_jpeg(client: TestClient, admin_token_headers: dict):
    """Uploading a JPEG should succeed and convert to WebP."""
    image_bytes = create_test_image(width=600, height=450, color=(100, 150, 200), img_format="JPEG")
    response = client.post(
        "/api/v1/uploads/image",
        files={"file": ("combo.jpg", image_bytes, "image/jpeg")},
        headers=admin_token_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["filename"].endswith(".webp")
    assert data["width"] == 600
    assert data["height"] == 450

    file_path = os.path.join("static", "uploads", data["filename"])
    if os.path.exists(file_path):
        os.remove(file_path)


def test_upload_image_resize_downscaling(client: TestClient, admin_token_headers: dict):
    """Images wider than 1000px must be downscaled to width 1000 while maintaining aspect ratio."""
    # 2000 x 1000 (aspect ratio 2:1) -> downscaled to 1000 x 500
    image_bytes = create_test_image(width=2000, height=1000, color=(255, 128, 0), img_format="PNG")
    response = client.post(
        "/api/v1/uploads/image",
        files={"file": ("large_banner.png", image_bytes, "image/png")},
        headers=admin_token_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["width"] == 1000
    assert data["height"] == 500

    file_path = os.path.join("static", "uploads", data["filename"])
    if os.path.exists(file_path):
        os.remove(file_path)


def test_upload_empty_file(client: TestClient, admin_token_headers: dict):
    """Uploading an empty file should return 400 Bad Request."""
    response = client.post(
        "/api/v1/uploads/image",
        files={"file": ("empty.png", b"", "image/png")},
        headers=admin_token_headers,
    )
    assert response.status_code == 400
    assert "vazio" in response.json()["detail"].lower()


def test_upload_invalid_format_text_file(client: TestClient, admin_token_headers: dict):
    """Uploading non-image files (e.g. text/html/executable) should return 400."""
    fake_content = b"Not an image file content"
    response = client.post(
        "/api/v1/uploads/image",
        files={"file": ("malicious.sh", fake_content, "text/plain")},
        headers=admin_token_headers,
    )
    assert response.status_code == 400


def test_upload_corrupted_image(client: TestClient, admin_token_headers: dict):
    """Uploading corrupted image byte streams should return 400."""
    corrupted_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 20
    response = client.post(
        "/api/v1/uploads/image",
        files={"file": ("corrupted.png", corrupted_bytes, "image/png")},
        headers=admin_token_headers,
    )
    assert response.status_code == 400
