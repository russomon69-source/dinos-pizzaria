import io
import os
import uuid
from fastapi import HTTPException, UploadFile, status
from PIL import Image

from app.schemas.upload import ImageUploadResponse

ALLOWED_FORMATS = {"JPEG", "JPG", "PNG", "WEBP", "GIF"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_IMAGE_WIDTH = 1000
WEBP_QUALITY = 82


class ImageService:
    @staticmethod
    async def process_and_save_image(
        file: UploadFile,
        upload_dir: str = "static/uploads",
    ) -> ImageUploadResponse:
        """
        Sanitize, validate magic bytes, resize, convert to WebP, and save image with UUIDv4.
        """
        # Read content and validate max file size
        contents = await file.read()
        if not contents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O arquivo enviado está vazio.",
            )

        if len(contents) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tamanho do arquivo excede o limite máximo de {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB.",
            )

        # Validate magic bytes / image header using Pillow verify()
        try:
            byte_stream = io.BytesIO(contents)
            with Image.open(byte_stream) as img:
                img_format = img.format
                if not img_format or img_format.upper() not in ALLOWED_FORMATS:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Formato de imagem '{img_format}' não suportado. Use JPEG, PNG, WEBP ou GIF.",
                    )
                img.verify()
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O arquivo enviado não é uma imagem válida ou está corrompido.",
            )

        # Re-open stream for actual pixel operations (after verify() modified stream position)
        byte_stream.seek(0)
        try:
            with Image.open(byte_stream) as img:
                # Handle image color modes for clean WebP conversion
                if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                    # Preserve alpha channel
                    processed_img = img.convert("RGBA")
                elif img.mode == "CMYK":
                    processed_img = img.convert("RGB")
                elif img.mode not in ("RGB", "RGBA"):
                    processed_img = img.convert("RGB")
                else:
                    processed_img = img.copy()

                # Resize if width exceeds MAX_IMAGE_WIDTH (maintain aspect ratio)
                orig_width, orig_height = processed_img.size
                if orig_width > MAX_IMAGE_WIDTH:
                    new_width = MAX_IMAGE_WIDTH
                    new_height = int(orig_height * (MAX_IMAGE_WIDTH / orig_width))
                    # Use LANCZOS filter for high quality downscaling
                    resample_filter = getattr(Image.Resampling, "LANCZOS", Image.LANCZOS)
                    processed_img = processed_img.resize((new_width, new_height), resample=resample_filter)
                else:
                    new_width, new_height = orig_width, orig_height

                # Generate secure UUIDv4 filename
                unique_filename = f"{uuid.uuid4().hex}.webp"
                os.makedirs(upload_dir, exist_ok=True)
                dest_path = os.path.join(upload_dir, unique_filename)

                # Save as optimized WebP
                processed_img.save(
                    dest_path,
                    format="WEBP",
                    quality=WEBP_QUALITY,
                    optimize=True,
                )

                file_size = os.path.getsize(dest_path)
                public_url = f"/static/uploads/{unique_filename}"

                return ImageUploadResponse(
                    url=public_url,
                    filename=unique_filename,
                    width=new_width,
                    height=new_height,
                    size_bytes=file_size,
                )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao processar e salvar imagem: {str(e)}",
            )
