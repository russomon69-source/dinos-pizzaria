import io
import time
from decimal import Decimal
import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.category import Category
from app.models.delivery import DeliveryZone
from app.models.product import Product


@pytest.fixture
def security_catalog(db_session: Session):
    """Seed minimal catalog for security and threat modeling tests."""
    cat = Category(name="Pizzas", slug="pizzas", order=1, is_active=True)
    db_session.add(cat)
    db_session.flush()

    prod = Product(
        title="Pizza T-Rex Suprema",
        description="Pepperoni vulcânico e mussarela",
        price=Decimal("60.00"),
        is_promo=False,
        is_active=True,
        category_id=cat.id,
    )
    zone = DeliveryZone(name="Centro", fee=Decimal("10.00"), estimated_minutes=30, is_active=True)
    db_session.add_all([prod, zone])
    db_session.commit()

    return {"cat": cat, "prod": prod, "zone": zone}


def test_security_price_tampering_ignored(client: TestClient, security_catalog: dict):
    """
    Threat T-06-01: Verify that client-submitted prices and subtotals are completely ignored.
    Backend recalculates authoritative prices from DB (2 * 60.00 = 120.00 + 10.00 fee = 130.00).
    """
    prod = security_catalog["prod"]
    zone = security_catalog["zone"]

    tampered_payload = {
        "customer_name": "TamperTest",
        "customer_phone": "(11) 99999-9999",
        "customer_address": "Rua Teste, 1337",
        "delivery_type": "delivery",
        "delivery_zone_id": zone.id,
        "payment_method": "pix",
        "subtotal": 0.01,
        "delivery_fee": 0.01,
        "total_amount": 0.02,
        "items": [
            {
                "item_type": "product",
                "item_id": prod.id,
                "quantity": 2,
                "unit_price": 0.01,
                "total_price": 0.02,
            }
        ],
    }

    res = client.post("/api/v1/orders", json=tampered_payload)
    assert res.status_code == 201
    order = res.json()["order"]
    assert Decimal(str(order["subtotal"])) == Decimal("120.00")
    assert Decimal(str(order["delivery_fee"])) == Decimal("10.00")
    assert Decimal(str(order["total_amount"])) == Decimal("130.00")


def test_security_malicious_upload_rejection(client: TestClient, admin_token_headers: dict):
    """
    Threat T-06-02: Verify rejection of disallowed scripts, fake headers, and corrupted binaries.
    """
    # 1. Non-image script file
    fake_script_payload = b"console.log('invalid_upload');"
    res_script = client.post(
        "/api/v1/uploads/image",
        files={"file": ("test_script.js", fake_script_payload, "application/javascript")},
        headers=admin_token_headers,
    )
    assert res_script.status_code == 400

    # 2. Corrupted random byte payload without magic bytes
    corrupted_bytes = bytes([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
    res_corrupt = client.post(
        "/api/v1/uploads/image",
        files={"file": ("corrupted.png", corrupted_bytes, "image/png")},
        headers=admin_token_headers,
    )
    assert res_corrupt.status_code == 400

    # 3. Plain text file masquerading as jpeg
    text_payload = b"This is plain text and not a real image binary."
    res_text = client.post(
        "/api/v1/uploads/image",
        files={"file": ("fake_image.jpg", text_payload, "image/jpeg")},
        headers=admin_token_headers,
    )
    assert res_text.status_code == 400


def test_security_upload_path_traversal_prevention(client: TestClient, admin_token_headers: dict):
    """
    Threat T-06-03: Verify that filename directory traversal attempts are neutralized
    by generating randomized UUID4 filenames and saving strictly as .webp in static/uploads/.
    """
    from tests.test_uploads import create_test_image

    img_bytes = create_test_image(width=100, height=100, color=(10, 20, 30), img_format="PNG")
    traversal_filename = "../../../../test_traversal.png"

    res = client.post(
        "/api/v1/uploads/image",
        files={"file": (traversal_filename, img_bytes, "image/png")},
        headers=admin_token_headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert ".." not in data["filename"]
    assert data["filename"].endswith(".webp")
    assert data["url"].startswith("/static/uploads/")


def test_security_sql_injection_resistance(client: TestClient, security_catalog: dict):
    """
    Threat T-06-04: Verify parameterized query safety against SQL Injection attacks.
    """
    sqli_payloads = [
        "' OR '1'='1",
        "'; SELECT 1; --",
        "1 UNION SELECT 1, 'admin', 'test' --",
    ]

    for sqli in sqli_payloads:
        # 1. Product category filter SQLi
        res_prod = client.get(f"/api/v1/products?category_id={sqli}")
        # Should return 422 (validation error) or empty list 200, never 500 error
        assert res_prod.status_code in (200, 422)

        # 2. Orders filter SQLi
        res_orders = client.get(f"/api/v1/orders?status={sqli}")
        # Unauthorized without token (401), but parameter should not cause SQL crash
        assert res_orders.status_code in (401, 422)


def test_security_jwt_tampering_and_expiration(client: TestClient):
    """
    Threat T-06-06: Verify rejection of tampered and expired JWT tokens.
    """
    # 1. Token signed with wrong secret key
    fake_token = jwt.encode(
        {"sub": "admin", "exp": int(time.time()) + 3600},
        "invalid-secret-key-12345",
        algorithm=settings.JWT_ALGORITHM,
    )
    res_fake = client.get("/api/v1/orders", headers={"Authorization": f"Bearer {fake_token}"})
    assert res_fake.status_code == 401

    # 2. Expired token
    expired_token = jwt.encode(
        {"sub": "admin", "exp": int(time.time()) - 3600},
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    res_expired = client.get("/api/v1/orders", headers={"Authorization": f"Bearer {expired_token}"})
    assert res_expired.status_code == 401

    # 3. Malformed token string
    res_malformed = client.get("/api/v1/orders", headers={"Authorization": "Bearer invalid-token-string"})
    assert res_malformed.status_code == 401


def test_security_rate_limiting_login_endpoint(client: TestClient):
    """
    Threat T-06-07: Verify SlowAPI rate limiting on the login endpoint.
    After 5 consecutive requests within 1 minute, the API returns HTTP 429 Too Many Requests.
    """
    login_payload = {"username": "wrong_user", "password": "wrong_password"}

    statuses = []
    # Send 10 rapid login attempts
    for _ in range(10):
        resp = client.post("/api/v1/auth/login", json=login_payload)
        statuses.append(resp.status_code)

    # At least some requests after the 5th attempt must be 429
    assert 429 in statuses, f"Expected 429 in rate limit attempts, got {statuses}"
