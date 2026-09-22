from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Custom HTTP 429 Too Many Requests handler returning structured JSON detail
    in Portuguese to inform users of temporary login throttling.
    """
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Muitas tentativas de login. Por favor, aguarde um minuto antes de tentar novamente.",
            "error": "rate_limit_exceeded",
        },
    )
