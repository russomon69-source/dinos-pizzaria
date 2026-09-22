from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.security import (
    create_access_token,
    get_current_admin,
    hash_password,
    verify_password,
)
from app.models.admin import AdminUser


def test_password_hashing_cost_factor_12():
    """Verify password hashing produces bcrypt format with cost factor 12 and verification works."""
    raw_password = "dinos_secure_password_2026"
    hashed = hash_password(raw_password)

    assert hashed.startswith("$2b$12$") or hashed.startswith("$2a$12$")
    assert verify_password(raw_password, hashed) is True
    assert verify_password("wrong_password", hashed) is False
    assert verify_password("", hashed) is False
    assert verify_password(raw_password, "invalid_hash_string") is False


def test_jwt_token_generation_and_expiry():
    """Verify create_access_token includes sub, exp, and iat claims and is decodable."""
    username = "admin_dinos"
    token = create_access_token(data={"sub": username})

    decoded = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
    assert decoded["sub"] == username
    assert "exp" in decoded
    assert "iat" in decoded

    # Expiration is in the future
    exp_dt = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
    now_dt = datetime.now(timezone.utc)
    assert exp_dt > now_dt


def test_jwt_token_expired_rejection(db_session):
    """Verify expired JWT token causes get_current_admin to raise HTTP 401."""
    username = "admin_expired"
    admin = AdminUser(
        username=username,
        hashed_password=hash_password("admin_pass"),
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()

    # Create expired token
    expired_token = create_access_token(
        data={"sub": username},
        expires_delta=timedelta(minutes=-10),
    )

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=expired_token,
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_admin(credentials=credentials, db=db_session)

    assert exc_info.value.status_code == 401
    assert "Credenciais inválidas ou sessão expirada." in exc_info.value.detail


def test_get_current_admin_inactive_user_raises_401(db_session):
    """Verify an inactive admin user cannot authenticate and raises HTTP 401."""
    username = "admin_inactive"
    admin = AdminUser(
        username=username,
        hashed_password=hash_password("admin_pass"),
        is_active=False,
    )
    db_session.add(admin)
    db_session.commit()

    token = create_access_token(data={"sub": username})
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=token,
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_admin(credentials=credentials, db=db_session)

    assert exc_info.value.status_code == 401
    assert "Credenciais inválidas ou sessão expirada." in exc_info.value.detail


def test_get_current_admin_valid_user(db_session):
    """Verify valid token returns active AdminUser instance."""
    username = "admin_valid"
    admin = AdminUser(
        username=username,
        hashed_password=hash_password("admin_pass"),
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()

    token = create_access_token(data={"sub": username})
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=token,
    )

    current_admin = get_current_admin(credentials=credentials, db=db_session)
    assert current_admin.id == admin.id
    assert current_admin.username == username
    assert current_admin.is_active is True


def test_get_current_admin_invalid_token(db_session):
    """Verify tampered or invalid token raises HTTP 401."""
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="invalid.tampered.token",
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_admin(credentials=credentials, db=db_session)

    assert exc_info.value.status_code == 401
