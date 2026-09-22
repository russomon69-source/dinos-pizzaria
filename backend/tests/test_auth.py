import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import Base
from app.core.rate_limiter import limiter
from app.core.security import create_access_token, hash_password, verify_password
from app.main import app, lifespan
from app.models.admin import AdminUser


def test_admin_lifespan_seed_initial_user(monkeypatch, test_db_path):
    """Verify application lifespan creates the default admin user if the table is empty."""
    test_db_url = f"sqlite:///{test_db_path}"
    test_eng = create_engine(test_db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_eng)
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_eng)

    # Monkeypatch engine and SessionLocal in main
    monkeypatch.setattr("app.main.engine", test_eng)
    monkeypatch.setattr("app.main.SessionLocal", TestSessionLocal)

    import asyncio

    async def run_lifespan():
        async with lifespan(app):
            pass

    asyncio.run(run_lifespan())

    # Verify admin user was created in database
    db = TestSessionLocal()
    try:
        admin = db.query(AdminUser).filter(AdminUser.username == settings.ADMIN_INITIAL_USERNAME).first()
        assert admin is not None
        assert admin.username == settings.ADMIN_INITIAL_USERNAME
        assert admin.is_active is True
        assert verify_password(settings.ADMIN_INITIAL_PASSWORD, admin.hashed_password) is True
    finally:
        db.close()
        test_eng.dispose()


def test_login_success_returns_token(client, db_session):
    """Verify POST /api/v1/auth/login with valid credentials returns 200 OK and JWT access token."""
    username = "admin_login_test"
    password = "secure_password_123"
    admin = AdminUser(
        username=username,
        hashed_password=hash_password(password),
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 20


def test_login_invalid_password_returns_401(client, db_session):
    """Verify POST /api/v1/auth/login with incorrect password returns 401 Unauthorized."""
    username = "admin_invalid_pw"
    password = "correct_password"
    admin = AdminUser(
        username=username,
        hashed_password=hash_password(password),
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "wrong_password_attempt"},
    )

    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Nome de usuário ou senha incorretos."


def test_login_nonexistent_user_returns_401(client):
    """Verify POST /api/v1/auth/login with nonexistent username returns 401 Unauthorized."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "ghost_user", "password": "any_password_123"},
    )

    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Nome de usuário ou senha incorretos."


def test_login_inactive_user_returns_401(client, db_session):
    """Verify inactive admin user cannot log in and receives 401 Unauthorized."""
    username = "admin_inactive_user"
    password = "some_password"
    admin = AdminUser(
        username=username,
        hashed_password=hash_password(password),
        is_active=False,
    )
    db_session.add(admin)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )

    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Nome de usuário ou senha incorretos."


def test_get_me_with_bearer_token_returns_admin_details(client, db_session):
    """Verify GET /api/v1/auth/me with valid Bearer token returns AdminOut payload."""
    username = "admin_me_test"
    password = "admin_password"
    admin = AdminUser(
        username=username,
        hashed_password=hash_password(password),
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()

    token = create_access_token(data={"sub": username})
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == admin.id
    assert data["username"] == username
    assert data["is_active"] is True
    assert "created_at" in data


def test_get_me_without_token_returns_401_or_403(client):
    """Verify GET /api/v1/auth/me without authorization header is rejected."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code in [401, 403]


def test_get_me_with_invalid_token_returns_401(client):
    """Verify GET /api/v1/auth/me with an invalid token returns 401 Unauthorized."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.fake.token"},
    )
    assert response.status_code == 401


def test_auth_rate_limiting_triggers_429(client, db_session):
    """Verify that > 5 login requests per minute triggers SlowAPI HTTP 429 Too Many Requests."""
    username = "admin_ratelimit"
    password = "some_password"
    admin = AdminUser(
        username=username,
        hashed_password=hash_password(password),
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()

    # Reset limiter storage explicitly
    if hasattr(limiter, "_storage") and hasattr(limiter._storage, "storage"):
        limiter._storage.storage.clear()

    # Send 5 attempts (allowed)
    for _ in range(5):
        res = client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": "wrong_password"},
        )
        assert res.status_code == 401

    # 6th attempt should be rate limited
    limited_res = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "wrong_password"},
    )
    assert limited_res.status_code == 429
    data = limited_res.json()
    assert data["error"] == "rate_limit_exceeded"
    assert "Muitas tentativas de login" in data["detail"]


def test_cors_headers_present(client):
    """Verify CORS middleware adds Access-Control-Allow-Origin for configured origins."""
    origin = "http://localhost:3000"
    response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") in [origin, "*"]


def test_health_check(client):
    """Verify GET /api/v1/health returns healthy status."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == settings.APP_NAME
