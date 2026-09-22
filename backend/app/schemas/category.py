from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Nome da categoria")
    slug: str = Field(..., min_length=2, max_length=100, description="Slug URL amigável")
    order: int = Field(default=0, ge=0, description="Ordem de exibição no cardápio")
    is_active: bool = Field(default=True, description="Status de ativação da categoria")


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    slug: Optional[str] = Field(None, min_length=2, max_length=100)
    order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class CategorySimpleOut(CategoryBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# Forward ref handled in __init__.py or product schema
class CategoryOut(CategoryBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
