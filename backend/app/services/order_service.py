from datetime import datetime, timezone, timedelta
from decimal import Decimal
import re
from typing import Any, Dict, List, Optional, Tuple, Union
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.combo import Combo
from app.models.coupon import Coupon
from app.models.delivery import DeliveryZone
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.site_content import SiteContent
from app.schemas.order import OrderCreate


def extract_size_prices(description: Optional[str], base_price: Decimal) -> Dict[str, Decimal]:
    prices = {
        "Pequena": base_price,
        "Família": base_price,
        "Familia": base_price,
        "Gigante": base_price,
        "Média": base_price,
        "Media": base_price,
    }
    if not description:
        return prices
    matches = re.findall(
        r"(Pequena|Família|Familia|Média|Media|Gigante)[:\s]*R\$\s*([\d,.]+)",
        description,
        re.IGNORECASE,
    )
    for name, val in matches:
        clean_val = val.replace(".", "").replace(",", ".")
        norm_name = (
            "Família"
            if name.lower() in ("família", "familia")
            else ("Média" if name.lower() in ("média", "media") else name.capitalize())
        )
        try:
            parsed = Decimal(clean_val).quantize(Decimal("0.01"))
            prices[norm_name] = parsed
            if norm_name == "Família":
                prices["Familia"] = parsed
            elif norm_name == "Média":
                prices["Media"] = parsed
        except Exception:
            pass
    return prices


class OrderCalculationResult(tuple):
    subtotal: Decimal
    delivery_fee: Decimal
    total_amount: Decimal
    order_items_data: List[Dict[str, Any]]
    discount_amount: Decimal
    coupon: Optional[Coupon]
    clean_coupon_code: Optional[str]
    fulfillment_time_type: str
    scheduled_for: Optional[datetime]

    def __new__(
        cls,
        subtotal: Decimal,
        delivery_fee: Decimal,
        total_amount: Decimal,
        order_items_data: List[Dict[str, Any]],
        discount_amount: Decimal = Decimal("0.00"),
        coupon: Optional[Coupon] = None,
        clean_coupon_code: Optional[str] = None,
        fulfillment_time_type: str = "asap",
        scheduled_for: Optional[datetime] = None,
    ):
        instance = super().__new__(
            cls, (subtotal, delivery_fee, total_amount, order_items_data)
        )
        instance.subtotal = subtotal
        instance.delivery_fee = delivery_fee
        instance.total_amount = total_amount
        instance.order_items_data = order_items_data
        instance.discount_amount = discount_amount
        instance.coupon = coupon
        instance.clean_coupon_code = clean_coupon_code
        instance.fulfillment_time_type = fulfillment_time_type
        instance.scheduled_for = scheduled_for
        return instance


class OrderCalculationService:
    def __init__(self, db: Session):
        self.db = db

    def calculate_and_validate(
        self, order_in: OrderCreate
    ) -> OrderCalculationResult:
        # 1. Validate items presence
        if not order_in.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O pedido deve conter pelo menos um item.",
            )

        # 2. Store Open/Closed check & Scheduling
        fulfillment_type = order_in.fulfillment_time_type or "asap"
        scheduled_for: Optional[datetime] = None

        store_is_open_row = (
            self.db.query(SiteContent).filter(SiteContent.key == "store_is_open").first()
        )
        is_store_open = True
        if store_is_open_row and store_is_open_row.value.strip().lower() in ("false", "0", "off", "nao", "não"):
            is_store_open = False

        if fulfillment_type == "asap":
            if not is_store_open:
                closed_msg_row = (
                    self.db.query(SiteContent)
                    .filter(SiteContent.key == "store_closed_message")
                    .first()
                )
                closed_msg = (
                    closed_msg_row.value.strip()
                    if closed_msg_row and closed_msg_row.value.strip()
                    else "No momento nossa cozinha está fechada para pedidos imediatos. Você pode agendar seu pedido para o horário de atendimento!"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=closed_msg,
                )
        elif fulfillment_type == "scheduled":
            if not order_in.scheduled_for:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Para pedidos agendados, é obrigatório informar a data e horário de agendamento.",
                )

            sched_utc = order_in.scheduled_for
            now_utc = datetime.now(timezone.utc)
            if sched_utc.tzinfo is None:
                sched_utc = sched_utc.replace(tzinfo=timezone.utc)

            # Minimum 15 minutes ahead and maximum 7 days ahead
            min_allowed = now_utc + timedelta(minutes=14)
            max_allowed = now_utc + timedelta(days=7)

            if sched_utc < min_allowed:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="O horário de agendamento deve ser de pelo menos 15 minutos no futuro.",
                )
            if sched_utc > max_allowed:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="O agendamento não pode exceder o prazo máximo de 7 dias.",
                )
            scheduled_for = sched_utc
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de atendimento inválido: '{fulfillment_type}'. Use 'asap' ou 'scheduled'.",
            )

        # 3. Calculate line items
        order_items_data: List[Dict[str, Any]] = []
        subtotal = Decimal("0.00")

        for item in order_in.items:
            options = getattr(item, "options", None) or {}
            size = options.get("size") if isinstance(options, dict) else None
            crust = options.get("crust") if isinstance(options, dict) else None
            flavors = options.get("flavors") if isinstance(options, dict) else None

            if item.item_type == "product":
                product = (
                    self.db.query(Product)
                    .filter(Product.id == item.item_id)
                    .first()
                )
                if not product or not product.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Produto com ID {item.item_id} não encontrado ou indisponível.",
                    )
                title = product.title
                base_price = Decimal(str(product.price)).quantize(Decimal("0.01"))
                product_fk = product.id
                combo_fk = None

                # Calculate unit price based on options
                size_prices = extract_size_prices(product.description, base_price)
                unit_price = base_price
                if size:
                    norm_size = (
                        "Família"
                        if str(size).lower() in ("família", "familia")
                        else ("Média" if str(size).lower() in ("média", "media") else str(size).capitalize())
                    )
                    if norm_size in size_prices:
                        unit_price = size_prices[norm_size]
                    elif str(size) in size_prices:
                        unit_price = size_prices[str(size)]
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Tamanho de pizza inválido: '{size}'.",
                        )

                crust_price = Decimal("0.00")
                if crust:
                    crust_str = str(crust).lower()
                    if (
                        "catupiry" in crust_str
                        or "cheddar" in crust_str
                        or "chocolate" in crust_str
                        or "7,50" in crust_str
                        or "7.50" in crust_str
                    ):
                        crust_price = Decimal("7.50")

                unit_price = (unit_price + crust_price).quantize(Decimal("0.01"))

            elif item.item_type == "combo":
                combo = (
                    self.db.query(Combo)
                    .filter(Combo.id == item.item_id)
                    .first()
                )
                if not combo or not combo.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Combo com ID {item.item_id} não encontrado ou indisponível.",
                    )
                title = f"Combo: {combo.title}"
                unit_price = Decimal(str(combo.price)).quantize(Decimal("0.01"))
                product_fk = None
                combo_fk = combo.id
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Tipo de item inválido: '{item.item_type}'. Use 'product' ou 'combo'.",
                )

            item_total = (unit_price * item.quantity).quantize(Decimal("0.01"))
            subtotal += item_total

            # Format notes with options
            notes_parts = []
            if size:
                notes_parts.append(f"Tamanho: {size}")
            if crust and "sem borda" not in str(crust).lower():
                notes_parts.append(f"Borda: {crust}")
            if flavors and isinstance(flavors, list) and len(flavors) > 0:
                notes_parts.append(f"Sabores: {' / '.join(flavors)}")
            elif flavors and isinstance(flavors, str) and flavors.strip():
                notes_parts.append(f"Sabores: {flavors.strip()}")

            if item.notes and item.notes.strip():
                notes_parts.append(item.notes.strip())

            formatted_notes = " | ".join(notes_parts) if notes_parts else None

            order_items_data.append(
                {
                    "item_type": item.item_type,
                    "product_id": product_fk,
                    "combo_id": combo_fk,
                    "title": title,
                    "unit_price": unit_price,
                    "quantity": item.quantity,
                    "subtotal": item_total,
                    "total_price": item_total,
                    "notes": formatted_notes,
                }
            )

        # 4. Delivery fee & Minimum Order calculation
        if order_in.delivery_type == "delivery":
            if not order_in.customer_address or not order_in.customer_address.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Endereço de entrega é obrigatório para pedidos do tipo entrega.",
                )
            if not order_in.delivery_zone_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Bairro / Zona de entrega é obrigatório para pedidos do tipo entrega.",
                )
            zone = (
                self.db.query(DeliveryZone)
                .filter(DeliveryZone.id == order_in.delivery_zone_id)
                .first()
            )
            if not zone or not zone.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Bairro / Zona de entrega com ID {order_in.delivery_zone_id} não encontrado ou inativo.",
                )

            # Minimum order check for neighborhood
            if zone.min_order_value is not None and zone.min_order_value > Decimal("0.00"):
                if subtotal < zone.min_order_value:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"O subtotal mínimo para entrega no bairro '{zone.name}' é de "
                            f"R$ {zone.min_order_value:.2f}. Adicione mais itens ao seu pedido."
                        ),
                    )

            delivery_fee = Decimal(str(zone.fee)).quantize(Decimal("0.01"))
        elif order_in.delivery_type == "pickup":
            delivery_fee = Decimal("0.00")
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de entrega inválido: '{order_in.delivery_type}'. Use 'delivery' ou 'pickup'.",
            )

        # 5. Coupon validation and calculation
        discount_amount = Decimal("0.00")
        coupon_obj: Optional[Coupon] = None
        clean_coupon_code: Optional[str] = None

        if order_in.coupon_code and order_in.coupon_code.strip():
            clean_coupon_code = order_in.coupon_code.strip().upper()
            coupon_obj = (
                self.db.query(Coupon)
                .filter(Coupon.code == clean_coupon_code)
                .first()
            )
            if not coupon_obj or not coupon_obj.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cupom inválido ou inativo.",
                )

            now_utc = datetime.now(timezone.utc)
            if coupon_obj.valid_until is not None:
                valid_until_utc = coupon_obj.valid_until
                if valid_until_utc.tzinfo is None:
                    valid_until_utc = valid_until_utc.replace(tzinfo=timezone.utc)
                if now_utc > valid_until_utc:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Este cupom já expirou.",
                    )

            if coupon_obj.max_uses is not None and coupon_obj.used_count >= coupon_obj.max_uses:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Limite de uso deste cupom atingido.",
                )

            if subtotal < coupon_obj.min_subtotal:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Subtotal mínimo de R$ {coupon_obj.min_subtotal:.2f} necessário para aplicar este cupom.",
                )

            if coupon_obj.discount_type == "percentage":
                discount = (subtotal * coupon_obj.discount_value) / Decimal("100.00")
                if coupon_obj.max_discount_amount is not None and coupon_obj.max_discount_amount > 0:
                    discount = min(discount, coupon_obj.max_discount_amount)
            else:  # "fixed"
                discount = coupon_obj.discount_value

            discount = min(discount, subtotal).quantize(Decimal("0.01"))
            discount_amount = discount

        # Final total calculation
        total_amount = max(Decimal("0.00"), subtotal - discount_amount + delivery_fee).quantize(Decimal("0.01"))

        # 6. Cash change validation
        if order_in.payment_method == "cash":
            if order_in.change_for is not None:
                change_for = Decimal(str(order_in.change_for)).quantize(Decimal("0.01"))
                if change_for < total_amount:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"O valor para troco (R$ {change_for:.2f}) não pode ser menor "
                            f"que o valor total do pedido (R$ {total_amount:.2f})."
                        ),
                    )

        return OrderCalculationResult(
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            total_amount=total_amount,
            order_items_data=order_items_data,
            discount_amount=discount_amount,
            coupon=coupon_obj,
            clean_coupon_code=clean_coupon_code,
            fulfillment_time_type=fulfillment_type,
            scheduled_for=scheduled_for,
        )

    def _create_order_instance(self, order_in: OrderCreate) -> Order:
        calc_result = self.calculate_and_validate(order_in)

        change_for: Optional[Decimal] = None
        if order_in.payment_method == "cash" and order_in.change_for is not None:
            change_for = Decimal(str(order_in.change_for)).quantize(Decimal("0.01"))

        delivery_zone_id = order_in.delivery_zone_id if order_in.delivery_type == "delivery" else None

        new_order = Order(
            customer_name=order_in.customer_name.strip(),
            customer_phone=order_in.customer_phone.strip(),
            customer_address=order_in.customer_address.strip() if order_in.customer_address else None,
            customer_reference=order_in.customer_reference.strip() if order_in.customer_reference else None,
            delivery_type=order_in.delivery_type,
            delivery_zone_id=delivery_zone_id,
            delivery_fee=calc_result.delivery_fee,
            subtotal=calc_result.subtotal,
            discount_amount=calc_result.discount_amount,
            coupon_code=calc_result.clean_coupon_code,
            total_amount=calc_result.total_amount,
            fulfillment_time_type=calc_result.fulfillment_time_type,
            scheduled_for=calc_result.scheduled_for,
            payment_method=order_in.payment_method,
            change_for=change_for,
            order_notes=order_in.order_notes.strip() if order_in.order_notes else None,
            status="pending",
            whatsapp_status="pending",
        )

        self.db.add(new_order)
        self.db.flush()

        for item_info in calc_result.order_items_data:
            order_item = OrderItem(
                order_id=new_order.id,
                item_type=item_info.get("item_type", "product"),
                product_id=item_info.get("product_id"),
                combo_id=item_info.get("combo_id"),
                title=item_info["title"],
                unit_price=item_info["unit_price"],
                quantity=item_info["quantity"],
                total_price=item_info["total_price"],
                notes=item_info["notes"],
            )
            self.db.add(order_item)

        # Increment coupon used_count on successful order placement
        if calc_result.coupon:
            calc_result.coupon.used_count += 1

        self.db.commit()
        self.db.refresh(new_order)
        return new_order

    @classmethod
    def create_order(
        cls,
        db: Optional[Session] = None,
        order_in: Optional[OrderCreate] = None,
        *args,
        **kwargs,
    ) -> Order:
        actual_db = db or kwargs.get("db")
        actual_order = order_in or kwargs.get("order_in")
        if isinstance(actual_db, Session) and actual_order:
            service = cls(actual_db)
            return service._create_order_instance(actual_order)
        elif isinstance(db, cls) and actual_order:
            return db._create_order_instance(actual_order)
        raise ValueError("Invalid arguments for create_order")
