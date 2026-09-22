from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Nome de usuário do administrador")
    password: str = Field(..., min_length=6, max_length=100, description="Senha do administrador")


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT Bearer token de acesso")
    token_type: str = Field(default="bearer", description="Tipo do token de autenticação")


class AdminOut(BaseModel):
    id: int
    username: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
