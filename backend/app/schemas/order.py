from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class OrderItemCreate(BaseModel):
    item_type: Literal["product", "combo"] = Field(
        default="product", description="Tipo do item: 'product' ou 'combo'"
    )
    item_id: int = Field(..., ge=1, description="ID do produto ou combo")
    quantity: int = Field(default=1, ge=1, le=50, description="Quantidade de itens")
    notes: Optional[str] = Field(
        None, max_length=255, description="Observações do item (ex: sem cebola)"
    )
    options: Optional[Dict[str, Any]] = Field(
        default=None, description="Opções customizadas de pizza (tamanho, borda, sabores)"
    )


class OrderItemOut(BaseModel):
    id: int
    order_id: int
    product_id: Optional[int] = None
    combo_id: Optional[int] = None
    item_type: Optional[str] = "product"
    title: str
    unit_price: Decimal = Field(..., decimal_places=2)
    quantity: int
    total_price: Decimal = Field(..., decimal_places=2)
    subtotal: Optional[Decimal] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def populate_subtotal(self) -> "OrderItemOut":
        if self.subtotal is None:
            self.subtotal = self.total_price
        return self


class OrderCreate(BaseModel):
    customer_name: str = Field(
        ..., min_length=2, max_length=100, description="Nome completo do cliente"
    )
    customer_phone: str = Field(
        ..., min_length=8, max_length=20, description="Telefone / WhatsApp do cliente"
    )
    customer_address: Optional[str] = Field(
        None, max_length=255, description="Endereço completo de entrega"
    )
    customer_reference: Optional[str] = Field(
        None, max_length=150, description="Ponto de referência para entrega"
    )
    delivery_type: Literal["delivery", "pickup"] = Field(
        default="delivery", description="Tipo de entrega: 'delivery' ou 'pickup'"
    )
    delivery_zone_id: Optional[int] = Field(
        None, ge=1, description="ID da zona/bairro de entrega (obrigatório se delivery)"
    )
    payment_method: Literal["pix", "credit_card", "debit_card", "cash"] = Field(
        ..., description="Forma de pagamento"
    )
    change_for: Optional[Decimal] = Field(
        None, ge=Decimal("0.00"), decimal_places=2, description="Troco para quanto (se dinheiro)"
    )
    coupon_code: Optional[str] = Field(
        None, max_length=50, description="Código de cupom de desconto opcional"
    )
    fulfillment_time_type: Literal["asap", "scheduled"] = Field(
        default="asap", description="Tipo de horário de atendimento ('asap' ou 'scheduled')"
    )
    scheduled_for: Optional[datetime] = Field(
        None, description="Data e hora agendadas para atendimento"
    )
    order_notes: Optional[str] = Field(
        None, max_length=1000, description="Observações gerais do pedido"
    )
    items: List[OrderItemCreate] = Field(
        ..., min_length=1, description="Lista de itens do pedido"
    )


class OrderOut(BaseModel):
    id: int
    customer_name: str
    customer_phone: str
    customer_address: Optional[str] = None
    customer_reference: Optional[str] = None
    delivery_type: str
    delivery_zone_id: Optional[int] = None
    delivery_fee: Decimal = Field(..., decimal_places=2)
    subtotal: Decimal = Field(..., decimal_places=2)
    discount_amount: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    coupon_code: Optional[str] = None
    total_amount: Decimal = Field(..., decimal_places=2)
    fulfillment_time_type: str = "asap"
    scheduled_for: Optional[datetime] = None
    payment_method: str
    change_for: Optional[Decimal] = None
    order_notes: Optional[str] = None
    status: str
    whatsapp_status: str
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemOut]

    model_config = ConfigDict(from_attributes=True)


class OrderTrackOut(BaseModel):
    id: int
    customer_name: str
    status: str
    delivery_type: str
    fulfillment_time_type: str
    scheduled_for: Optional[datetime] = None
    created_at: datetime
    delivery_fee: Decimal = Field(..., decimal_places=2)
    subtotal: Decimal = Field(..., decimal_places=2)
    discount_amount: Decimal = Field(..., decimal_places=2)
    total_amount: Decimal = Field(..., decimal_places=2)
    items_count: int
    items_summary: List[str]

    model_config = ConfigDict(from_attributes=True)


class OrderStatusUpdate(BaseModel):
    status: Literal[
        "pending",
        "confirmed",
        "in_preparation",
        "out_for_delivery",
        "delivered",
        "cancelled",
    ] = Field(..., description="Novo status do pedido")


class OrderCheckoutResponse(BaseModel):
    order: OrderOut
    whatsapp_url: str
    whatsapp_status: str
