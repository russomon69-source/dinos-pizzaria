import os
import re
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.product import Product
from app.models.delivery import DeliveryZone


def test_checkout_module_served_and_exports(client: TestClient):
    """Test that /js/checkout.js is served with correct headers and exports checkout functions."""
    response = client.get("/js/checkout.js")
    assert response.status_code == 200, "Failed to load /js/checkout.js"
    assert "javascript" in response.headers.get("content-type", "")

    content = response.text
    required_exports = [
        "initCheckout",
        "openCheckoutModal",
        "closeCheckoutModal",
        "submitOrder",
    ]
    for exp in required_exports:
        assert exp in content, f"Export {exp} missing from checkout.js"


def test_checkout_logic_rules_embedded():
    """Verify business logic rules in checkout.js directly from file."""
    checkout_path = os.path.join("frontend", "public", "js", "checkout.js")
    assert os.path.exists(checkout_path), "frontend/public/js/checkout.js must exist"

    with open(checkout_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Rule: Delivery vs Pickup handling (Pitfall 3: Delivery fee set to 0 and address optional on pickup)
    assert "pickup" in content, "checkout.js must handle pickup delivery type"
    assert "delivery" in content, "checkout.js must handle delivery delivery type"

    # Rule: Double submit mitigation (Threat T-04-08)
    assert "disabled" in content, "checkout.js must disable submit button to prevent double submits"

    # Rule: Price tampering mitigation (Threat T-04-07: payload only sends item_id, item_type, quantity, notes)
    assert "item_id" in content or "itemId" in content, "checkout.js must map items with item_id"

    # Rule: Clear cart after order submission
    assert "cart.clear" in content, "checkout.js must call cart.clear() after successful submission"


def test_ui_checkout_helpers_and_modals(client: TestClient):
    """Test that /js/ui.js exports phone masking and success modal functions."""
    response = client.get("/js/ui.js")
    assert response.status_code == 200, "Failed to load /js/ui.js"

    content = response.text
    assert "maskPhone" in content, "ui.js should export maskPhone helper"
    assert "openSuccessModal" in content, "ui.js should export openSuccessModal"


def test_checkout_validations(client: TestClient, db_session: Session):
    """Test server-side contract and validations aligned with storefront checkout behavior."""
    # Seed category & product
    cat = Category(name="Pizzas Especiais", slug="pizzas-especiais", is_active=True, order=1)
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)

    prod = Product(
        title="Pizza Rex Margherita",
        description="Molho rústico, mozzarella e manjericão",
        price=50.00,
        is_active=True,
        category_id=cat.id,
    )
    db_session.add(prod)

    # Seed delivery zone
    zone = DeliveryZone(name="Bairro Dino 1", fee=10.00, estimated_minutes=30, is_active=True)
    db_session.add(zone)
    db_session.commit()
    db_session.refresh(prod)
    db_session.refresh(zone)

    # 1. Successful delivery order
    valid_payload = {
        "customer_name": "Rex Silva",
        "customer_phone": "(11) 98765-4321",
        "customer_address": "Rua Vulcânica, 42",
        "customer_reference": "Em frente à caverna",
        "delivery_type": "delivery",
        "delivery_zone_id": zone.id,
        "payment_method": "pix",
        "items": [
            {
                "item_type": "product",
                "item_id": prod.id,
                "quantity": 2,
                "notes": "Massa crocante"
            }
        ]
    }
    res = client.post("/api/v1/orders", json=valid_payload)
    assert res.status_code == 201
    data = res.json()
    assert "order" in data
    assert "whatsapp_url" in data
    assert float(data["order"]["subtotal"]) == 100.00
    assert float(data["order"]["delivery_fee"]) == 10.00
    assert float(data["order"]["total_amount"]) == 110.00

    # 2. Successful pickup order (fee = 0, no delivery_zone_id required)
    pickup_payload = {
        "customer_name": "Dino Santos",
        "customer_phone": "(11) 91234-5678",
        "delivery_type": "pickup",
        "payment_method": "credit_card",
        "items": [
            {
                "item_type": "product",
                "item_id": prod.id,
                "quantity": 1
            }
        ]
    }
    res_pickup = client.post("/api/v1/orders", json=pickup_payload)
    assert res_pickup.status_code == 201
    pickup_data = res_pickup.json()
    assert float(pickup_data["order"]["delivery_fee"]) == 0.00
    assert float(pickup_data["order"]["total_amount"]) == 50.00

    # 3. Cash with insufficient change_for rejected by server
    cash_bad_payload = {
        "customer_name": "T-Rex Junior",
        "customer_phone": "(11) 99999-8888",
        "delivery_type": "pickup",
        "payment_method": "cash",
        "change_for": 30.00,  # total is 50.00
        "items": [
            {
                "item_type": "product",
                "item_id": prod.id,
                "quantity": 1
            }
        ]
    }
    res_cash_bad = client.post("/api/v1/orders", json=cash_bad_payload)
    assert res_cash_bad.status_code == 400
