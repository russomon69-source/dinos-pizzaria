from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ComboBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=150, description="Título do combo")
    description: Optional[str] = Field(None, max_length=1000, description="Descrição dos itens inclusos no combo")
    price: Decimal = Field(..., ge=Decimal("0.01"), decimal_places=2, description="Preço promocional do combo em Reais (R$)")
    image_url: Optional[str] = Field(None, max_length=255, description="URL pública da imagem WebP")
    is_active: bool = Field(default=True, description="Disponibilidade do combo")
    is_promo_of_day: bool = Field(default=False, description="Destaque como Promoção do Dia")


class ComboCreate(ComboBase):
    pass


class ComboUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=150)
    description: Optional[str] = Field(None, max_length=1000)
    price: Optional[Decimal] = Field(None, ge=Decimal("0.01"), decimal_places=2)
    image_url: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    is_promo_of_day: Optional[bool] = None


class ComboOut(ComboBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
