import pytest
from pydantic import ValidationError
from app.core.config import Settings


def test_settings_default_values():
    settings = Settings()
    assert settings.APP_NAME == "DINOS Pizzaria API"
    assert settings.APP_ENV == "development"
    assert settings.PORT == 8000
    assert settings.DATABASE_URL == "sqlite:///./dinos_pizzaria.db"
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 1440
    assert settings.JWT_ALGORITHM == "HS256"


def test_cors_origins_list_parsing():
    settings = Settings(
        CORS_ORIGINS="http://localhost:8000, http://127.0.0.1:8000 , https://dinospizzaria.com"
    )
    assert settings.cors_origins_list == [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://dinospizzaria.com",
    ]


def test_cors_origins_empty_string():
    settings = Settings(CORS_ORIGINS="")
    assert settings.cors_origins_list == []


def test_secret_key_minimum_length():
    # Valid key with >= 32 chars
    settings = Settings(
        SECRET_KEY="12345678901234567890123456789012"
    )
    assert len(settings.SECRET_KEY) == 32

    # Invalid key with < 32 chars should raise ValidationError
    with pytest.raises(ValidationError):
        Settings(SECRET_KEY="short-secret-key")
