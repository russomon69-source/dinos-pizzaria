from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.models.category import Category
from app.models.delivery import DeliveryZone
from app.models.order import Order
from app.models.product import Product
from app.services.order_service import OrderCalculationService
from app.services.whatsapp_service import WhatsAppService


@pytest.fixture
def pizza_catalog(db_session):
    cat_salgadas = Category(name="Pizzas Salgadas", slug="pizzas-salgadas", order=1, is_active=True)
    db_session.add(cat_salgadas)
    db_session.flush()

    p1 = Product(
        title="Pizza Calabresa",
        description="Molho artesanal, mussarela, calabresa fatiada e orégano. Preços: Pequena: R$50,00 / Família: R$65,00 / Gigante: R$75,00.",
        price=Decimal("65.00"),
        is_promo=False,
        is_active=True,
        category_id=cat_salgadas.id,
    )
    p2 = Product(
        title="Pizza 4 Queijos",
        description="Mussarela, provolone, parmesão e catupiry legítimo. Preços: Pequena: R$55,00 / Família: R$70,00 / Gigante: R$80,00.",
        price=Decimal("70.00"),
        is_promo=False,
        is_active=True,
        category_id=cat_salgadas.id,
    )
    p3 = Product(
        title="Coca-Cola 2L",
        description="Refrigerante garrafa 2 litros.",
        price=Decimal("12.00"),
        is_promo=False,
        is_active=True,
        category_id=cat_salgadas.id,
    )
    db_session.add_all([p1, p2, p3])

    zone = DeliveryZone(
        name="Bairro Central",
        fee=Decimal("8.00"),
        estimated_minutes=40,
        is_active=True,
    )
    db_session.add(zone)
    db_session.commit()

    return {"p1": p1, "p2": p2, "p3": p3, "zone": zone}


def test_pizza_options_price_calculation_backend(client: TestClient, pizza_catalog):
    p1 = pizza_catalog["p1"]
    zone = pizza_catalog["zone"]

    # Order with Gigante size (R$ 75,00) + Catupiry crust (R$ 7,50) = R$ 82,50 unit price
    payload = {
        "customer_name": "Rex Dino",
        "customer_phone": "(11) 98765-4321",
        "customer_address": "Rua Jurássica, 100",
        "delivery_type": "delivery",
        "delivery_zone_id": zone.id,
        "payment_method": "pix",
        "items": [
            {
                "item_type": "product",
                "item_id": p1.id,
                "quantity": 2,
                "notes": "Sem cebola",
                "options": {
                    "size": "Gigante",
                    "crust": "Catupiry (+ R$ 7,50)",
                    "flavors": ["Pizza Calabresa", "Pizza 4 Queijos"]
                }
            }
        ]
    }

    res = client.post("/api/v1/orders", json=payload)
    assert res.status_code == 201
    data = res.json()

    order = data["order"]
    # Unit price = 75.00 + 7.50 = 82.50
    # Qty = 2 -> Subtotal = 165.00
    # Delivery fee = 8.00 -> Total = 173.00
    assert Decimal(str(order["subtotal"])) == Decimal("165.00")
    assert Decimal(str(order["delivery_fee"])) == Decimal("8.00")
    assert Decimal(str(order["total_amount"])) == Decimal("173.00")

    item = order["items"][0]
    assert Decimal(str(item["unit_price"])) == Decimal("82.50")
    assert Decimal(str(item["subtotal"])) == Decimal("165.00")
    assert "Gigante" in item["notes"]
    assert "Catupiry" in item["notes"]
    assert "Pizza Calabresa / Pizza 4 Queijos" in item["notes"]


def test_pizza_options_tampered_price_ignored(client: TestClient, pizza_catalog):
    p1 = pizza_catalog["p1"]
    zone = pizza_catalog["zone"]

    # Client attempts to send fake crust and lower base price
    payload = {
        "customer_name": "Hacker Dino",
        "customer_phone": "(11) 98765-4321",
        "customer_address": "Rua Jurássica, 100",
        "delivery_type": "delivery",
        "delivery_zone_id": zone.id,
        "payment_method": "pix",
        "items": [
            {
                "item_type": "product",
                "item_id": p1.id,
                "quantity": 1,
                "options": {
                    "size": "Pequena", # R$ 50.00
                    "crust": "Chocolate (+ R$ 7,50)", # R$ 7.50
                    "flavors": ["Pizza Calabresa"]
                }
            }
        ]
    }

    res = client.post("/api/v1/orders", json=payload)
    assert res.status_code == 201
    order = res.json()["order"]
    # Unit price = 50.00 + 7.50 = 57.50
    # Subtotal = 57.50
    assert Decimal(str(order["subtotal"])) == Decimal("57.50")
    assert Decimal(str(order["total_amount"])) == Decimal("65.50")


def test_whatsapp_message_formats_pizza_options(db_session, pizza_catalog):
    p1 = pizza_catalog["p1"]
    zone = pizza_catalog["zone"]

    calc_service = OrderCalculationService(db_session)
    order_data = {
        "customer_name": "Rex Dino",
        "customer_phone": "(11) 98765-4321",
        "customer_address": "Rua Jurássica, 100",
        "customer_reference": "Portão preto",
        "delivery_type": "delivery",
        "delivery_zone_id": zone.id,
        "payment_method": "pix",
        "order_notes": "Caprichar no molho",
        "items": [
            {
                "item_type": "product",
                "item_id": p1.id,
                "quantity": 1,
                "notes": "Massa bem assada",
                "options": {
                    "size": "Família",
                    "crust": "Cheddar (+ R$ 7,50)",
                    "flavors": ["Pizza Calabresa", "Pizza 4 Queijos"]
                }
            }
        ]
    }

    from app.schemas.order import OrderCreate
    validated_order = OrderCreate(**order_data)
    subtotal, fee, total, items_computed = calc_service.calculate_and_validate(validated_order)

    order = Order(
        customer_name=validated_order.customer_name,
        customer_phone=validated_order.customer_phone,
        customer_address=validated_order.customer_address,
        customer_reference=validated_order.customer_reference,
        delivery_type=validated_order.delivery_type,
        delivery_zone_id=validated_order.delivery_zone_id,
        payment_method=validated_order.payment_method,
        subtotal=subtotal,
        delivery_fee=fee,
        total_amount=total,
        order_notes=validated_order.order_notes,
        status="pending",
    )
    db_session.add(order)
    db_session.flush()

    from app.models.order import OrderItem
    for it in items_computed:
        db_session.add(OrderItem(
            order_id=order.id,
            item_type=it["item_type"],
            product_id=it["product_id"],
            combo_id=it["combo_id"],
            title=it["title"],
            unit_price=it["unit_price"],
            quantity=it["quantity"],
            subtotal=it["subtotal"],
            notes=it["notes"]
        ))
    db_session.commit()
    db_session.refresh(order)

    wa_service = WhatsAppService()
    message = wa_service.format_order_message(order)

    assert "Família" in message
    assert "Cheddar" in message
    assert "Pizza Calabresa / Pizza 4 Queijos" in message
    assert "R$ 72,50" in message or "72.50" in message
