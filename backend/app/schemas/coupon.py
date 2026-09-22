from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class CouponBase(BaseModel):
    code: str = Field(..., min_length=2, max_length=50, description="Código do cupom (ex: DINOS10)")
    description: Optional[str] = Field(None, max_length=255, description="Descrição do benefício")
    discount_type: str = Field(default="percentage", description="Tipo de desconto: 'percentage' ou 'fixed'")
    discount_value: Decimal = Field(..., ge=Decimal("0.01"), decimal_places=2, description="Valor ou % de desconto")
    min_subtotal: Decimal = Field(
        default=Decimal("0.00"), ge=Decimal("0.00"), decimal_places=2, description="Subtotal mínimo para aplicar"
    )
    max_discount_amount: Optional[Decimal] = Field(
        None, ge=Decimal("0.01"), decimal_places=2, description="Teto de desconto para cupons percentuais"
    )
    max_uses: Optional[int] = Field(None, ge=1, description="Limite máximo de utilizações")
    is_active: bool = Field(default=True, description="Se o cupom está ativo")
    valid_until: Optional[datetime] = Field(None, description="Data limite de validade")


class CouponCreate(CouponBase):
    pass


class CouponUpdate(BaseModel):
    code: Optional[str] = Field(None, min_length=2, max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    discount_type: Optional[str] = None
    discount_value: Optional[Decimal] = Field(None, ge=Decimal("0.01"), decimal_places=2)
    min_subtotal: Optional[Decimal] = Field(None, ge=Decimal("0.00"), decimal_places=2)
    max_discount_amount: Optional[Decimal] = Field(None, ge=Decimal("0.01"), decimal_places=2)
    max_uses: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None
    valid_until: Optional[datetime] = None


class CouponOut(CouponBase):
    id: int
    used_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CouponValidateIn(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    subtotal: Decimal = Field(..., ge=Decimal("0.00"), decimal_places=2)


class CouponValidateOut(BaseModel):
    valid: bool
    code: str
    discount_amount: Decimal = Decimal("0.00")
    discount_type: str
    discount_value: Decimal
    description: Optional[str] = None
    message: str
