import logging
import urllib.parse
from decimal import Decimal
from typing import Tuple
import httpx

from app.core.config import settings
from app.models.order import Order

logger = logging.getLogger(__name__)

PAYMENT_METHOD_LABELS = {
    "pix": "PIX",
    "credit_card": "Cartão de Crédito",
    "debit_card": "Cartão de Débito",
    "cash": "Dinheiro",
}


class WhatsAppService:
    @staticmethod
    def format_order_message(order: Order) -> str:
        """
        Formats a structured, human-readable Brazilian Portuguese Markdown message
        summarizing customer information, items, delivery details, notes, and payment info.
        """
        payment_label = PAYMENT_METHOD_LABELS.get(order.payment_method, order.payment_method)

        lines = [
            f"*🦖 DINOS PIZZARIA - NOVO PEDIDO #{order.id} 🍕*",
            "",
            f"*Cliente:* {order.customer_name}",
            f"*Telefone:* {order.customer_phone}",
        ]

        if getattr(order, "fulfillment_time_type", "asap") == "scheduled" and getattr(order, "scheduled_for", None):
            sched_str = order.scheduled_for.strftime("%d/%m/%Y às %H:%M")
            lines.append(f"*Agendamento:* 🕒 Para {sched_str}")
        else:
            lines.append("*Atendimento:* ⚡ Imediato (O mais rápido possível)")

        if order.delivery_type == "delivery":
            lines.append("*Tipo:* 🛵 Entrega (Delivery)")
            if order.customer_address:
                lines.append(f"*Endereço:* {order.customer_address}")
            if order.customer_reference:
                lines.append(f"*Ponto de Referência:* {order.customer_reference}")
        else:
            lines.append("*Tipo:* 🏪 Retirada no Balcão (Pickup)")

        lines.append("")
        lines.append("*ITENS DO PEDIDO:*")

        for idx, item in enumerate(order.items, start=1):
            item_line = f"{idx}. {item.quantity}x {item.title} - R$ {item.total_price:.2f}"
            lines.append(item_line)
            if item.notes:
                lines.append(f"   _Obs: {item.notes}_")

        lines.append("")
        lines.append(f"*Subtotal:* R$ {order.subtotal:.2f}")

        discount = getattr(order, "discount_amount", Decimal("0.00")) or Decimal("0.00")
        if discount > Decimal("0.00"):
            coupon_code = getattr(order, "coupon_code", None) or "CUPOM"
            lines.append(f"*Cupom ({coupon_code}):* - R$ {discount:.2f}")

        lines.append(f"*Taxa de Entrega:* R$ {order.delivery_fee:.2f}")
        lines.append(f"*Total:* R$ {order.total_amount:.2f}")
        lines.append(f"*Forma de Pagamento:* {payment_label}")

        if order.payment_method == "cash" and order.change_for is not None:
            troco = Decimal(str(order.change_for)) - Decimal(str(order.total_amount))
            lines.append(f"*Troco para:* R$ {order.change_for:.2f} (Levar de troco: R$ {troco:.2f})")

        if order.order_notes:
            lines.append(f"*Observações:* {order.order_notes}")

        lines.append("")
        lines.append("_Pizzas as Legendary as the Dinos!_")

        return "\n".join(lines)

    @staticmethod
    def generate_fallback_url(message: str) -> str:
        """
        Generates a direct wa.me URL with the URL-encoded order message.
        """
        phone_number = settings.WHATSAPP_PHONE_NUMBER
        encoded_message = urllib.parse.quote(message)
        return f"https://wa.me/{phone_number}?text={encoded_message}"

    @classmethod
    async def dispatch_order_message(cls, order: Order) -> Tuple[str, str]:
        """
        Dispatches order notification to WhatsApp via Evolution API v2 if configured.
        Applies a strict timeout (default 3.0s) and automatically falls back to a wa.me URL
        if Evolution API fails, times out, or is unconfigured.

        Returns:
            Tuple[str, str]: (whatsapp_url, whatsapp_status)
            whatsapp_status is either 'sent' or 'fallback_generated'
        """
        message = cls.format_order_message(order)
        whatsapp_url = cls.generate_fallback_url(message)

        # Check if Evolution API configuration is present
        if not (
            settings.EVOLUTION_API_URL
            and settings.EVOLUTION_API_KEY
            and settings.EVOLUTION_INSTANCE_NAME
        ):
            logger.info("Evolution API not configured. Generated wa.me fallback URL.")
            return whatsapp_url, "fallback_generated"

        endpoint = (
            f"{settings.EVOLUTION_API_URL.rstrip('/')}"
            f"/message/sendText/{settings.EVOLUTION_INSTANCE_NAME}"
        )
        headers = {
            "apikey": settings.EVOLUTION_API_KEY,
            "Content-Type": "application/json",
        }
        # Sanitize customer phone or send to store phone number
        target_number = "".join(filter(str.isdigit, str(order.customer_phone)))

        payload = {
            "number": target_number,
            "text": message,
        }

        try:
            async with httpx.AsyncClient(timeout=settings.EVOLUTION_TIMEOUT_SECONDS) as client:
                response = await client.post(endpoint, json=payload, headers=headers)
                if response.status_code in (200, 201):
                    logger.info(f"Evolution API message sent successfully for order #{order.id}")
                    return whatsapp_url, "sent"
                else:
                    logger.warning(
                        f"Evolution API returned HTTP {response.status_code} for order #{order.id}: "
                        f"{response.text}. Using fallback."
                    )
                    return whatsapp_url, "fallback_generated"
        except (httpx.TimeoutException, httpx.RequestError, Exception) as exc:
            logger.warning(
                f"Evolution API dispatch failed for order #{order.id} ({type(exc).__name__}: {exc}). "
                f"Using wa.me fallback."
            )
            return whatsapp_url, "fallback_generated"
