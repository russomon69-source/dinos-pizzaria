import os
import sys
from pathlib import Path

# Ensure backend directory is in sys.path regardless of execution root
_backend_dir = str(Path(__file__).resolve().parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded

import app.models  # Register all models for Base.metadata
from app.api.auth import router as auth_router
from app.api.categories import router as categories_router
from app.api.combos import router as combos_router
from app.api.coupons import router as coupons_router
from app.api.delivery import router as delivery_router
from app.api.orders import router as orders_router
from app.api.products import router as products_router
from app.api.reviews import router as reviews_router
from app.api.uploads import router as uploads_router
from app.api.site_content import router as site_content_router
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.rate_limiter import limiter, rate_limit_exceeded_handler
from app.core.security import hash_password
from app.models.admin import AdminUser

# Ensure static upload directories exist on filesystem
os.makedirs("static/uploads", exist_ok=True)


def run_sqlite_schema_migrations(db_engine):
    """
    Safely adds missing columns to existing SQLite tables when running without Alembic migrations.
    """
    try:
        with db_engine.begin() as conn:
            # Check products table
            res = conn.exec_driver_sql("PRAGMA table_info(products);").fetchall()
            if res:
                cols = [r[1] for r in res]
                if "is_featured" not in cols:
                    conn.exec_driver_sql("ALTER TABLE products ADD COLUMN is_featured BOOLEAN NOT NULL DEFAULT 0;")

            # Check delivery_zones table
            res = conn.exec_driver_sql("PRAGMA table_info(delivery_zones);").fetchall()
            if res:
                cols = [r[1] for r in res]
                if "min_order_value" not in cols:
                    conn.exec_driver_sql("ALTER TABLE delivery_zones ADD COLUMN min_order_value NUMERIC(10, 2) NOT NULL DEFAULT 0.00;")

            # Check orders table
            res = conn.exec_driver_sql("PRAGMA table_info(orders);").fetchall()
            if res:
                cols = [r[1] for r in res]
                if "fulfillment_time_type" not in cols:
                    conn.exec_driver_sql("ALTER TABLE orders ADD COLUMN fulfillment_time_type VARCHAR(20) NOT NULL DEFAULT 'asap';")
                if "scheduled_for" not in cols:
                    conn.exec_driver_sql("ALTER TABLE orders ADD COLUMN scheduled_for DATETIME NULL;")
                if "coupon_code" not in cols:
                    conn.exec_driver_sql("ALTER TABLE orders ADD COLUMN coupon_code VARCHAR(50) NULL;")
                if "discount_amount" not in cols:
                    conn.exec_driver_sql("ALTER TABLE orders ADD COLUMN discount_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.00;")
    except Exception as exc:
        print(f"[Database Migration Warning] {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager:
    - Creates database tables if they do not exist
    - Runs safe schema migrations for SQLite
    - Ensures static/uploads directory exists
    - Auto-seeds the initial administrative user if admin_users table is empty
    """
    # Startup: Ensure upload directories exist
    os.makedirs("static/uploads", exist_ok=True)

    # Startup: Ensure tables exist
    Base.metadata.create_all(bind=engine)

    # Startup: Ensure SQLite columns exist
    run_sqlite_schema_migrations(engine)

    # Seed default admin user if none exists
    db = SessionLocal()
    try:
        admin_count = db.query(AdminUser).count()
        if admin_count == 0:
            hashed = hash_password(settings.ADMIN_INITIAL_PASSWORD)
            initial_admin = AdminUser(
                username=settings.ADMIN_INITIAL_USERNAME,
                hashed_password=hashed,
                is_active=True,
            )
            db.add(initial_admin)
            db.commit()
    finally:
        db.close()

    yield

    # Shutdown: cleanup if necessary


app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
)

# SlowAPI Rate Limiting State & Error Handling
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Cross-Origin Resource Sharing (CORS) Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security Headers Middleware
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self';"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


app.add_middleware(SecurityHeadersMiddleware)

# Attack / Security Logging Middleware
import logging, time
security_logger = logging.getLogger("dinos.security")
security_logger.setLevel(logging.INFO)
if not security_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [SECURITY] %(message)s"))
    security_logger.addHandler(handler)

class SecurityAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.time()
        try:
            response = await call_next(request)
        except Exception as exc:
            security_logger.warning(f"BLOCKED ATTEMPT path={request.url.path} method={request.method} exception={type(exc).__name__}")
            raise
        duration = time.time() - start
        status = getattr(response, "status_code", 0)
        # Log suspicious patterns (rate limit hits, injection attempts, bad auth)
        if status in (401, 403, 429, 400, 422):
            security_logger.info(f"AUDIT path={request.url.path} method={request.method} status={status} ip={request.client.host if request.client else 'unknown'} duration_ms={duration*1000:.1f}")
        # Explicit suspicious payload detection (basic signatures)
        query = str(request.query_params) if hasattr(request, "query_params") else ""
        body = ""
        try:
            if hasattr(request, "body"):
                body = await request.body()
                if isinstance(body, bytes):
                    body = body.decode("utf-8", errors="ignore")
        except Exception:
            pass
        combined = f"{query} {body}".lower()
        suspicious_patterns = ["' or '", "'; drop", "union select", "script>", "<script", "exec(", "eval(", "../../", "..\\\\", "<img", "onload=", "javascript:"]
        for pat in suspicious_patterns:
            if pat in combined:
                security_logger.warning(f"SUSPICIOUS PAYLOAD pattern='{pat}' path={request.url.path} method={request.method} ip={request.client.host if request.client else 'unknown'}")
                break
        return response

app.add_middleware(SecurityAuditMiddleware)

# Mount Static Files handler for media uploads
app.mount("/static", StaticFiles(directory="static"), name="static")

# API Routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(categories_router, prefix="/api/v1")
app.include_router(products_router, prefix="/api/v1")
app.include_router(combos_router, prefix="/api/v1")
app.include_router(coupons_router, prefix="/api/v1")
app.include_router(delivery_router, prefix="/api/v1")
app.include_router(orders_router, prefix="/api/v1")
app.include_router(reviews_router, prefix="/api/v1")
app.include_router(uploads_router, prefix="/api/v1")
app.include_router(site_content_router, prefix="/api/v1")


@app.get("/api/v1/health", tags=["Health"])
def health_check():
    """Service health check endpoint."""
    return {"status": "ok", "app": settings.APP_NAME}


# Mount static frontend applications (Admin SPA must be mounted strictly before root /)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FRONTEND_ADMIN_DIR = os.path.join(BASE_DIR, "frontend", "admin")
FRONTEND_PUBLIC_DIR = os.path.join(BASE_DIR, "frontend", "public")


@app.get("/admin", include_in_schema=False)
def serve_admin_redirect():
    """Redirect /admin to /admin/ for correct relative assets."""
    return RedirectResponse(url="/admin/")


@app.get("/admin/", include_in_schema=False)
def serve_admin_index():
    """Serve Admin SPA index.html for root admin path."""
    admin_index = (
        os.path.join(FRONTEND_ADMIN_DIR, "index.html")
        if os.path.exists(FRONTEND_ADMIN_DIR)
        else os.path.join("frontend", "admin", "index.html")
    )
    return FileResponse(admin_index, media_type="text/html")


if os.path.exists(FRONTEND_ADMIN_DIR):
    app.mount("/admin", StaticFiles(directory=FRONTEND_ADMIN_DIR, html=True), name="admin_frontend")
elif os.path.exists("frontend/admin"):
    app.mount("/admin", StaticFiles(directory="frontend/admin", html=True), name="admin_frontend")

if os.path.exists(FRONTEND_PUBLIC_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_PUBLIC_DIR, html=True), name="public_frontend")
elif os.path.exists("frontend/public"):
    app.mount("/", StaticFiles(directory="frontend/public", html=True), name="public_frontend")

