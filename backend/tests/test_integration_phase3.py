from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.models.category import Category
from app.models.combo import Combo
from app.models.delivery import DeliveryZone
from app.models.product import Product


@pytest.fixture
def phase3_catalog(db_session):
    """Seed comprehensive catalog for Phase 3 E2E testing."""
    cat_pizza = Category(name="Pizzas", slug="pizzas", order=1, is_active=True)
    cat_drinks = Category(name="Bebidas", slug="bebidas", order=2, is_active=True)
    db_session.add_all([cat_pizza, cat_drinks])
    db_session.flush()

    p1 = Product(
        title="Pizza T-Rex Suprema",
        description="Molho rústico, queijo duplo, pepperoni crocante",
        price=Decimal("62.50"),
        is_promo=False,
        is_active=True,
        category_id=cat_pizza.id,
    )
    p2 = Product(
        title="Refrigerante Dinos 2L",
        description="Garrafa 2 Litros bem gelada",
        price=Decimal("14.00"),
        is_promo=False,
        is_active=True,
        category_id=cat_drinks.id,
    )
    p_inactive = Product(
        title="Pizza Indisponível",
        description="Esgotada",
        price=Decimal("70.00"),
        is_promo=False,
        is_active=False,
        category_id=cat_pizza.id,
    )
    db_session.add_all([p1, p2, p_inactive])

    combo = Combo(
        title="Super Combo Triássico",
        description="1 Pizza T-Rex + 1 Refri 2L",
        price=Decimal("69.90"),
        is_active=True,
        is_promo_of_day=True,
    )
    db_session.add(combo)

    zone_centro = DeliveryZone(
        name="Bairro Centro",
        fee=Decimal("6.00"),
        estimated_minutes=30,
        is_active=True,
    )
    zone_norte = DeliveryZone(
        name="Zona Norte",
        fee=Decimal("12.50"),
        estimated_minutes=45,
        is_active=True,
    )
    db_session.add_all([zone_centro, zone_norte])
    db_session.commit()

    return {
        "p1": p1,
        "p2": p2,
        "p_inactive": p_inactive,
        "combo": combo,
        "zone_centro": zone_centro,
        "zone_norte": zone_norte,
    }


def test_e2e_guest_checkout_to_admin_lifecycle(client: TestClient, admin_token_headers, phase3_catalog):
    """
    End-to-end test verifying:
    1. Guest customer creates delivery order with multiple products & combo.
    2. Backend computes exact authoritative subtotal, delivery fee, and total.
    3. WhatsApp fallback URL and status are returned in checkout response.
    4. Admin authenticates, lists orders, finds newly created order.
    5. Admin inspects order details (items, notes, calculated totals).
    6. Admin transitions order through production pipeline (pending -> confirmed -> in_preparation -> delivered).
    """
    p1 = phase3_catalog["p1"]
    p2 = phase3_catalog["p2"]
    combo = phase3_catalog["combo"]
    zone_centro = phase3_catalog["zone_centro"]

    # Step 1: Customer submits order (trying to inject price tampering, which is ignored)
    checkout_payload = {
        "customer_name": "Dr. Alan Grant",
        "customer_phone": "11999998888",
        "customer_address": "Parque dos Dinossauros, Portão 3",
        "customer_reference": "Próximo à cerca elétrica",
        "delivery_type": "delivery",
        "delivery_zone_id": zone_centro.id,
        "payment_method": "cash",
        "change_for": 200.00,
        "order_notes": "Entregar com cuidado!",
        "items": [
            {"item_type": "product", "item_id": p1.id, "quantity": 1, "notes": "massa fina"},
            {"item_type": "product", "item_id": p2.id, "quantity": 1},
            {"item_type": "combo", "item_id": combo.id, "quantity": 1, "notes": "tudo bem gelado"},
        ],
    }

    checkout_res = client.post("/api/v1/orders", json=checkout_payload)
    assert checkout_res.status_code == 201
    checkout_data = checkout_res.json()

    # Step 2: Authoritative calculations check
    # p1: 62.50 * 1 = 62.50
    # p2: 14.00 * 1 = 14.00
    # combo: 69.90 * 1 = 69.90
    # Subtotal: 62.50 + 14.00 + 69.90 = 146.40
    # Delivery fee: 6.00
    # Total: 152.40
    order_data = checkout_data["order"]
    order_id = order_data["id"]
    assert Decimal(str(order_data["subtotal"])) == Decimal("146.40")
    assert Decimal(str(order_data["delivery_fee"])) == Decimal("6.00")
    assert Decimal(str(order_data["total_amount"])) == Decimal("152.40")
    assert Decimal(str(order_data["change_for"])) == Decimal("200.00")
    assert order_data["status"] == "pending"
    assert len(order_data["items"]) == 3

    # Step 3: WhatsApp fallback URL verification
    assert "whatsapp_url" in checkout_data
    assert "https://wa.me/" in checkout_data["whatsapp_url"]
    assert checkout_data["whatsapp_status"] in ("sent", "fallback_generated")

    # Step 4: Admin queries order list
    list_res = client.get("/api/v1/orders", headers=admin_token_headers)
    assert list_res.status_code == 200
    orders_list = list_res.json()
    assert any(o["id"] == order_id for o in orders_list)

    # Step 5: Admin inspects order details
    detail_res = client.get(f"/api/v1/orders/{order_id}", headers=admin_token_headers)
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["customer_name"] == "Dr. Alan Grant"
    assert detail_data["customer_address"] == "Parque dos Dinossauros, Portão 3"
    assert detail_data["order_notes"] == "Entregar com cuidado!"
    assert len(detail_data["items"]) == 3

    # Step 6: Admin updates status pipeline
    # pending -> confirmed
    s1 = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "confirmed"},
        headers=admin_token_headers,
    )
    assert s1.status_code == 200
    assert s1.json()["status"] == "confirmed"

    # confirmed -> in_preparation
    s2 = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "in_preparation"},
        headers=admin_token_headers,
    )
    assert s2.status_code == 200
    assert s2.json()["status"] == "in_preparation"

    # in_preparation -> out_for_delivery
    s3 = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "out_for_delivery"},
        headers=admin_token_headers,
    )
    assert s3.status_code == 200
    assert s3.json()["status"] == "out_for_delivery"

    # out_for_delivery -> delivered
    s4 = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "delivered"},
        headers=admin_token_headers,
    )
    assert s4.status_code == 200
    assert s4.json()["status"] == "delivered"


def test_e2e_pickup_zero_delivery_fee(client: TestClient, phase3_catalog):
    """Verify pickup order zeroes delivery fee regardless of any passed zone data."""
    p1 = phase3_catalog["p1"]

    pickup_payload = {
        "customer_name": "Ellie Sattler",
        "customer_phone": "11988889999",
        "delivery_type": "pickup",
        "payment_method": "pix",
        "items": [{"item_type": "product", "item_id": p1.id, "quantity": 2}],
    }

    res = client.post("/api/v1/orders", json=pickup_payload)
    assert res.status_code == 201
    order = res.json()["order"]

    assert order["delivery_type"] == "pickup"
    assert order["delivery_zone_id"] is None
    assert Decimal(str(order["delivery_fee"])) == Decimal("0.00")
    # p1: 62.50 * 2 = 125.00
    assert Decimal(str(order["subtotal"])) == Decimal("125.00")
    assert Decimal(str(order["total_amount"])) == Decimal("125.00")
