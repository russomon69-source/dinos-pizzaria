import os
from decimal import Decimal
from fastapi.testclient import TestClient
from tests.test_uploads import create_test_image


def test_phase2_full_workflow_integration(client: TestClient, admin_token_headers: dict):
    """
    End-to-end integration test for Phase 2:
    - Admin uploads media (WebP generation & static file serving)
    - Admin creates categories, products, combos, and delivery zones
    - Public storefront queries active catalog, daily promo, and delivery zones
    - Admin toggles availability and promo status
    - Public catalog reflects instant availability changes
    """
    created_files = []

    try:
        # 1. Admin uploads product image
        prod_img_bytes = create_test_image(width=800, height=600, color=(255, 69, 0), img_format="PNG")
        upload_resp = client.post(
            "/api/v1/uploads/image",
            files={"file": ("dinos_carnivora.png", prod_img_bytes, "image/png")},
            headers=admin_token_headers,
        )
        assert upload_resp.status_code == 201
        upload_data = upload_resp.json()
        prod_image_url = upload_data["url"]
        created_files.append(os.path.join("static", "uploads", upload_data["filename"]))

        # Verify static media access
        static_resp = client.get(prod_image_url)
        assert static_resp.status_code == 200

        # 2. Admin creates Category
        cat_resp = client.post(
            "/api/v1/categories",
            json={"name": "Pizzas Especiais", "slug": "pizzas-especiais", "order": 1, "is_active": True},
            headers=admin_token_headers,
        )
        assert cat_resp.status_code == 201
        category = cat_resp.json()
        category_id = category["id"]

        # 3. Admin creates Product with uploaded image URL
        prod_resp = client.post(
            "/api/v1/products",
            json={
                "title": "Pizza T-Rex Especial",
                "description": "Molho rústico, mussarela premium, pepperoni vulcânico e bacon crocante.",
                "price": 64.90,
                "image_url": prod_image_url,
                "is_promo": False,
                "is_active": True,
                "category_id": category_id,
            },
            headers=admin_token_headers,
        )
        assert prod_resp.status_code == 201
        product = prod_resp.json()
        product_id = product["id"]
        assert product["image_url"] == prod_image_url
        assert product["category"]["id"] == category_id

        # 4. Admin creates Combo with promo of day
        combo_img_bytes = create_test_image(width=500, height=500, color=(255, 174, 25), img_format="JPEG")
        combo_upload_resp = client.post(
            "/api/v1/uploads/image",
            files={"file": ("combo_jurassico.jpg", combo_img_bytes, "image/jpeg")},
            headers=admin_token_headers,
        )
        assert combo_upload_resp.status_code == 201
        combo_upload_data = combo_upload_resp.json()
        combo_image_url = combo_upload_data["url"]
        created_files.append(os.path.join("static", "uploads", combo_upload_data["filename"]))

        combo_resp = client.post(
            "/api/v1/combos",
            json={
                "title": "Combo Jurássico Família",
                "description": "2 Pizzas Grandes + 1 Refrigerante 2L + Borda Recheada",
                "price": 119.90,
                "image_url": combo_image_url,
                "is_active": True,
                "is_promo_of_day": True,
            },
            headers=admin_token_headers,
        )
        assert combo_resp.status_code == 201
        combo = combo_resp.json()
        combo_id = combo["id"]

        # 5. Admin creates Delivery Zones
        zone_centro = client.post(
            "/api/v1/delivery-zones",
            json={"name": "Centro", "fee": 5.00, "estimated_minutes": 30, "is_active": True},
            headers=admin_token_headers,
        )
        assert zone_centro.status_code == 201

        zone_jardins = client.post(
            "/api/v1/delivery-zones",
            json={"name": "Jardim das Américas", "fee": 12.50, "estimated_minutes": 45, "is_active": True},
            headers=admin_token_headers,
        )
        assert zone_jardins.status_code == 201

        # 6. Public Storefront Queries (no token required)
        # Categories
        pub_cat_resp = client.get("/api/v1/categories")
        assert pub_cat_resp.status_code == 200
        assert len(pub_cat_resp.json()) == 1
        assert pub_cat_resp.json()[0]["name"] == "Pizzas Especiais"

        # Products
        pub_prod_resp = client.get("/api/v1/products")
        assert pub_prod_resp.status_code == 200
        prods = pub_prod_resp.json()
        assert len(prods) == 1
        assert prods[0]["title"] == "Pizza T-Rex Especial"
        assert prods[0]["category"]["slug"] == "pizzas-especiais"

        # Combos and Promo of Day
        pub_combo_resp = client.get("/api/v1/combos")
        assert pub_combo_resp.status_code == 200
        assert len(pub_combo_resp.json()) == 1

        pub_promo_day_resp = client.get("/api/v1/combos/promos")
        assert pub_promo_day_resp.status_code == 200
        promos = pub_promo_day_resp.json()
        assert len(promos) == 1
        assert promos[0]["title"] == "Combo Jurássico Família"

        # Delivery Zones
        pub_zones_resp = client.get("/api/v1/delivery-zones")
        assert pub_zones_resp.status_code == 200
        zones = pub_zones_resp.json()
        assert len(zones) == 2

        # 7. Admin toggles product active status
        toggle_resp = client.patch(
            f"/api/v1/products/{product_id}/toggle-active",
            headers=admin_token_headers,
        )
        assert toggle_resp.status_code == 200
        assert toggle_resp.json()["is_active"] is False

        # Public catalog should now return 0 active products
        pub_prod_resp_after = client.get("/api/v1/products")
        assert pub_prod_resp_after.status_code == 200
        assert len(pub_prod_resp_after.json()) == 0

        # Reactivate product
        client.patch(
            f"/api/v1/products/{product_id}/toggle-active",
            headers=admin_token_headers,
        )

        # Admin toggles promo status
        promo_toggle_resp = client.patch(
            f"/api/v1/products/{product_id}/toggle-promo",
            headers=admin_token_headers,
        )
        assert promo_toggle_resp.status_code == 200
        assert promo_toggle_resp.json()["is_promo"] is True

    finally:
        # Cleanup created files
        for path in created_files:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
