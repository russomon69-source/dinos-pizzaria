from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class DeliveryZoneBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Nome do bairro ou região de entrega")
    fee: Decimal = Field(..., ge=Decimal("0.00"), decimal_places=2, description="Taxa de entrega em Reais (R$)")
    min_order_value: Decimal = Field(
        default=Decimal("0.00"), ge=Decimal("0.00"), decimal_places=2, description="Valor mínimo de pedido para o bairro"
    )
    estimated_minutes: Optional[int] = Field(None, ge=1, le=180, description="Tempo estimado de entrega em minutos")
    is_active: bool = Field(default=True, description="Disponibilidade para entregas")


class DeliveryZoneCreate(DeliveryZoneBase):
    pass


class DeliveryZoneUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    fee: Optional[Decimal] = Field(None, ge=Decimal("0.00"), decimal_places=2)
    min_order_value: Optional[Decimal] = Field(None, ge=Decimal("0.00"), decimal_places=2)
    estimated_minutes: Optional[int] = Field(None, ge=1, le=180)
    is_active: Optional[bool] = None


class DeliveryZoneOut(DeliveryZoneBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
