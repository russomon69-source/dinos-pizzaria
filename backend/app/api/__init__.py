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

__all__ = [
    "auth_router",
    "categories_router",
    "products_router",
    "combos_router",
    "coupons_router",
    "delivery_router",
    "orders_router",
    "reviews_router",
    "uploads_router",
    "site_content_router",
]
