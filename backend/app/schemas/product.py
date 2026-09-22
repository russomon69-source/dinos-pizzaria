from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.category import CategorySimpleOut


class ProductBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=150, description="Título do produto")
    description: Optional[str] = Field(None, max_length=1000, description="Descrição detalhada do produto")
    price: Decimal = Field(..., ge=Decimal("0.01"), decimal_places=2, description="Preço unitário em Reais (R$)")
    image_url: Optional[str] = Field(None, max_length=255, description="URL pública da imagem WebP")
    is_promo: bool = Field(default=False, description="Indica se é uma promoção")
    is_featured: bool = Field(default=False, description="Indica se é destaque/mais pedidas")
    is_active: bool = Field(default=True, description="Disponibilidade para pedidos")
    category_id: int = Field(..., gt=0, description="ID da categoria vinculada")


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=150)
    description: Optional[str] = Field(None, max_length=1000)
    price: Optional[Decimal] = Field(None, ge=Decimal("0.01"), decimal_places=2)
    image_url: Optional[str] = Field(None, max_length=255)
    is_promo: Optional[bool] = None
    is_featured: Optional[bool] = None
    is_active: Optional[bool] = None
    category_id: Optional[int] = Field(None, gt=0)


class ProductOut(ProductBase):
    id: int
    category: Optional[CategorySimpleOut] = None

    model_config = ConfigDict(from_attributes=True)
