import os
import sqlite3
import tempfile
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import app.models  # Ensure all models are registered with Base.metadata
from app.core.database import Base, get_db, set_sqlite_pragma
from app.core.rate_limiter import limiter
from app.core.security import create_access_token, hash_password
from app.models.admin import AdminUser
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture(scope="function")
def test_db_path():
    """Create a temporary SQLite database file for testing WAL and pragmas."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    # Cleanup after test
    for f in [path, f"{path}-wal", f"{path}-shm"]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except OSError:
                pass


@pytest.fixture(scope="function")
def test_engine(test_db_path):
    """Create a test SQLAlchemy engine bound to the temporary file with connect pragmas attached."""
    db_url = f"sqlite:///{test_db_path}"
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        echo=False,
    )
    event.listen(engine, "connect", set_sqlite_pragma)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine):
    """Provide a clean transactional SQLAlchemy session for testing."""
    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def reset_limiter_state():
    """Reset SlowAPI rate limiter state between tests."""
    try:
        limiter.reset()
    except Exception:
        pass
    if hasattr(limiter, "_storage") and hasattr(limiter._storage, "storage"):
        try:
            limiter._storage.storage.clear()
        except Exception:
            pass


@pytest.fixture(scope="function")
def client(db_session):
    """Provide a FastAPI TestClient with database session overridden."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_admin(db_session):
    """Create a test admin user in the database."""
    admin = AdminUser(
        username="testadmin",
        hashed_password=hash_password("SuperSecret123!"),
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture(scope="function")
def admin_token_headers(test_admin):
    """Generate authorization headers with a valid Bearer JWT for test_admin."""
    token = create_access_token(data={"sub": test_admin.username})
    return {"Authorization": f"Bearer {token}"}
