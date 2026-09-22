from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.combo import Combo
from app.models.delivery import DeliveryZone
from app.models.product import Product


@pytest.fixture
def seeded_e2e_catalog(db_session: Session):
    """Seed sample categories, products, combos, and delivery zones for full E2E testing."""
    cat_pizzas = Category(name="Pizzas Salgadas", slug="pizzas-salgadas", order=1, is_active=True)
    cat_bebidas = Category(name="Bebidas", slug="bebidas", order=2, is_active=True)
    db_session.add_all([cat_pizzas, cat_bebidas])
    db_session.flush()

    prod_trex = Product(
        title="Pizza T-Rex Suprema",
        description="Molho rústico, pepperoni vulcânico, mussarela premium e orégano",
        price=Decimal("68.90"),
        image_url="/static/uploads/trex.webp",
        is_promo=True,
        is_active=True,
        category_id=cat_pizzas.id,
    )
    prod_refri = Product(
        title="Refrigerante Dinos 2L",
        description="Refrigerante gelado garrafa 2 litros",
        price=Decimal("12.00"),
        image_url="/static/uploads/refri.webp",
        is_promo=False,
        is_active=True,
        category_id=cat_bebidas.id,
    )
    prod_inactive = Product(
        title="Pizza Fóssil Indisponível",
        description="Esgotada",
        price=Decimal("80.00"),
        image_url="/static/uploads/inactive.webp",
        is_promo=False,
        is_active=False,
        category_id=cat_pizzas.id,
    )
    db_session.add_all([prod_trex, prod_refri, prod_inactive])

    combo_furia = Combo(
        title="Combo Fúria T-Rex",
        description="1 Pizza T-Rex Suprema + 1 Refri 2L + Borda Recheada",
        price=Decimal("79.90"),
        image_url="/static/uploads/combo_furia.webp",
        is_active=True,
        is_promo_of_day=True,
    )
    db_session.add(combo_furia)

    zone_centro = DeliveryZone(
        name="Centro Jurássico",
        fee=Decimal("7.50"),
        estimated_minutes=35,
        is_active=True,
    )
    zone_norte = DeliveryZone(
        name="Vale dos Fósseis",
        fee=Decimal("14.00"),
        estimated_minutes=50,
        is_active=True,
    )
    db_session.add_all([zone_centro, zone_norte])
    db_session.commit()

    return {
        "cat_pizzas": cat_pizzas,
        "cat_bebidas": cat_bebidas,
        "prod_trex": prod_trex,
        "prod_refri": prod_refri,
        "prod_inactive": prod_inactive,
        "combo_furia": combo_furia,
        "zone_centro": zone_centro,
        "zone_norte": zone_norte,
    }


def test_e2e_complete_guest_purchase_flow_delivery(
    client: TestClient, admin_token_headers: dict, seeded_e2e_catalog: dict
):
    """
    Complete E2E life cycle:
    1. Guest explores storefront: categories, active products, promo combos, delivery zones.
    2. Builds cart with multiple products (with notes) and a combo.
    3. Submits delivery order with delivery zone.
    4. Authoritative recalculation verified (subtotal, fee, total, notes).
    5. Admin queries order list and details.
    6. Admin transitions status through full Kanban pipeline:
       pending -> confirmed -> in_preparation -> out_for_delivery -> delivered.
    """
    prod_trex = seeded_e2e_catalog["prod_trex"]
    prod_refri = seeded_e2e_catalog["prod_refri"]
    combo_furia = seeded_e2e_catalog["combo_furia"]
    zone_centro = seeded_e2e_catalog["zone_centro"]

    # 1. Storefront queries
    cat_res = client.get("/api/v1/categories?active_only=true")
    assert cat_res.status_code == 200
    assert len(cat_res.json()) >= 2

    prod_res = client.get("/api/v1/products?active_only=true")
    assert prod_res.status_code == 200
    assert any(p["id"] == prod_trex.id for p in prod_res.json())

    combo_res = client.get("/api/v1/combos/promos")
    assert combo_res.status_code == 200
    assert any(c["id"] == combo_furia.id for c in combo_res.json())

    zone_res = client.get("/api/v1/delivery-zones?active_only=true")
    assert zone_res.status_code == 200
    assert any(z["id"] == zone_centro.id for z in zone_res.json())

    # 2 & 3. Guest submits checkout
    checkout_payload = {
        "customer_name": "Dr. Alan Grant",
        "customer_phone": "(11) 98765-4321",
        "customer_address": "Alameda dos Dinossauros, 100",
        "customer_reference": "Próximo à cerca elétrica",
        "delivery_type": "delivery",
        "delivery_zone_id": zone_centro.id,
        "payment_method": "pix",
        "order_notes": "Entregar na recepção do parque",
        "items": [
            {
                "item_type": "product",
                "item_id": prod_trex.id,
                "quantity": 2,
                "notes": "Massa bem crocante e sem cebola",
            },
            {
                "item_type": "product",
                "item_id": prod_refri.id,
                "quantity": 1,
                "notes": "Bem gelado",
            },
            {
                "item_type": "combo",
                "item_id": combo_furia.id,
                "quantity": 1,
                "notes": "Borda de catupiry",
            },
        ],
    }

    order_resp = client.post("/api/v1/orders", json=checkout_payload)
    assert order_resp.status_code == 201
    order_data = order_resp.json()

    # 4. Authoritative calculations check
    # prod_trex: 68.90 * 2 = 137.80
    # prod_refri: 12.00 * 1 = 12.00
    # combo_furia: 79.90 * 1 = 79.90
    # Subtotal: 137.80 + 12.00 + 79.90 = 229.70
    # Delivery fee: 7.50
    # Total: 237.20
    order = order_data["order"]
    order_id = order["id"]
    assert Decimal(str(order["subtotal"])) == Decimal("229.70")
    assert Decimal(str(order["delivery_fee"])) == Decimal("7.50")
    assert Decimal(str(order["total_amount"])) == Decimal("237.20")
    assert order["status"] == "pending"
    assert len(order["items"]) == 3
    assert order["customer_name"] == "Dr. Alan Grant"
    assert order["customer_address"] == "Alameda dos Dinossauros, 100"
    assert order["order_notes"] == "Entregar na recepção do parque"

    # Verify WhatsApp fallback / url
    assert "whatsapp_url" in order_data
    assert "https://wa.me/" in order_data["whatsapp_url"]
    assert order_data["whatsapp_status"] in ("sent", "fallback_generated")

    # 5. Admin queries order list and details
    list_resp = client.get("/api/v1/orders", headers=admin_token_headers)
    assert list_resp.status_code == 200
    assert any(o["id"] == order_id for o in list_resp.json())

    detail_resp = client.get(f"/api/v1/orders/{order_id}", headers=admin_token_headers)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["id"] == order_id
    assert len(detail["items"]) == 3
    assert any("sem cebola" in str(item.get("notes")) for item in detail["items"])

    # 6. Admin transitions status through Kanban pipeline
    transitions = [
        "confirmed",
        "in_preparation",
        "out_for_delivery",
        "delivered",
    ]
    for next_status in transitions:
        patch_res = client.patch(
            f"/api/v1/orders/{order_id}/status",
            json={"status": next_status},
            headers=admin_token_headers,
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["status"] == next_status


def test_e2e_pickup_order_zero_fee(client: TestClient, seeded_e2e_catalog: dict):
    """Verify pickup orders set delivery_fee=0.00 and delivery_zone_id=None."""
    prod_trex = seeded_e2e_catalog["prod_trex"]

    pickup_payload = {
        "customer_name": "Ellie Sattler",
        "customer_phone": "(11) 97777-6666",
        "delivery_type": "pickup",
        "payment_method": "credit_card",
        "items": [
            {
                "item_type": "product",
                "item_id": prod_trex.id,
                "quantity": 2,
            }
        ],
    }

    res = client.post("/api/v1/orders", json=pickup_payload)
    assert res.status_code == 201
    order = res.json()["order"]

    assert order["delivery_type"] == "pickup"
    assert order["delivery_zone_id"] is None
    assert Decimal(str(order["delivery_fee"])) == Decimal("0.00")
    # 68.90 * 2 = 137.80
    assert Decimal(str(order["subtotal"])) == Decimal("137.80")
    assert Decimal(str(order["total_amount"])) == Decimal("137.80")


def test_e2e_cash_payment_change_rules(client: TestClient, seeded_e2e_catalog: dict):
    """Verify cash payment change rules: change_for >= total succeeds, change_for < total fails with 400."""
    prod_refri = seeded_e2e_catalog["prod_refri"]
    zone_centro = seeded_e2e_catalog["zone_centro"]

    # Subtotal = 12.00, Fee = 7.50 -> Total = 19.50
    # Case 1: Insufficient change_for (R$ 15.00 < R$ 19.50) -> 400
    bad_cash = {
        "customer_name": "Ian Malcolm",
        "customer_phone": "(11) 96666-5555",
        "customer_address": "Rua do Caos, 42",
        "delivery_type": "delivery",
        "delivery_zone_id": zone_centro.id,
        "payment_method": "cash",
        "change_for": 15.00,
        "items": [{"item_type": "product", "item_id": prod_refri.id, "quantity": 1}],
    }
    res_bad = client.post("/api/v1/orders", json=bad_cash)
    assert res_bad.status_code == 400
    assert "não pode ser menor que o valor total" in res_bad.json()["detail"]

    # Case 2: Valid change_for (R$ 50.00 >= R$ 19.50) -> 201
    good_cash = {
        **bad_cash,
        "change_for": 50.00,
    }
    res_good = client.post("/api/v1/orders", json=good_cash)
    assert res_good.status_code == 201
    order = res_good.json()["order"]
    assert Decimal(str(order["change_for"])) == Decimal("50.00")
    assert Decimal(str(order["total_amount"])) == Decimal("19.50")


def test_e2e_order_cancellation_workflow(
    client: TestClient, admin_token_headers: dict, seeded_e2e_catalog: dict
):
    """Verify admin can cancel an order in the Kanban pipeline."""
    prod_refri = seeded_e2e_catalog["prod_refri"]

    res = client.post(
        "/api/v1/orders",
        json={
            "customer_name": "John Hammond",
            "customer_phone": "(11) 95555-4444",
            "delivery_type": "pickup",
            "payment_method": "pix",
            "items": [{"item_type": "product", "item_id": prod_refri.id, "quantity": 1}],
        },
    )
    assert res.status_code == 201
    order_id = res.json()["order"]["id"]

    # Cancel order
    cancel_res = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "cancelled"},
        headers=admin_token_headers,
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"

    # Verify query filtered by status
    filter_res = client.get("/api/v1/orders?status=cancelled", headers=admin_token_headers)
    assert filter_res.status_code == 200
    assert any(o["id"] == order_id for o in filter_res.json())


def test_e2e_invalid_status_transition_rejection(
    client: TestClient, admin_token_headers: dict, seeded_e2e_catalog: dict
):
    """Verify invalid status updates return HTTP 422 Unprocessable Entity."""
    prod_refri = seeded_e2e_catalog["prod_refri"]

    res = client.post(
        "/api/v1/orders",
        json={
            "customer_name": "Dennis Nedry",
            "customer_phone": "(11) 94444-3333",
            "delivery_type": "pickup",
            "payment_method": "cash",
            "change_for": 20.00,
            "items": [{"item_type": "product", "item_id": prod_refri.id, "quantity": 1}],
        },
    )
    assert res.status_code == 201
    order_id = res.json()["order"]["id"]

    # Invalid status attempt
    invalid_patch = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "invalid_status_xyz"},
        headers=admin_token_headers,
    )
    assert invalid_patch.status_code == 422
