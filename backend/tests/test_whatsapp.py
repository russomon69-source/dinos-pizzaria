from decimal import Decimal
import pytest
import httpx
import respx

from app.core.config import settings
from app.models.order import Order, OrderItem
from app.services.whatsapp_service import WhatsAppService


@pytest.fixture
def sample_delivery_order():
    order = Order(
        id=101,
        customer_name="T-Rex Silva",
        customer_phone="11988887777",
        customer_address="Rua dos Dinossauros, 100",
        customer_reference="Próximo à caverna",
        delivery_type="delivery",
        delivery_zone_id=1,
        delivery_fee=Decimal("8.00"),
        subtotal=Decimal("60.00"),
        total_amount=Decimal("68.00"),
        payment_method="cash",
        change_for=Decimal("100.00"),
        order_notes="Campainha não funciona",
        status="pending",
        whatsapp_status="pending",
    )
    item1 = OrderItem(
        id=1,
        order_id=101,
        product_id=1,
        title="Pizza T-Rex Especial",
        unit_price=Decimal("50.00"),
        quantity=1,
        total_price=Decimal("50.00"),
        notes="sem cebola",
    )
    item2 = OrderItem(
        id=2,
        order_id=101,
        product_id=2,
        title="Guaraná 2L",
        unit_price=Decimal("10.00"),
        quantity=1,
        total_price=Decimal("10.00"),
        notes=None,
    )
    order.items = [item1, item2]
    return order


@pytest.fixture
def sample_pickup_order():
    order = Order(
        id=102,
        customer_name="Raptor Santos",
        customer_phone="11977778888",
        customer_address=None,
        customer_reference=None,
        delivery_type="pickup",
        delivery_zone_id=None,
        delivery_fee=Decimal("0.00"),
        subtotal=Decimal("45.00"),
        total_amount=Decimal("45.00"),
        payment_method="pix",
        change_for=None,
        order_notes=None,
        status="pending",
        whatsapp_status="pending",
    )
    item1 = OrderItem(
        id=3,
        order_id=102,
        product_id=3,
        title="Combo Jurássico",
        unit_price=Decimal("45.00"),
        quantity=1,
        total_price=Decimal("45.00"),
        notes=None,
    )
    order.items = [item1]
    return order


def test_format_order_message_delivery(sample_delivery_order):
    msg = WhatsAppService.format_order_message(sample_delivery_order)

    assert "*🦖 DINOS PIZZARIA - NOVO PEDIDO #101 🍕*" in msg
    assert "*Cliente:* T-Rex Silva" in msg
    assert "*Telefone:* 11988887777" in msg
    assert "*Tipo:* 🛵 Entrega (Delivery)" in msg
    assert "*Endereço:* Rua dos Dinossauros, 100" in msg
    assert "*Ponto de Referência:* Próximo à caverna" in msg
    assert "1. 1x Pizza T-Rex Especial - R$ 50.00" in msg
    assert "_Obs: sem cebola_" in msg
    assert "2. 1x Guaraná 2L - R$ 10.00" in msg
    assert "*Subtotal:* R$ 60.00" in msg
    assert "*Taxa de Entrega:* R$ 8.00" in msg
    assert "*Total:* R$ 68.00" in msg
    assert "*Forma de Pagamento:* Dinheiro" in msg
    assert "*Troco para:* R$ 100.00 (Levar de troco: R$ 32.00)" in msg
    assert "*Observações:* Campainha não funciona" in msg


def test_format_order_message_pickup(sample_pickup_order):
    msg = WhatsAppService.format_order_message(sample_pickup_order)

    assert "*🦖 DINOS PIZZARIA - NOVO PEDIDO #102 🍕*" in msg
    assert "*Cliente:* Raptor Santos" in msg
    assert "*Tipo:* 🏪 Retirada no Balcão (Pickup)" in msg
    assert "*Endereço:*" not in msg
    assert "1. 1x Combo Jurássico - R$ 45.00" in msg
    assert "*Taxa de Entrega:* R$ 0.00" in msg
    assert "*Total:* R$ 45.00" in msg
    assert "*Forma de Pagamento:* PIX" in msg
    assert "*Troco para:*" not in msg


def test_generate_fallback_url(sample_delivery_order):
    msg = WhatsAppService.format_order_message(sample_delivery_order)
    url = WhatsAppService.generate_fallback_url(msg)

    assert url.startswith(f"https://wa.me/{settings.WHATSAPP_PHONE_NUMBER}?text=")
    assert "DINOS%20PIZZARIA" in url or "DINOS+PIZZARIA" in url or "%2A" in url


@pytest.mark.asyncio
async def test_dispatch_order_message_unconfigured(sample_delivery_order, monkeypatch):
    monkeypatch.setattr(settings, "EVOLUTION_API_URL", "")
    monkeypatch.setattr(settings, "EVOLUTION_API_KEY", "")
    monkeypatch.setattr(settings, "EVOLUTION_INSTANCE_NAME", "")

    url, status = await WhatsAppService.dispatch_order_message(sample_delivery_order)

    assert status == "fallback_generated"
    assert url.startswith(f"https://wa.me/{settings.WHATSAPP_PHONE_NUMBER}?text=")


@pytest.mark.asyncio
@respx.mock
async def test_dispatch_order_message_evolution_success(sample_delivery_order, monkeypatch):
    monkeypatch.setattr(settings, "EVOLUTION_API_URL", "https://evolution.example.com")
    monkeypatch.setattr(settings, "EVOLUTION_API_KEY", "test-api-key")
    monkeypatch.setattr(settings, "EVOLUTION_INSTANCE_NAME", "dinos-instance")

    respx.post("https://evolution.example.com/message/sendText/dinos-instance").mock(
        return_value=httpx.Response(200, json={"status": "SUCCESS", "message": "Message sent"})
    )

    url, status = await WhatsAppService.dispatch_order_message(sample_delivery_order)

    assert status == "sent"
    assert url.startswith(f"https://wa.me/{settings.WHATSAPP_PHONE_NUMBER}?text=")


@pytest.mark.asyncio
@respx.mock
async def test_dispatch_order_message_evolution_timeout(sample_delivery_order, monkeypatch):
    monkeypatch.setattr(settings, "EVOLUTION_API_URL", "https://evolution.example.com")
    monkeypatch.setattr(settings, "EVOLUTION_API_KEY", "test-api-key")
    monkeypatch.setattr(settings, "EVOLUTION_INSTANCE_NAME", "dinos-instance")

    respx.post("https://evolution.example.com/message/sendText/dinos-instance").mock(
        side_effect=httpx.TimeoutException("Connection timed out after 3.0 seconds")
    )

    url, status = await WhatsAppService.dispatch_order_message(sample_delivery_order)

    # Should gracefully catch timeout and return fallback_generated
    assert status == "fallback_generated"
    assert url.startswith(f"https://wa.me/{settings.WHATSAPP_PHONE_NUMBER}?text=")


@pytest.mark.asyncio
@respx.mock
async def test_dispatch_order_message_evolution_500_error(sample_delivery_order, monkeypatch):
    monkeypatch.setattr(settings, "EVOLUTION_API_URL", "https://evolution.example.com")
    monkeypatch.setattr(settings, "EVOLUTION_API_KEY", "test-api-key")
    monkeypatch.setattr(settings, "EVOLUTION_INSTANCE_NAME", "dinos-instance")

    respx.post("https://evolution.example.com/message/sendText/dinos-instance").mock(
        return_value=httpx.Response(500, json={"error": "Internal Server Error"})
    )

    url, status = await WhatsAppService.dispatch_order_message(sample_delivery_order)

    assert status == "fallback_generated"
    assert url.startswith(f"https://wa.me/{settings.WHATSAPP_PHONE_NUMBER}?text=")
