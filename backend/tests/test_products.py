from decimal import Decimal
from fastapi import status


def create_sample_category(client, admin_token_headers, name="Pizzas Salgadas", slug="pizzas-salgadas"):
    res = client.post(
        "/api/v1/categories",
        json={"name": name, "slug": slug, "order": 1, "is_active": True},
        headers=admin_token_headers,
    )
    return res.json()["id"]


def test_public_list_products_empty(client):
    response = client.get("/api/v1/products")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_admin_create_product_success(client, admin_token_headers):
    cat_id = create_sample_category(client, admin_token_headers)
    payload = {
        "title": "T-Rex Pepperoni",
        "description": "Molho rústico, muçarela especial, dobro de pepperoni e orégano.",
        "price": "69.90",
        "image_url": "/static/uploads/t-rex.webp",
        "is_promo": False,
        "is_active": True,
        "category_id": cat_id,
    }
    res = client.post("/api/v1/products", json=payload, headers=admin_token_headers)
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert data["title"] == "T-Rex Pepperoni"
    assert data["price"] == "69.90"
    assert data["category_id"] == cat_id
    assert data["category"]["name"] == "Pizzas Salgadas"
    assert "id" in data


def test_create_product_invalid_category(client, admin_token_headers):
    payload = {
        "title": "Bronto Burguer Pizza",
        "price": "55.00",
        "category_id": 99999,
    }
    res = client.post("/api/v1/products", json=payload, headers=admin_token_headers)
    assert res.status_code == status.HTTP_400_BAD_REQUEST


def test_create_product_unauthorized(client, admin_token_headers):
    cat_id = create_sample_category(client, admin_token_headers, name="Massas", slug="massas")
    payload = {
        "title": "Lasagna Dinos",
        "price": "49.90",
        "category_id": cat_id,
    }
    res = client.post("/api/v1/products", json=payload)
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_product_by_id(client, admin_token_headers):
    cat_id = create_sample_category(client, admin_token_headers, name="Bebidas", slug="bebidas-prod")
    create_res = client.post(
        "/api/v1/products",
        json={"title": "Guaraná Antarctica 2L", "price": "14.00", "category_id": cat_id},
        headers=admin_token_headers,
    )
    prod_id = create_res.json()["id"]

    res = client.get(f"/api/v1/products/{prod_id}")
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["title"] == "Guaraná Antarctica 2L"
    assert res.json()["price"] == "14.00"


def test_update_product(client, admin_token_headers):
    cat_id = create_sample_category(client, admin_token_headers, name="Calzones", slug="calzones-prod")
    create_res = client.post(
        "/api/v1/products",
        json={"title": "Calzone Carnívoro", "price": "45.00", "category_id": cat_id},
        headers=admin_token_headers,
    )
    prod_id = create_res.json()["id"]

    update_payload = {"price": "49.90", "title": "Super Calzone Carnívoro"}
    up_res = client.put(f"/api/v1/products/{prod_id}", json=update_payload, headers=admin_token_headers)
    assert up_res.status_code == status.HTTP_200_OK
    assert up_res.json()["price"] == "49.90"
    assert up_res.json()["title"] == "Super Calzone Carnívoro"


def test_toggle_product_active_and_promo(client, admin_token_headers):
    cat_id = create_sample_category(client, admin_token_headers, name="Especiais", slug="especiais-prod")
    create_res = client.post(
        "/api/v1/products",
        json={"title": "Velociraptor 4 Queijos", "price": "64.00", "category_id": cat_id},
        headers=admin_token_headers,
    )
    prod_id = create_res.json()["id"]

    # Toggle promo
    promo_res = client.patch(f"/api/v1/products/{prod_id}/toggle-promo", headers=admin_token_headers)
    assert promo_res.status_code == status.HTTP_200_OK
    assert promo_res.json()["is_promo"] is True

    # Filter by promo in public endpoint
    list_promo = client.get("/api/v1/products?is_promo=true")
    assert any(p["id"] == prod_id for p in list_promo.json())

    # Toggle active
    active_res = client.patch(f"/api/v1/products/{prod_id}/toggle-active", headers=admin_token_headers)
    assert active_res.status_code == status.HTTP_200_OK
    assert active_res.json()["is_active"] is False

    # Inactive product does not appear in public active list
    pub_list = client.get("/api/v1/products?active_only=true")
    assert not any(p["id"] == prod_id for p in pub_list.json())

    # But appears in admin-list
    admin_list = client.get("/api/v1/products/admin-list", headers=admin_token_headers)
    assert any(p["id"] == prod_id for p in admin_list.json())


def test_delete_product(client, admin_token_headers):
    cat_id = create_sample_category(client, admin_token_headers, name="Sobremesas", slug="sobremesas-prod")
    create_res = client.post(
        "/api/v1/products",
        json={"title": "Pizza Vulcão de Chocolate", "price": "52.00", "category_id": cat_id},
        headers=admin_token_headers,
    )
    prod_id = create_res.json()["id"]

    del_res = client.delete(f"/api/v1/products/{prod_id}", headers=admin_token_headers)
    assert del_res.status_code == status.HTTP_204_NO_CONTENT

    get_res = client.get(f"/api/v1/products/{prod_id}")
    assert get_res.status_code == status.HTTP_404_NOT_FOUND
