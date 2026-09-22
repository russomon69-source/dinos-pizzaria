from fastapi import APIRouter, Depends, File, UploadFile, status

from app.core.security import get_current_admin
from app.models.admin import AdminUser
from app.schemas.upload import ImageUploadResponse
from app.services.image_service import ImageService

router = APIRouter(prefix="/uploads", tags=["Uploads"])


@router.post(
    "/image",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload e otimização de imagem para produtos/combos",
)
async def upload_product_image(
    file: UploadFile = File(..., description="Arquivo de imagem (JPEG, PNG, WEBP, GIF)"),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """
    Recebe um arquivo de imagem, valida integridade de bytes, redimensiona para no máximo 1000px,
    converte para formato WebP otimizado (< 150KB) e salva com nome UUIDv4.
    Requer autenticação de administrador.
    """
    return await ImageService.process_and_save_image(file)
