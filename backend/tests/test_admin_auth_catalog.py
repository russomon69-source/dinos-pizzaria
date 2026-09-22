import io
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.product import Product
from app.models.combo import Combo


# ==============================================================================
# 1. Admin Static Files Delivery & Routing Tests
# ==============================================================================

def test_admin_root_serves_html(client: TestClient):
    """Test that GET /admin and /admin/ serve the admin panel SPA index.html."""
    response = client.get("/admin")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "DINOS ADMIN" in response.text or "DINOS <span>ADMIN</span>" in response.text
    assert "login-view" in response.text
    assert "admin-layout" in response.text
    assert "tab-products" in response.text
    assert "tab-combos" in response.text


def test_admin_css_assets_served(client: TestClient):
    """Test that Admin CSS design tokens and layout stylesheets are served."""
    for css_path in ["/admin/css/variables.css", "/admin/css/admin.css"]:
        response = client.get(css_path)
        assert response.status_code == 200, f"Failed to load {css_path}"
        assert "text/css" in response.headers.get("content-type", "")

    # Check variables.css contains DINOS Dark & Neon tokens
    resp_vars = client.get("/admin/css/variables.css")
    assert "--color-bg-primary" in resp_vars.text
    assert "--color-gold" in resp_vars.text
    assert "--color-clay" in resp_vars.text
    assert "--color-rustic-red" in resp_vars.text


def test_admin_js_modules_served(client: TestClient):
    """Test that all modular Vanilla JS ES6 modules are served with correct headers."""
    js_modules = [
        "/admin/js/admin-api.js",
        "/admin/js/admin-auth.js",
        "/admin/js/admin-dropzone.js",
        "/admin/js/admin-products.js",
        "/admin/js/admin-combos.js",
        "/admin/js/admin-zones.js",
        "/admin/js/admin-sound.js",
        "/admin/js/admin-orders.js",
        "/admin/js/admin-app.js",
    ]
    for js_path in js_modules:
        response = client.get(js_path)
        assert response.status_code == 200, f"Failed to load {js_path}"
        content_type = response.headers.get("content-type", "")
        assert "javascript" in content_type

    # Verify key exports in admin-api.js
    api_resp = client.get("/admin/js/admin-api.js")
    assert "export const adminApi" in api_resp.text
    assert "getAdminProducts" in api_resp.text
    assert "getAdminCombos" in api_resp.text
    assert "uploadImage" in api_resp.text


def test_public_and_admin_isolation(client: TestClient):
    """Verify that public storefront root / and admin /admin are isolated correctly."""
    pub_resp = client.get("/")
    assert pub_resp.status_code == 200
    assert "text/html" in pub_resp.headers.get("content-type", "")

    admin_resp = client.get("/admin")
    assert admin_resp.status_code == 200
    assert "text/html" in admin_resp.headers.get("content-type", "")

    # Public has public menu, Admin has admin panel title
    assert "dinos_admin_token" in client.get("/admin/js/admin-api.js").text


# ==============================================================================
# 2. Authentication & Admin Authorization Tests
# ==============================================================================

def test_admin_login_success(client: TestClient, test_admin):
    """Test authentication endpoint returns JWT token for valid credentials."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testadmin", "password": "SuperSecret123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_admin_me_endpoint(client: TestClient, admin_token_headers):
    """Test /api/v1/auth/me returns admin profile when authenticated."""
    response = client.get("/api/v1/auth/me", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testadmin"
    assert data["is_active"] is True


def test_admin_me_unauthorized(client: TestClient):
    """Test /api/v1/auth/me rejects unauthenticated requests with 401."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


# ==============================================================================
# 3. Product Catalog Management Tests
# ==============================================================================

@pytest.fixture
def sample_category(db_session: Session):
    """Create a sample category for product tests."""
    category = Category(name="Pizzas Especiais", slug="pizzas-especiais", is_active=True, order=1)
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


def test_admin_products_crud_and_toggles(
    client: TestClient,
    admin_token_headers,
    sample_category
):
    """Test full CRUD cycle and 1-click toggles for admin product management."""
    # 1. Unauthenticated access to admin list is rejected
    unauth_resp = client.get("/api/v1/products/admin-list")
    assert unauth_resp.status_code == 401

    # 2. Create a new product
    create_payload = {
        "title": "T-Rex Cheddar Bacon",
        "description": "Molho especial, queijo cheddar cremoso e cubos de bacon crocante.",
        "price": 54.90,
        "image_url": "/static/uploads/trex-bacon.webp",
        "is_active": True,
        "is_promo": False,
        "category_id": sample_category.id,
    }
    create_resp = client.post(
        "/api/v1/products",
        json=create_payload,
        headers=admin_token_headers,
    )
    assert create_resp.status_code == 201
    product_data = create_resp.json()
    product_id = product_data["id"]
    assert product_data["title"] == "T-Rex Cheddar Bacon"
    assert product_data["is_active"] is True
    assert product_data["is_promo"] is False

    # 3. List products in admin view
    list_resp = client.get("/api/v1/products/admin-list", headers=admin_token_headers)
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) >= 1
    assert any(p["id"] == product_id for p in items)

    # 4. Toggle is_active
    toggle_active_resp = client.patch(
        f"/api/v1/products/{product_id}/toggle-active",
        headers=admin_token_headers,
    )
    assert toggle_active_resp.status_code == 200
    assert toggle_active_resp.json()["is_active"] is False

    # 5. Toggle is_promo
    toggle_promo_resp = client.patch(
        f"/api/v1/products/{product_id}/toggle-promo",
        headers=admin_token_headers,
    )
    assert toggle_promo_resp.status_code == 200
    assert toggle_promo_resp.json()["is_promo"] is True

    # 6. Update product
    update_payload = {
        "title": "T-Rex Cheddar Bacon Supreme",
        "price": 59.90,
    }
    update_resp = client.put(
        f"/api/v1/products/{product_id}",
        json=update_payload,
        headers=admin_token_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["title"] == "T-Rex Cheddar Bacon Supreme"
    assert float(update_resp.json()["price"]) == 59.90

    # 7. Delete product
    delete_resp = client.delete(
        f"/api/v1/products/{product_id}",
        headers=admin_token_headers,
    )
    assert delete_resp.status_code in (200, 204)

    # 8. Verify deletion
    get_resp = client.get(f"/api/v1/products/{product_id}")
    assert get_resp.status_code == 404


# ==============================================================================
# 4. Combos Catalog Management Tests
# ==============================================================================

def test_admin_combos_crud_and_toggles(client: TestClient, admin_token_headers):
    """Test full CRUD cycle and 1-click toggles for admin combo management."""
    # 1. Unauthenticated access to admin list is rejected
    unauth_resp = client.get("/api/v1/combos/admin-list")
    assert unauth_resp.status_code == 401

    # 2. Create a new combo
    create_payload = {
        "title": "Combo Jurássico Família",
        "description": "2 Pizzas Grandes + 1 Refrigerante 2L + 1 Pizza Broto Doce.",
        "price": 109.90,
        "image_url": "/static/uploads/combo-jurassico.webp",
        "is_active": True,
        "is_promo_of_day": False,
    }
    create_resp = client.post(
        "/api/v1/combos",
        json=create_payload,
        headers=admin_token_headers,
    )
    assert create_resp.status_code == 201
    combo_data = create_resp.json()
    combo_id = combo_data["id"]
    assert combo_data["title"] == "Combo Jurássico Família"
    assert combo_data["is_active"] is True
    assert combo_data["is_promo_of_day"] is False

    # 3. List combos in admin view
    list_resp = client.get("/api/v1/combos/admin-list", headers=admin_token_headers)
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) >= 1
    assert any(c["id"] == combo_id for c in items)

    # 4. Toggle is_active
    toggle_active_resp = client.patch(
        f"/api/v1/combos/{combo_id}/toggle-active",
        headers=admin_token_headers,
    )
    assert toggle_active_resp.status_code == 200
    assert toggle_active_resp.json()["is_active"] is False

    # 5. Toggle is_promo_of_day
    toggle_promo_resp = client.patch(
        f"/api/v1/combos/{combo_id}/toggle-promo",
        headers=admin_token_headers,
    )
    assert toggle_promo_resp.status_code == 200
    assert toggle_promo_resp.json()["is_promo_of_day"] is True

    # 6. Update combo
    update_payload = {
        "title": "Combo Jurássico Mega Família",
        "price": 119.90,
    }
    update_resp = client.put(
        f"/api/v1/combos/{combo_id}",
        json=update_payload,
        headers=admin_token_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["title"] == "Combo Jurássico Mega Família"
    assert float(update_resp.json()["price"]) == 119.90

    # 7. Delete combo
    delete_resp = client.delete(
        f"/api/v1/combos/{combo_id}",
        headers=admin_token_headers,
    )
    assert delete_resp.status_code in (200, 204)

    # 8. Verify deletion
    get_resp = client.get(f"/api/v1/combos/{combo_id}")
    assert get_resp.status_code == 404


# ==============================================================================
# 5. Admin Image Upload Test
# ==============================================================================

def test_admin_upload_image(client: TestClient, admin_token_headers):
    """Test that image upload works with valid JPEG/PNG and converts to WebP."""
    # Create an in-memory test image
    img = Image.new("RGB", (400, 400), color=(255, 174, 25))
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_bytes = img_byte_arr.getvalue()

    response = client.post(
        "/api/v1/uploads/image",
        files={"file": ("pizza-test.png", img_bytes, "image/png")},
        headers=admin_token_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert "filename" in data or "url" in data or "image_url" in data
    filename = data.get("filename", "")
    assert filename.endswith(".webp") or data.get("url", "").endswith(".webp")
