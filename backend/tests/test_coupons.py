from datetime import datetime, timezone, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.coupon import Coupon


def test_public_coupon_validate_percentage_and_fixed(client: TestClient, db_session: Session):
    # Setup test coupons
    c1 = Coupon(
        code="PROMO10",
        description="10% off",
        discount_type="percentage",
        discount_value=Decimal("10.00"),
        min_subtotal=Decimal("50.00"),
        max_discount_amount=Decimal("20.00"),
        is_active=True,
    )
    c2 = Coupon(
        code="VALE15",
        description="R$ 15 off",
        discount_type="fixed",
        discount_value=Decimal("15.00"),
        min_subtotal=Decimal("40.00"),
        is_active=True,
    )
    db_session.add_all([c1, c2])
    db_session.commit()

    # Validate PROMO10 with subtotal 100 -> 10.00 discount
    r1 = client.post("/api/v1/coupons/validate", json={"code": "promo10", "subtotal": 100.00})
    assert r1.status_code == 200
    data1 = r1.json()
    assert data1["valid"] is True
    assert float(data1["discount_amount"]) == 10.00
    assert data1["code"] == "PROMO10"

    # Validate min_subtotal rejection
    r2 = client.post("/api/v1/coupons/validate", json={"code": "PROMO10", "subtotal": 30.00})
    assert r2.status_code == 200
    assert r2.json()["valid"] is False
    assert "mínimo" in r2.json()["message"].lower()

    # Validate VALE15
    r3 = client.post("/api/v1/coupons/validate", json={"code": "vale15", "subtotal": 50.00})
    assert r3.status_code == 200
    assert r3.json()["valid"] is True
    assert float(r3.json()["discount_amount"]) == 15.00


def test_public_coupon_validate_expired_and_inactive(client: TestClient, db_session: Session):
    past_date = datetime.now(timezone.utc) - timedelta(days=2)
    c_expired = Coupon(
        code="EXPIRADO",
        description="Expirado",
        discount_type="fixed",
        discount_value=Decimal("10.00"),
        is_active=True,
        valid_until=past_date,
    )
    c_inactive = Coupon(
        code="INATIVO",
        description="Inativo",
        discount_type="fixed",
        discount_value=Decimal("10.00"),
        is_active=False,
    )
    db_session.add_all([c_expired, c_inactive])
    db_session.commit()

    r_exp = client.post("/api/v1/coupons/validate", json={"code": "EXPIRADO", "subtotal": 50.00})
    assert r_exp.status_code == 200
    assert r_exp.json()["valid"] is False
    assert "expirou" in r_exp.json()["message"].lower()

    r_ina = client.post("/api/v1/coupons/validate", json={"code": "INATIVO", "subtotal": 50.00})
    assert r_ina.status_code == 200
    assert r_ina.json()["valid"] is False
    assert "inválido" in r_ina.json()["message"].lower() or "inativo" in r_ina.json()["message"].lower()


def test_admin_coupon_crud_and_auth(client: TestClient, admin_token_headers: dict):
    # Unauthorized check
    r_unauth = client.get("/api/v1/coupons/admin-list")
    assert r_unauth.status_code in (401, 403)

    # Admin Create
    payload = {
        "code": "DINOS20",
        "description": "Cupom 20% Dinos",
        "discount_type": "percentage",
        "discount_value": 20.00,
        "min_subtotal": 50.00,
        "max_discount_amount": 30.00,
        "max_uses": 50,
        "is_active": True,
    }
    r_create = client.post("/api/v1/coupons", json=payload, headers=admin_token_headers)
    assert r_create.status_code == 201
    created = r_create.json()
    coupon_id = created["id"]
    assert created["code"] == "DINOS20"

    # Admin List
    r_list = client.get("/api/v1/coupons/admin-list", headers=admin_token_headers)
    assert r_list.status_code == 200
    assert any(c["id"] == coupon_id for c in r_list.json())

    # Admin Update
    r_update = client.put(
        f"/api/v1/coupons/{coupon_id}",
        json={"description": "Atualizado 25%", "discount_value": 25.00},
        headers=admin_token_headers,
    )
    assert r_update.status_code == 200
    assert r_update.json()["description"] == "Atualizado 25%"
    assert float(r_update.json()["discount_value"]) == 25.00

    # Admin Toggle Active
    r_toggle = client.patch(f"/api/v1/coupons/{coupon_id}/toggle-active", headers=admin_token_headers)
    assert r_toggle.status_code == 200
    assert r_toggle.json()["is_active"] is False

    # Admin Delete
    r_del = client.delete(f"/api/v1/coupons/{coupon_id}", headers=admin_token_headers)
    assert r_del.status_code == 204
