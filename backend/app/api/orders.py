from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_admin
from app.core.database import get_db
from app.models.admin import AdminUser
from app.models.order import Order
from app.schemas.order import (
    OrderCheckoutResponse,
    OrderCreate,
    OrderOut,
    OrderStatusUpdate,
    OrderTrackOut,
)
from app.services.order_service import OrderCalculationService
from app.services.whatsapp_service import WhatsAppService

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get(
    "/track",
    response_model=OrderTrackOut,
    summary="Acompanhar status público do pedido por ID e telefone",
)
def track_order_public(
    order_id: int = Query(..., description="ID do pedido"),
    phone: str = Query(..., min_length=4, description="Telefone ou últimos 4 dígitos do telefone"),
    db: Session = Depends(get_db),
):
    """
    Public order tracking endpoint:
    - Verifies order ID and phone matching without leaking sensitive customer personal information
    - Returns current workflow status, item summaries, and delivery/scheduling details
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido não encontrado ou dados não conferem.",
        )

    clean_query_phone = "".join(filter(str.isdigit, str(phone)))
    clean_order_phone = "".join(filter(str.isdigit, str(order.customer_phone)))

    if len(clean_query_phone) < 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe pelo menos os últimos 4 dígitos do telefone cadastrado.",
        )

    if not (clean_order_phone.endswith(clean_query_phone) or clean_query_phone.endswith(clean_order_phone)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido não encontrado ou dados não conferem.",
        )

    items_count = sum(item.quantity for item in order.items)
    items_summary = [f"{item.quantity}x {item.title}" for item in order.items]

    return OrderTrackOut(
        id=order.id,
        customer_name=order.customer_name,
        status=order.status,
        delivery_type=order.delivery_type,
        fulfillment_time_type=getattr(order, "fulfillment_time_type", "asap") or "asap",
        scheduled_for=getattr(order, "scheduled_for", None),
        created_at=order.created_at,
        delivery_fee=order.delivery_fee,
        subtotal=order.subtotal,
        discount_amount=getattr(order, "discount_amount", Decimal("0.00")) or Decimal("0.00"),
        total_amount=order.total_amount,
        items_count=items_count,
        items_summary=items_summary,
    )


@router.post(
    "",
    response_model=OrderCheckoutResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Checkout público (guest) com recálculo autoritativo e disparo WhatsApp",
)
async def create_guest_order(
    order_in: OrderCreate,
    db: Session = Depends(get_db),
):
    """
    Public guest checkout endpoint:
    - Authoritatively recalculates prices from DB
    - Validates items, delivery zone, and payment change rules
    - Dispatches WhatsApp message via Evolution API with wa.me fallback
    - Updates order.whatsapp_status and returns complete checkout response
    """
    order: Order = OrderCalculationService.create_order(db=db, order_in=order_in)

    # Dispatch WhatsApp notification (async Evolution API with resilient wa.me fallback)
    whatsapp_url, whatsapp_status = await WhatsAppService.dispatch_order_message(order)

    # Persist the resulting whatsapp status in DB
    order.whatsapp_status = whatsapp_status
    db.commit()
    db.refresh(order)

    order_out = OrderOut.model_validate(order)
    return OrderCheckoutResponse(
        order=order_out,
        whatsapp_url=whatsapp_url,
        whatsapp_status=whatsapp_status,
    )


@router.get(
    "",
    response_model=List[OrderOut],
    summary="Listar histórico de pedidos (Admin)",
)
def list_orders(
    skip: int = Query(0, ge=0, description="Registros para pular"),
    limit: int = Query(50, ge=1, le=100, description="Limite de registros retornados"),
    status_filter: Optional[str] = Query(
        None, alias="status", description="Filtrar por status do pedido"
    ),
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    """
    Admin-only endpoint to list orders ordered by newest first with optional status filtering.
    """
    query = db.query(Order)
    if status_filter:
        query = query.filter(Order.status == status_filter)

    orders = query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()
    return [OrderOut.model_validate(order) for order in orders]


@router.get(
    "/{order_id}",
    response_model=OrderOut,
    summary="Obter detalhes de um pedido (Admin)",
)
def get_order_details(
    order_id: int,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    """
    Admin-only endpoint to inspect full order details including line items.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido com ID {order_id} não encontrado.",
        )
    return OrderOut.model_validate(order)


@router.patch(
    "/{order_id}/status",
    response_model=OrderOut,
    summary="Atualizar status do pedido no fluxo de produção (Admin)",
)
def update_order_status(
    order_id: int,
    status_in: OrderStatusUpdate,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    """
    Admin-only endpoint to update order workflow status
    (e.g., pending -> confirmed -> in_preparation -> out_for_delivery -> delivered / cancelled).
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido com ID {order_id} não encontrado.",
        )

    order.status = status_in.status
    db.commit()
    db.refresh(order)

    return OrderOut.model_validate(order)
