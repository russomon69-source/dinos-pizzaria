from datetime import datetime, timezone, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.coupon import Coupon
from app.models.delivery import DeliveryZone
from app.models.product import Product
from app.models.site_content import SiteContent


def test_order_with_coupon_and_tracking(client: TestClient, db_session: Session):
    cat = Category(name="Pizzas Salgadas", slug="pizzas-salgadas", is_active=True)
    db_session.add(cat)
    db_session.commit()

    prod = Product(
        title="Pizza T-Rex Especial",
        description="Massa artesanal. Média: R$ 45,00, Gigante: R$ 55,00",
        price=Decimal("45.00"),
        category_id=cat.id,
        is_active=True,
    )
    zone = DeliveryZone(name="Centro", fee=Decimal("8.00"), is_active=True, min_order_value=Decimal("30.00"))
    coupon = Coupon(
        code="BEMVINDO10",
        discount_type="fixed",
        discount_value=Decimal("10.00"),
        min_subtotal=Decimal("40.00"),
        is_active=True,
    )
    db_session.add_all([prod, zone, coupon])
    db_session.commit()

    order_payload = {
        "customer_name": "João Pereira",
        "customer_phone": "(11) 98765-4321",
        "customer_address": "Rua das Flores, 123",
        "delivery_type": "delivery",
        "delivery_zone_id": zone.id,
        "payment_method": "credit_card",
        "coupon_code": "BEMVINDO10",
        "fulfillment_time_type": "asap",
        "items": [
            {
                "item_type": "product",
                "item_id": prod.id,
                "quantity": 1,
                "options": {"size": "Média"},
            }
        ],
    }

    # Place order
    r = client.post("/api/v1/orders", json=order_payload)
    assert r.status_code == 201
    data = r.json()
    order_data = data["order"]
    order_id = order_data["id"]

    # Subtotal 45.00, discount 10.00, delivery 8.00 -> total 43.00
    assert float(order_data["subtotal"]) == 45.00
    assert float(order_data["discount_amount"]) == 10.00
    assert float(order_data["delivery_fee"]) == 8.00
    assert float(order_data["total_amount"]) == 43.00

    # Verify coupon used_count incremented
    db_session.refresh(coupon)
    assert coupon.used_count == 1

    # Public tracking success with last 4 digits "4321"
    r_track = client.get(f"/api/v1/orders/track?order_id={order_id}&phone=4321")
    assert r_track.status_code == 200
    track_data = r_track.json()
    assert track_data["id"] == order_id
    assert track_data["customer_name"] == "João Pereira"
    assert track_data["status"] == "pending"
    assert track_data["items_count"] == 1
    assert len(track_data["items_summary"]) == 1

    # Public tracking with wrong phone fails
    r_wrong = client.get(f"/api/v1/orders/track?order_id={order_id}&phone=9999")
    assert r_wrong.status_code == 404


def test_order_store_closed_and_scheduled_flow(client: TestClient, db_session: Session):
    cat = Category(name="Pizzas", slug="pizzas", is_active=True)
    db_session.add(cat)
    db_session.commit()

    prod = Product(
        title="Pizza Brontossauro",
        description="Média: R$ 50,00",
        price=Decimal("50.00"),
        category_id=cat.id,
        is_active=True,
    )
    zone = DeliveryZone(name="Bairro Alto", fee=Decimal("5.00"), is_active=True)
    # Set store to closed
    store_closed_setting = SiteContent(key="store_is_open", value="false")
    closed_msg_setting = SiteContent(key="store_closed_message", value="Estamos fechados agora.")
    db_session.add_all([prod, zone, store_closed_setting, closed_msg_setting])
    db_session.commit()

    # Immediate order when closed -> 400
    payload_asap = {
        "customer_name": "Marcos",
        "customer_phone": "11988887777",
        "delivery_type": "pickup",
        "payment_method": "pix",
        "fulfillment_time_type": "asap",
        "items": [{"item_type": "product", "item_id": prod.id, "quantity": 1}],
    }
    r_asap = client.post("/api/v1/orders", json=payload_asap)
    assert r_asap.status_code == 400
    assert "fechados" in r_asap.json()["detail"].lower()

    # Scheduled order for 2 hours in the future -> success
    future_time = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    payload_sched = {
        "customer_name": "Marcos",
        "customer_phone": "11988887777",
        "delivery_type": "pickup",
        "payment_method": "pix",
        "fulfillment_time_type": "scheduled",
        "scheduled_for": future_time,
        "items": [{"item_type": "product", "item_id": prod.id, "quantity": 1}],
    }
    r_sched = client.post("/api/v1/orders", json=payload_sched)
    assert r_sched.status_code == 201
    assert r_sched.json()["order"]["fulfillment_time_type"] == "scheduled"


def test_neighborhood_min_order_value_validation(client: TestClient, db_session: Session):
    cat = Category(name="Pizzas", slug="pizzas-2", is_active=True)
    db_session.add(cat)
    db_session.commit()

    prod = Product(
        title="Pizza Broto",
        description="Pequena: R$ 25,00",
        price=Decimal("25.00"),
        category_id=cat.id,
        is_active=True,
    )
    zone = DeliveryZone(name="Zona Leste", fee=Decimal("10.00"), is_active=True, min_order_value=Decimal("60.00"))
    db_session.add_all([prod, zone])
    db_session.commit()

    # Subtotal 25.00 is below min_order_value 60.00 for delivery -> 400
    payload = {
        "customer_name": "Ana",
        "customer_phone": "11977776666",
        "customer_address": "Av Principal, 400",
        "delivery_type": "delivery",
        "delivery_zone_id": zone.id,
        "payment_method": "pix",
        "items": [{"item_type": "product", "item_id": prod.id, "quantity": 1}],
    }
    r_fail = client.post("/api/v1/orders", json=payload)
    assert r_fail.status_code == 400
    assert "mínimo" in r_fail.json()["detail"].lower()

    # Pickup ignores neighborhood min_order_value -> success
    payload_pickup = {
        "customer_name": "Ana",
        "customer_phone": "11977776666",
        "delivery_type": "pickup",
        "payment_method": "pix",
        "items": [{"item_type": "product", "item_id": prod.id, "quantity": 1}],
    }
    r_pickup = client.post("/api/v1/orders", json=payload_pickup)
    assert r_pickup.status_code == 201


def test_featured_products_api_and_admin_toggle(client: TestClient, db_session: Session, admin_token_headers: dict):
    cat = Category(name="Mais Pedidas", slug="mais-pedidas", is_active=True)
    db_session.add(cat)
    db_session.commit()

    p1 = Product(title="Pizza Dinosaurus Rex", price=Decimal("60.00"), category_id=cat.id, is_active=True, is_featured=True)
    p2 = Product(title="Pizza Pterodáctilo", price=Decimal("50.00"), category_id=cat.id, is_active=True, is_featured=False)
    db_session.add_all([p1, p2])
    db_session.commit()

    # Public featured endpoint returns only p1
    r_feat = client.get("/api/v1/products/featured")
    assert r_feat.status_code == 200
    data = r_feat.json()
    assert len(data) == 1
    assert data[0]["title"] == "Pizza Dinosaurus Rex"

    # Admin toggle p2 featured -> True
    r_tog = client.patch(f"/api/v1/products/{p2.id}/toggle-featured", headers=admin_token_headers)
    assert r_tog.status_code == 200
    assert r_tog.json()["is_featured"] is True

    # Now public featured endpoint returns both
    r_feat2 = client.get("/api/v1/products/featured")
    assert len(r_feat2.json()) == 2
