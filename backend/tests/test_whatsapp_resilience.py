import urllib.parse
from decimal import Decimal
from unittest.mock import AsyncMock, patch
import pytest
import httpx

from app.core.config import settings
from app.models.order import Order, OrderItem
from app.services.whatsapp_service import WhatsAppService


@pytest.fixture
def sample_delivery_order():
    """Create in-memory Order instance for WhatsApp message tests."""
    order = Order(
        id=42,
        customer_name="Dr. Alan Grant",
        customer_phone="(11) 98765-4321",
        customer_address="Alameda dos Dinossauros, 100",
        customer_reference="Portão 3",
        delivery_type="delivery",
        delivery_zone_id=1,
        delivery_fee=Decimal("8.50"),
        subtotal=Decimal("80.90"),
        total_amount=Decimal("89.40"),
        payment_method="cash",
        change_for=Decimal("100.00"),
        order_notes="Cuidado com os velociraptors no jardim",
        status="pending",
        whatsapp_status="pending",
    )
    item1 = OrderItem(
        id=1,
        order_id=42,
        product_id=10,
        title="Pizza T-Rex Suprema",
        unit_price=Decimal("68.90"),
        quantity=1,
        total_price=Decimal("68.90"),
        notes="Massa fina",
    )
    item2 = OrderItem(
        id=2,
        order_id=42,
        product_id=20,
        title="Refrigerante Dinos 2L",
        unit_price=Decimal("12.00"),
        quantity=1,
        total_price=Decimal("12.00"),
        notes=None,
    )
    order.items = [item1, item2]
    return order


@pytest.fixture
def sample_pickup_order():
    """Create in-memory pickup Order instance for WhatsApp message tests."""
    order = Order(
        id=43,
        customer_name="Ellie Sattler",
        customer_phone="(11) 91234-5678",
        delivery_type="pickup",
        delivery_zone_id=None,
        delivery_fee=Decimal("0.00"),
        subtotal=Decimal("68.90"),
        total_amount=Decimal("68.90"),
        payment_method="pix",
        change_for=None,
        order_notes=None,
        status="pending",
        whatsapp_status="pending",
    )
    item1 = OrderItem(
        id=3,
        order_id=43,
        product_id=10,
        title="Pizza T-Rex Suprema",
        unit_price=Decimal("68.90"),
        quantity=1,
        total_price=Decimal("68.90"),
        notes=None,
    )
    order.items = [item1]
    return order


@pytest.mark.asyncio
async def test_whatsapp_evolution_api_success(sample_delivery_order):
    """Test successful dispatch to Evolution API v2 returning status 'sent'."""
    with patch.object(settings, "EVOLUTION_API_URL", "http://evolution.test"), \
         patch.object(settings, "EVOLUTION_API_KEY", "secret-test-key"), \
         patch.object(settings, "EVOLUTION_INSTANCE_NAME", "dinos-instance"):

        mock_response = httpx.Response(
            status_code=200,
            json={"status": "SUCCESS", "message": "Message sent"},
            request=httpx.Request("POST", "http://evolution.test"),
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            url, status = await WhatsAppService.dispatch_order_message(sample_delivery_order)

            assert status == "sent"
            assert url.startswith("https://wa.me/")
            assert settings.WHATSAPP_PHONE_NUMBER in url
            mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_whatsapp_evolution_api_timeout_failover(sample_delivery_order):
    """Test timeout (>3.0s) gracefully falling back to wa.me with status 'fallback_generated'."""
    with patch.object(settings, "EVOLUTION_API_URL", "http://evolution.test"), \
         patch.object(settings, "EVOLUTION_API_KEY", "secret-test-key"), \
         patch.object(settings, "EVOLUTION_INSTANCE_NAME", "dinos-instance"):

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Connection timed out after 3.0s")

            url, status = await WhatsAppService.dispatch_order_message(sample_delivery_order)

            assert status == "fallback_generated"
            assert url.startswith("https://wa.me/")
            assert settings.WHATSAPP_PHONE_NUMBER in url


@pytest.mark.asyncio
async def test_whatsapp_evolution_api_http_500_failover(sample_delivery_order):
    """Test HTTP 500 server error from Evolution API falling back to wa.me gracefully."""
    with patch.object(settings, "EVOLUTION_API_URL", "http://evolution.test"), \
         patch.object(settings, "EVOLUTION_API_KEY", "secret-test-key"), \
         patch.object(settings, "EVOLUTION_INSTANCE_NAME", "dinos-instance"):

        mock_response = httpx.Response(
            status_code=500,
            text="Internal Server Error from Evolution WhatsApp Gateway",
            request=httpx.Request("POST", "http://evolution.test"),
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            url, status = await WhatsAppService.dispatch_order_message(sample_delivery_order)

            assert status == "fallback_generated"
            assert url.startswith("https://wa.me/")


@pytest.mark.asyncio
async def test_whatsapp_unconfigured_credentials_immediate_fallback(sample_delivery_order):
    """Test immediate wa.me fallback when Evolution API credentials are not configured."""
    with patch.object(settings, "EVOLUTION_API_URL", ""), \
         patch.object(settings, "EVOLUTION_API_KEY", ""), \
         patch.object(settings, "EVOLUTION_INSTANCE_NAME", ""):

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            url, status = await WhatsAppService.dispatch_order_message(sample_delivery_order)

            assert status == "fallback_generated"
            assert url.startswith("https://wa.me/")
            mock_post.assert_not_called()


def test_whatsapp_markdown_formatting_and_url_encoding(sample_delivery_order, sample_pickup_order):
    """Test full Markdown template formatting in Brazilian Portuguese and URL encoding."""
    # 1. Delivery order message formatting
    delivery_msg = WhatsAppService.format_order_message(sample_delivery_order)
    assert "*🦖 DINOS PIZZARIA - NOVO PEDIDO #42 🍕*" in delivery_msg
    assert "*Cliente:* Dr. Alan Grant" in delivery_msg
    assert "*Telefone:* (11) 98765-4321" in delivery_msg
    assert "*Tipo:* 🛵 Entrega (Delivery)" in delivery_msg
    assert "*Endereço:* Alameda dos Dinossauros, 100" in delivery_msg
    assert "*Ponto de Referência:* Portão 3" in delivery_msg
    assert "1. 1x Pizza T-Rex Suprema - R$ 68.90" in delivery_msg
    assert "_Obs: Massa fina_" in delivery_msg
    assert "2. 1x Refrigerante Dinos 2L - R$ 12.00" in delivery_msg
    assert "*Subtotal:* R$ 80.90" in delivery_msg
    assert "*Taxa de Entrega:* R$ 8.50" in delivery_msg
    assert "*Total:* R$ 89.40" in delivery_msg
    assert "*Forma de Pagamento:* Dinheiro" in delivery_msg
    assert "*Troco para:* R$ 100.00 (Levar de troco: R$ 10.60)" in delivery_msg
    assert "*Observações:* Cuidado com os velociraptors no jardim" in delivery_msg

    # Test URL generation
    fallback_url = WhatsAppService.generate_fallback_url(delivery_msg)
    assert fallback_url.startswith(f"https://wa.me/{settings.WHATSAPP_PHONE_NUMBER}?text=")
    parsed = urllib.parse.urlparse(fallback_url)
    qs = urllib.parse.parse_qs(parsed.query)
    assert "text" in qs
    assert "🦖 DINOS PIZZARIA" in qs["text"][0]

    # 2. Pickup order message formatting
    pickup_msg = WhatsAppService.format_order_message(sample_pickup_order)
    assert "*Tipo:* 🏪 Retirada no Balcão (Pickup)" in pickup_msg
    assert "*Taxa de Entrega:* R$ 0.00" in pickup_msg
    assert "*Forma de Pagamento:* PIX" in pickup_msg
    assert "*Troco para:*" not in pickup_msg
