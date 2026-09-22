from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ReviewBase(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=100, description="Nome do cliente")
    rating: int = Field(default=5, ge=1, le=5, description="Nota de 1 a 5 estrelas")
    comment: str = Field(..., min_length=3, max_length=1000, description="Depoimento ou avaliação")
    is_published: bool = Field(default=True, description="Se está visível publicamente no site")


class ReviewCreate(ReviewBase):
    pass


class ReviewUpdate(BaseModel):
    customer_name: Optional[str] = Field(None, min_length=2, max_length=100)
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = Field(None, min_length=3, max_length=1000)
    is_published: Optional[bool] = None


class ReviewOut(ReviewBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
