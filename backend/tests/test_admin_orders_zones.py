import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.product import Product
from app.models.combo import Combo
from app.models.delivery import DeliveryZone
from app.models.order import Order, OrderItem


# ==============================================================================
# 1. Admin Static Assets & Routing Tests (Plan 05-02 Modules)
# ==============================================================================

def test_admin_new_js_modules_served(client: TestClient):
    """Test that admin-zones.js, admin-sound.js, and admin-orders.js are served correctly."""
    modules = [
        ("/admin/js/admin-zones.js", ["initZones", "loadZones", "openZoneModal"]),
        ("/admin/js/admin-sound.js", ["initSound", "toggleSound", "playNewOrderSound", "AudioContext"]),
        ("/admin/js/admin-orders.js", ["initOrders", "loadOrders", "startOrderPolling", "STATUS_CONFIG"]),
    ]

    for path, expected_tokens in modules:
        response = client.get(path)
        assert response.status_code == 200, f"Failed to load {path}"
        assert "javascript" in response.headers.get("content-type", "")
        for token in expected_tokens:
            assert token in response.text, f"Token '{token}' not found in {path}"


def test_admin_html_contains_kanban_and_zones_markup(client: TestClient):
    """Test that admin SPA HTML contains complete markup for Kanban columns, zones, and modals."""
    response = client.get("/admin")
    assert response.status_code == 200
    html = response.text

    # Kanban columns
    assert "orders-kanban-board" in html
    assert "cards-col-pending" in html
    assert "cards-col-in_preparation" in html
    assert "cards-col-out_for_delivery" in html
    assert "cards-col-delivered" in html
    assert "cards-col-cancelled" in html

    # Zones management
    assert "zones-table" in html
    assert "zones-search" in html
    assert "btn-new-zone" in html

    # Modals
    assert "modal-zone" in html
    assert "modal-order-details" in html
    assert "order-detail-status-badge" in html
    assert "btn-advance-order-status" in html


# ==============================================================================
# 2. Delivery Zones Management & Toggles Tests
# ==============================================================================

def test_admin_delivery_zones_crud_and_toggle(client: TestClient, admin_token_headers):
    """Test full CRUD lifecycle and 1-click active toggle for delivery zones."""
    # 1. Unauthenticated access is rejected
    unauth_resp = client.get("/api/v1/delivery-zones/admin-list")
    assert unauth_resp.status_code == 401

    # 2. Create new delivery zone
    create_payload = {
        "name": "Bairro Jurássico Prime",
        "fee": 9.50,
        "estimated_minutes": 45,
        "is_active": True,
    }
    create_resp = client.post(
        "/api/v1/delivery-zones",
        json=create_payload,
        headers=admin_token_headers,
    )
    assert create_resp.status_code == 201
    zone_data = create_resp.json()
    zone_id = zone_data["id"]
    assert zone_data["name"] == "Bairro Jurássico Prime"
    assert Decimal(str(zone_data["fee"])) == Decimal("9.50")
    assert zone_data["estimated_minutes"] == 45
    assert zone_data["is_active"] is True

    # 3. List zones in admin view
    list_resp = client.get("/api/v1/delivery-zones/admin-list", headers=admin_token_headers)
    assert list_resp.status_code == 200
    zones = list_resp.json()
    assert any(z["id"] == zone_id for z in zones)

    # 4. Toggle is_active
    toggle_resp = client.patch(
        f"/api/v1/delivery-zones/{zone_id}/toggle-active",
        headers=admin_token_headers,
    )
    assert toggle_resp.status_code == 200
    assert toggle_resp.json()["is_active"] is False

    # 5. Update zone fee and estimated minutes
    update_payload = {
        "name": "Bairro Jurássico Prime & Sul",
        "fee": 12.00,
        "estimated_minutes": 50,
    }
    update_resp = client.put(
        f"/api/v1/delivery-zones/{zone_id}",
        json=update_payload,
        headers=admin_token_headers,
    )
    assert update_resp.status_code == 200
    updated_data = update_resp.json()
    assert updated_data["name"] == "Bairro Jurássico Prime & Sul"
    assert Decimal(str(updated_data["fee"])) == Decimal("12.00")
    assert updated_data["estimated_minutes"] == 50

    # 6. Delete zone
    delete_resp = client.delete(
        f"/api/v1/delivery-zones/{zone_id}",
        headers=admin_token_headers,
    )
    assert delete_resp.status_code in (200, 204)

    # 7. Verify deletion
    get_deleted = client.get(f"/api/v1/delivery-zones/{zone_id}")
    assert get_deleted.status_code == 404


# ==============================================================================
# 3. Orders Kanban Workflow, Inspection & Status Transitions Tests
# ==============================================================================

@pytest.fixture
def setup_orders_catalog(db_session: Session):
    """Seed test category, product, and delivery zone for order tests."""
    cat = Category(name="Pizzas Especiais", slug="pizzas-especiais", is_active=True, order=1)
    db_session.add(cat)
    db_session.flush()

    prod = Product(
        title="Pizza Jurassic Pepperoni",
        description="Pepperoni artesanal com queijo derretido.",
        price=Decimal("58.00"),
        is_active=True,
        is_promo=False,
        category_id=cat.id,
    )
    zone = DeliveryZone(
        name="Vila Dinossauro",
        fee=Decimal("8.00"),
        estimated_minutes=35,
        is_active=True,
    )
    db_session.add_all([prod, zone])
    db_session.commit()
    db_session.refresh(prod)
    db_session.refresh(zone)
    return {"prod": prod, "zone": zone}


def test_admin_orders_kanban_lifecycle_and_validation(
    client: TestClient,
    admin_token_headers,
    setup_orders_catalog
):
    """Test full order lifecycle transitions across Kanban stages and schema validation."""
    prod = setup_orders_catalog["prod"]
    zone = setup_orders_catalog["zone"]

    # 1. Customer creates an order
    create_payload = {
        "customer_name": "Velociraptor Blue",
        "customer_phone": "11977778888",
        "customer_address": "Alameda dos Carnívoros, 400",
        "customer_reference": "Portão Verde",
        "delivery_type": "delivery",
        "delivery_zone_id": zone.id,
        "payment_method": "cash",
        "change_for": 100.00,
        "order_notes": "Cortar em 8 pedaços bem crocantes.",
        "items": [
            {
                "item_type": "product",
                "item_id": prod.id,
                "quantity": 1,
                "notes": "massa média",
            }
        ],
    }
    create_resp = client.post("/api/v1/orders", json=create_payload)
    assert create_resp.status_code == 201
    order_id = create_resp.json()["order"]["id"]

    # 2. Admin unauthenticated access is rejected
    assert client.get("/api/v1/orders").status_code == 401
    assert client.get(f"/api/v1/orders/{order_id}").status_code == 401
    assert client.patch(f"/api/v1/orders/{order_id}/status", json={"status": "in_preparation"}).status_code == 401

    # 3. Admin lists orders
    list_resp = client.get("/api/v1/orders", headers=admin_token_headers)
    assert list_resp.status_code == 200
    orders = list_resp.json()
    assert any(o["id"] == order_id for o in orders)

    # 4. Admin inspects order details
    detail_resp = client.get(f"/api/v1/orders/{order_id}", headers=admin_token_headers)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["customer_name"] == "Velociraptor Blue"
    assert detail["customer_phone"] == "11977778888"
    assert detail["delivery_type"] == "delivery"
    assert detail["payment_method"] == "cash"
    assert Decimal(str(detail["subtotal"])) == Decimal("58.00")
    assert Decimal(str(detail["delivery_fee"])) == Decimal("8.00")
    assert Decimal(str(detail["total_amount"])) == Decimal("66.00")
    assert Decimal(str(detail["change_for"])) == Decimal("100.00")
    assert detail["status"] == "pending"
    assert len(detail["items"]) == 1
    assert detail["items"][0]["title"] == "Pizza Jurassic Pepperoni"

    # 5. Kanban Stage Transitions: pending -> in_preparation -> out_for_delivery -> delivered
    transitions = ["in_preparation", "out_for_delivery", "delivered"]
    for next_status in transitions:
        patch_resp = client.patch(
            f"/api/v1/orders/{order_id}/status",
            json={"status": next_status},
            headers=admin_token_headers,
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["status"] == next_status

    # 6. Filter orders by status
    delivered_list = client.get("/api/v1/orders?status=delivered", headers=admin_token_headers)
    assert delivered_list.status_code == 200
    assert any(o["id"] == order_id for o in delivered_list.json())

    # 7. Invalid status rejected with 422
    invalid_resp = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "flying_dino"},
        headers=admin_token_headers,
    )
    assert invalid_resp.status_code == 422


def test_admin_order_cancellation(
    client: TestClient,
    admin_token_headers,
    setup_orders_catalog
):
    """Test order cancellation transition directly from pending to cancelled."""
    prod = setup_orders_catalog["prod"]

    create_resp = client.post(
        "/api/v1/orders",
        json={
            "customer_name": "Triceratops Jr",
            "customer_phone": "11988889999",
            "delivery_type": "pickup",
            "payment_method": "pix",
            "items": [{"item_type": "product", "item_id": prod.id, "quantity": 1}],
        },
    )
    assert create_resp.status_code == 201
    order_id = create_resp.json()["order"]["id"]

    # Cancel order
    cancel_resp = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "cancelled"},
        headers=admin_token_headers,
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"
