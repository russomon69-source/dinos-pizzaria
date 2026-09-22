from pydantic import BaseModel, Field


class ImageUploadResponse(BaseModel):
    url: str = Field(..., description="URL pública estática da imagem WebP gerada")
    filename: str = Field(..., description="Nome único do arquivo salvo (UUIDv4.webp)")
    width: int = Field(..., description="Largura da imagem final em pixels")
    height: int = Field(..., description="Altura da imagem final em pixels")
    size_bytes: int = Field(..., description="Tamanho do arquivo em bytes")
