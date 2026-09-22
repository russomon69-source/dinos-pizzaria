import os
import pytest
from fastapi.testclient import TestClient


def test_root_serves_index_html(client: TestClient):
    """Test that the root route GET / serves the index.html storefront file."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "DINOS Pizzaria" in response.text
    assert "<!DOCTYPE html>" in response.text or "<!doctype html>" in response.text.lower()


def test_css_assets_served(client: TestClient):
    """Test that all modular Design System CSS files are served correctly."""
    css_files = [
        "/css/variables.css",
        "/css/base.css",
        "/css/components.css",
        "/css/responsive.css",
    ]
    for css_path in css_files:
        response = client.get(css_path)
        assert response.status_code == 200, f"Failed to load {css_path}"
        assert "text/css" in response.headers.get("content-type", "")


def test_brand_and_css_tokens(client: TestClient):
    """Test that official DINOS Dark & Neon brand colors and typography are defined in variables.css."""
    response = client.get("/css/variables.css")
    assert response.status_code == 200
    content = response.text

    # DINOS Official Palette
    assert "#121212" in content  # Charred Black
    assert "#FFAE19" in content.upper()  # Neon Gold
    assert "#B86B4B" in content.upper()  # Warm Clay
    assert "#B33927" in content.upper()  # Rustic Red

    # CSS Custom Property names
    assert "--color-bg-primary" in content
    assert "--color-gold" in content
    assert "--color-clay" in content
    assert "--color-rustic-red" in content
    assert "--font-display" in content
    assert "--font-body" in content
    assert "Montserrat" in content
    assert "Inter" in content


def test_brand_vector_svg_assets_served(client: TestClient):
    """Test that the brand mascot vector logo and Jurassic doodle pattern are served correctly."""
    svg_assets = [
        "/images/dinos-logo.svg",
        "/images/dinos-doodle-pattern.svg",
    ]
    for svg_path in svg_assets:
        response = client.get(svg_path)
        assert response.status_code == 200, f"Failed to load {svg_path}"
        assert "image/svg+xml" in response.headers.get("content-type", "")
        assert "<svg" in response.text


def test_api_client_module_syntax(client: TestClient):
    """Test that /js/api.js is served and exports the required API methods."""
    response = client.get("/js/api.js")
    assert response.status_code == 200
    content_type = response.headers.get("content-type", "")
    assert "javascript" in content_type

    content = response.text
    assert "export const api" in content or "export { api }" in content
    assert "getCategories" in content
    assert "getProducts" in content
    assert "getCombos" in content
    assert "getPromoCombos" in content
    assert "getDeliveryZones" in content
    assert "createOrder" in content


def test_api_v1_endpoints_not_conflicted(client: TestClient):
    """Verify that root static mount does not mask or conflict with /api/v1 endpoints."""
    health_resp = client.get("/api/v1/health")
    assert health_resp.status_code == 200
    assert health_resp.json().get("status") == "ok"

    cat_resp = client.get("/api/v1/categories")
    assert cat_resp.status_code == 200
    assert isinstance(cat_resp.json(), list)
