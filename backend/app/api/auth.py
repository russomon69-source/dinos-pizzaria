from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limiter import limiter
from app.core.security import create_access_token, get_current_admin, verify_password
from app.models.admin import AdminUser
from app.schemas.auth import AdminOut, LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(
    request: Request,
    credentials: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate administrative credentials and issue a signed PyJWT Bearer token.
    Throttled at 5 requests/minute per client IP to prevent brute-force attacks.
    """
    admin = (
        db.query(AdminUser)
        .filter(AdminUser.username == credentials.username, AdminUser.is_active == True)  # noqa: E712
        .first()
    )

    if not admin or not verify_password(credentials.password, admin.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nome de usuário ou senha incorretos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": admin.username})
    return TokenResponse(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=AdminOut)
def get_me(
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminOut:
    """
    Retrieve authenticated administrative user profile details using the Bearer token.
    """
    return current_admin
