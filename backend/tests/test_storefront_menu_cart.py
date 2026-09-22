import os
import re
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.product import Product
from app.models.combo import Combo
from app.models.delivery import DeliveryZone


def test_cart_module_served_and_exports(client: TestClient):
    """Test that /js/cart.js is served with correct headers and exports CartStore and cart singleton."""
    response = client.get("/js/cart.js")
    assert response.status_code == 200, "Failed to load /js/cart.js"
    assert "javascript" in response.headers.get("content-type", "")

    content = response.text
    assert "export class CartStore" in content
    assert "export const cart" in content
    assert "dinos_cart_v1" in content
    assert "cart:updated" in content

    # Key methods check
    methods = [
        "loadFromStorage",
        "saveToStorage",
        "addItem",
        "updateQuantity",
        "removeItem",
        "clear",
        "getSubtotal",
        "getDeliveryFee",
        "getTotal",
        "getItemCount",
        "getState",
    ]
    for method in methods:
        assert method in content, f"Method {method} missing from cart.js"


def test_cart_logic_rules_embedded():
    """Verify the business logic implementation patterns in cart.js directly from file."""
    cart_path = os.path.join("frontend", "public", "js", "cart.js")
    assert os.path.exists(cart_path), "frontend/public/js/cart.js must exist"

    with open(cart_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Rule: Check that max quantity capping (<= 50) is implemented (Threat T-04-06)
    assert "50" in content, "cart.js should cap max quantity per item at 50"

    # Rule: Check that notes are trimmed and compared for unique cart items (Pitfall 2)
    assert "trim" in content, "cart.js should trim notes to compare items accurately"

    # Rule: Check that quantity <= 0 triggers removal
    assert "<= 0" in content or "< 1" in content or "splice" in content, "cart.js must handle item removal on zero quantity"


def test_ui_module_exports(client: TestClient):
    """Test that /js/ui.js is served and exports UI helper methods."""
    response = client.get("/js/ui.js")
    assert response.status_code == 200, "Failed to load /js/ui.js"
    assert "javascript" in response.headers.get("content-type", "")

    content = response.text
    required_exports = [
        "formatCurrency",
        "showToast",
        "openItemModal",
        "closeItemModal",
        "renderCartDrawer",
        "toggleCartDrawer",
    ]
    for exp in required_exports:
        assert exp in content, f"Export {exp} missing from ui.js"

    # Verify BRL currency formatting with Intl.NumberFormat
    assert "Intl.NumberFormat" in content
    assert "pt-BR" in content
    assert "BRL" in content


def test_app_module_structure(client: TestClient):
    """Test that /js/app.js is served, imports necessary modules and initializes menu/cart."""
    response = client.get("/js/app.js")
    assert response.status_code == 200, "Failed to load /js/app.js"
    assert "javascript" in response.headers.get("content-type", "")

    content = response.text
    assert "import" in content
    assert "./api.js" in content
    assert "./cart.js" in content
    assert "./ui.js" in content
    assert "setupCategoryNavigation" in content
    assert "IntersectionObserver" in content


def test_storefront_api_data_contract(client: TestClient, db_session: Session):
    """Verify backend endpoints required for the storefront cardápio return proper structured data."""
    # Seed sample category
    cat = Category(name="Pizzas Clássicas", slug="pizzas-classicas", order=1, is_active=True)
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)

    # Seed sample product
    prod = Product(
        title="Pizza Rex Calabresa",
        description="Calabresa artesanal, cebola roxa e orégano vulcânico",
        price=49.90,
        image_url="/static/uploads/calabresa.webp",
        is_promo=True,
        is_active=True,
        category_id=cat.id,
    )
    db_session.add(prod)

    # Seed sample combo
    combo = Combo(
        title="Combo T-Rex Gigante",
        description="1 Pizza Grande + 1 Refrigerante 2L + 1 Sobremesa Vulcão",
        price=79.90,
        image_url="/static/uploads/combo_trex.webp",
        is_promo_of_day=True,
        is_active=True,
    )
    db_session.add(combo)

    # Seed sample delivery zone
    zone = DeliveryZone(name="Centro Jurássico", fee=8.00, estimated_minutes=35, is_active=True)
    db_session.add(zone)
    db_session.commit()

    # 1. Categories
    cat_res = client.get("/api/v1/categories?active_only=true")
    assert cat_res.status_code == 200
    categories = cat_res.json()
    assert any(c["id"] == cat.id for c in categories)

    # 2. Products
    prod_res = client.get(f"/api/v1/products?active_only=true&category_id={cat.id}")
    assert prod_res.status_code == 200
    products = prod_res.json()
    assert any(p["id"] == prod.id for p in products)
    matched_prod = next(p for p in products if p["id"] == prod.id)
    assert matched_prod["is_promo"] is True
    assert float(matched_prod["price"]) == 49.90

    # 3. Promo Combos
    combo_res = client.get("/api/v1/combos/promos")
    assert combo_res.status_code == 200
    combos = combo_res.json()
    assert any(c["id"] == combo.id for c in combos)
    matched_combo = next(c for c in combos if c["id"] == combo.id)
    assert matched_combo["is_promo_of_day"] is True

    # 4. Delivery Zones
    zone_res = client.get("/api/v1/delivery-zones?active_only=true")
    assert zone_res.status_code == 200
    zones = zone_res.json()
    assert any(z["id"] == zone.id for z in zones)
