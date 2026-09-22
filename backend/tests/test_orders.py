from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.models.category import Category
from app.models.combo import Combo
from app.models.delivery import DeliveryZone
from app.models.order import Order
from app.models.product import Product


@pytest.fixture
def order_catalog(db_session):
    """Seed test category, products, combo, and delivery zone for order tests."""
    category = Category(name="Pizzas Clássicas", slug="pizzas-classicas", order=1, is_active=True)
    db_session.add(category)
    db_session.flush()

    prod1 = Product(
        title="Pizza Calabresa Dinos",
        description="Molho artesanal, mussarela e calabresa crocante",
        price=Decimal("49.90"),
        is_promo=False,
        is_active=True,
        category_id=category.id,
    )
    prod2 = Product(
        title="Coca-Cola 2L",
        description="Refrigerante garrafa 2 litros",
        price=Decimal("12.00"),
        is_promo=False,
        is_active=True,
        category_id=category.id,
    )
    inactive_prod = Product(
        title="Pizza Fora de Estoque",
        description="Indisponível temporariamente",
        price=Decimal("59.90"),
        is_promo=False,
        is_active=False,
        category_id=category.id,
    )
    db_session.add_all([prod1, prod2, inactive_prod])

    combo1 = Combo(
        title="Combo Jurássico 1",
        description="1 Pizza Calabresa + 1 Coca-Cola 2L",
        price=Decimal("55.00"),
        is_active=True,
        is_promo_of_day=True,
    )
    inactive_combo = Combo(
        title="Combo Indisponível",
        description="Não disponível hoje",
        price=Decimal("45.00"),
        is_active=False,
        is_promo_of_day=False,
    )
    db_session.add_all([combo1, inactive_combo])

    zone1 = DeliveryZone(
        name="Centro",
        fee=Decimal("7.50"),
        estimated_minutes=35,
        is_active=True,
    )
    inactive_zone = DeliveryZone(
        name="Zona Distante",
        fee=Decimal("20.00"),
        estimated_minutes=60,
        is_active=False,
    )
    db_session.add_all([zone1, inactive_zone])
    db_session.commit()

    return {
        "prod1": prod1,
        "prod2": prod2,
        "inactive_prod": inactive_prod,
        "combo1": combo1,
        "inactive_combo": inactive_combo,
        "zone1": zone1,
        "inactive_zone": inactive_zone,
    }


def test_create_order_delivery_success(client: TestClient, order_catalog):
    prod1 = order_catalog["prod1"]
    prod2 = order_catalog["prod2"]
    zone1 = order_catalog["zone1"]

    payload = {
        "customer_name": "T-Rex Silva",
        "customer_phone": "11988887777",
        "customer_address": "Rua dos Fósseis, 123 - Apto 4",
        "customer_reference": "Próximo ao museu",
        "delivery_type": "delivery",
        "delivery_zone_id": zone1.id,
        "payment_method": "pix",
        "order_notes": "Tocar a campainha duas vezes",
        "items": [
            {"item_type": "product", "item_id": prod1.id, "quantity": 2, "notes": "sem cebola"},
            {"item_type": "product", "item_id": prod2.id, "quantity": 1, "notes": "bem gelada"},
        ],
    }

    response = client.post("/api/v1/orders", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert "order" in data
    order = data["order"]
    assert order["customer_name"] == "T-Rex Silva"
    assert order["customer_phone"] == "11988887777"
    assert order["delivery_type"] == "delivery"
    assert order["delivery_zone_id"] == zone1.id

    # Authoritative calculation check
    # prod1: 49.90 * 2 = 99.80
    # prod2: 12.00 * 1 = 12.00
    # Subtotal = 111.80
    # Delivery fee = 7.50
    # Total = 119.30
    assert Decimal(str(order["subtotal"])) == Decimal("111.80")
    assert Decimal(str(order["delivery_fee"])) == Decimal("7.50")
    assert Decimal(str(order["total_amount"])) == Decimal("119.30")
    assert order["status"] == "pending"
    assert len(order["items"]) == 2

    # Verify WhatsApp URL and status
    assert "whatsapp_url" in data
    assert "https://wa.me/" in data["whatsapp_url"]
    assert data["whatsapp_status"] in ("sent", "fallback_generated")


def test_create_order_pickup_success(client: TestClient, order_catalog):
    prod1 = order_catalog["prod1"]
    combo1 = order_catalog["combo1"]

    payload = {
        "customer_name": "Velociraptor Santos",
        "customer_phone": "11977776666",
        "delivery_type": "pickup",
        "payment_method": "credit_card",
        "items": [
            {"item_type": "product", "item_id": prod1.id, "quantity": 1},
            {"item_type": "combo", "item_id": combo1.id, "quantity": 1, "notes": "sem gelo"},
        ],
    }

    response = client.post("/api/v1/orders", json=payload)
    assert response.status_code == 201
    data = response.json()

    order = data["order"]
    assert order["delivery_type"] == "pickup"
    assert order["delivery_zone_id"] is None
    assert Decimal(str(order["delivery_fee"])) == Decimal("0.00")
    # prod1 (49.90) + combo1 (55.00) = 104.90
    assert Decimal(str(order["subtotal"])) == Decimal("104.90")
    assert Decimal(str(order["total_amount"])) == Decimal("104.90")


def test_cash_payment_change_validation(client: TestClient, order_catalog):
    prod1 = order_catalog["prod1"]
    zone1 = order_catalog["zone1"]

    # Total will be 49.90 + 7.50 = 57.40
    # Test change_for < total_amount (R$ 50.00) -> Should fail 400
    invalid_cash_payload = {
        "customer_name": "Brontossauro Lima",
        "customer_phone": "11966665555",
        "customer_address": "Av. Jurássica, 45",
        "delivery_type": "delivery",
        "delivery_zone_id": zone1.id,
        "payment_method": "cash",
        "change_for": 50.00,
        "items": [{"item_type": "product", "item_id": prod1.id, "quantity": 1}],
    }
    response = client.post("/api/v1/orders", json=invalid_cash_payload)
    assert response.status_code == 400
    assert "não pode ser menor que o valor total" in response.json()["detail"]

    # Test change_for >= total_amount (R$ 100.00) -> Should succeed
    valid_cash_payload = {
        **invalid_cash_payload,
        "change_for": 100.00,
    }
    response = client.post("/api/v1/orders", json=valid_cash_payload)
    assert response.status_code == 201
    order = response.json()["order"]
    assert Decimal(str(order["change_for"])) == Decimal("100.00")
    assert Decimal(str(order["total_amount"])) == Decimal("57.40")


def test_inactive_item_rejection(client: TestClient, order_catalog):
    inactive_prod = order_catalog["inactive_prod"]
    inactive_combo = order_catalog["inactive_combo"]
    zone1 = order_catalog["zone1"]

    # Inactive product
    payload_inactive_prod = {
        "customer_name": "T-Rex Silva",
        "customer_phone": "11988887777",
        "customer_address": "Rua dos Fósseis, 123",
        "delivery_type": "delivery",
        "delivery_zone_id": zone1.id,
        "payment_method": "pix",
        "items": [{"item_type": "product", "item_id": inactive_prod.id, "quantity": 1}],
    }
    res1 = client.post("/api/v1/orders", json=payload_inactive_prod)
    assert res1.status_code == 400
    assert "não encontrado ou indisponível" in res1.json()["detail"]

    # Inactive combo
    payload_inactive_combo = {
        "customer_name": "T-Rex Silva",
        "customer_phone": "11988887777",
        "customer_address": "Rua dos Fósseis, 123",
        "delivery_type": "delivery",
        "delivery_zone_id": zone1.id,
        "payment_method": "pix",
        "items": [{"item_type": "combo", "item_id": inactive_combo.id, "quantity": 1}],
    }
    res2 = client.post("/api/v1/orders", json=payload_inactive_combo)
    assert res2.status_code == 400
    assert "não encontrado ou indisponível" in res2.json()["detail"]


def test_delivery_validation_missing_zone_or_address(client: TestClient, order_catalog):
    prod1 = order_catalog["prod1"]
    inactive_zone = order_catalog["inactive_zone"]

    # Missing address
    payload_no_address = {
        "customer_name": "T-Rex Silva",
        "customer_phone": "11988887777",
        "delivery_type": "delivery",
        "delivery_zone_id": order_catalog["zone1"].id,
        "payment_method": "pix",
        "items": [{"item_type": "product", "item_id": prod1.id, "quantity": 1}],
    }
    res_no_address = client.post("/api/v1/orders", json=payload_no_address)
    assert res_no_address.status_code == 400
    assert "Endereço de entrega é obrigatório" in res_no_address.json()["detail"]

    # Missing zone id
    payload_no_zone = {
        "customer_name": "T-Rex Silva",
        "customer_phone": "11988887777",
        "customer_address": "Rua Central, 100",
        "delivery_type": "delivery",
        "payment_method": "pix",
        "items": [{"item_type": "product", "item_id": prod1.id, "quantity": 1}],
    }
    res_no_zone = client.post("/api/v1/orders", json=payload_no_zone)
    assert res_no_zone.status_code == 400
    assert "Bairro / Zona de entrega é obrigatório" in res_no_zone.json()["detail"]

    # Inactive zone id
    payload_inactive_zone = {
        "customer_name": "T-Rex Silva",
        "customer_phone": "11988887777",
        "customer_address": "Rua Central, 100",
        "delivery_type": "delivery",
        "delivery_zone_id": inactive_zone.id,
        "payment_method": "pix",
        "items": [{"item_type": "product", "item_id": prod1.id, "quantity": 1}],
    }
    res_inactive_zone = client.post("/api/v1/orders", json=payload_inactive_zone)
    assert res_inactive_zone.status_code == 400
    assert "não encontrado ou inativo" in res_inactive_zone.json()["detail"]


def test_admin_order_monitoring_and_status_update(client: TestClient, admin_token_headers, order_catalog):
    prod1 = order_catalog["prod1"]
    zone1 = order_catalog["zone1"]

    # Create 2 orders
    res1 = client.post(
        "/api/v1/orders",
        json={
            "customer_name": "Cliente 1",
            "customer_phone": "11911112222",
            "delivery_type": "pickup",
            "payment_method": "pix",
            "items": [{"item_type": "product", "item_id": prod1.id, "quantity": 1}],
        },
    )
    assert res1.status_code == 201
    order1_id = res1.json()["order"]["id"]

    res2 = client.post(
        "/api/v1/orders",
        json={
            "customer_name": "Cliente 2",
            "customer_phone": "11933334444",
            "customer_address": "Rua Teste, 500",
            "delivery_type": "delivery",
            "delivery_zone_id": zone1.id,
            "payment_method": "credit_card",
            "items": [{"item_type": "product", "item_id": prod1.id, "quantity": 2}],
        },
    )
    assert res2.status_code == 201
    order2_id = res2.json()["order"]["id"]

    # Test unauthenticated access to admin endpoints -> 401
    unauth_list = client.get("/api/v1/orders")
    assert unauth_list.status_code == 401

    unauth_detail = client.get(f"/api/v1/orders/{order1_id}")
    assert unauth_detail.status_code == 401

    unauth_status = client.patch(
        f"/api/v1/orders/{order1_id}/status",
        json={"status": "confirmed"},
    )
    assert unauth_status.status_code == 401

    # Test authenticated admin list
    auth_list = client.get("/api/v1/orders", headers=admin_token_headers)
    assert auth_list.status_code == 200
    orders_list = auth_list.json()
    assert len(orders_list) >= 2
    order_ids = [o["id"] for o in orders_list]
    assert order1_id in order_ids
    assert order2_id in order_ids

    # Test authenticated admin detail
    auth_detail = client.get(f"/api/v1/orders/{order2_id}", headers=admin_token_headers)
    assert auth_detail.status_code == 200
    detail_data = auth_detail.json()
    assert detail_data["id"] == order2_id
    assert detail_data["customer_name"] == "Cliente 2"
    assert len(detail_data["items"]) == 1
    assert detail_data["items"][0]["quantity"] == 2

    # Test 404 on non-existent order
    not_found = client.get("/api/v1/orders/99999", headers=admin_token_headers)
    assert not_found.status_code == 404

    # Test status update workflow
    # pending -> confirmed
    patch_confirmed = client.patch(
        f"/api/v1/orders/{order1_id}/status",
        json={"status": "confirmed"},
        headers=admin_token_headers,
    )
    assert patch_confirmed.status_code == 200
    assert patch_confirmed.json()["status"] == "confirmed"

    # confirmed -> in_preparation
    patch_prep = client.patch(
        f"/api/v1/orders/{order1_id}/status",
        json={"status": "in_preparation"},
        headers=admin_token_headers,
    )
    assert patch_prep.status_code == 200
    assert patch_prep.json()["status"] == "in_preparation"

    # in_preparation -> out_for_delivery
    patch_delivery = client.patch(
        f"/api/v1/orders/{order1_id}/status",
        json={"status": "out_for_delivery"},
        headers=admin_token_headers,
    )
    assert patch_delivery.status_code == 200
    assert patch_delivery.json()["status"] == "out_for_delivery"

    # out_for_delivery -> delivered
    patch_delivered = client.patch(
        f"/api/v1/orders/{order1_id}/status",
        json={"status": "delivered"},
        headers=admin_token_headers,
    )
    assert patch_delivered.status_code == 200
    assert patch_delivered.json()["status"] == "delivered"

    # Test filter by status
    filtered_res = client.get("/api/v1/orders?status=delivered", headers=admin_token_headers)
    assert filtered_res.status_code == 200
    filtered_orders = filtered_res.json()
    assert all(o["status"] == "delivered" for o in filtered_orders)
    assert order1_id in [o["id"] for o in filtered_orders]

    # Test invalid status -> 422
    invalid_patch = client.patch(
        f"/api/v1/orders/{order1_id}/status",
        json={"status": "invalid_status_xyz"},
        headers=admin_token_headers,
    )
    assert invalid_patch.status_code == 422
