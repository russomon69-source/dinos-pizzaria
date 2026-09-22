from fastapi import status


def test_public_list_delivery_zones_empty(client):
    response = client.get("/api/v1/delivery-zones")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_admin_create_delivery_zone_success(client, admin_token_headers):
    payload = {
        "name": "Centro",
        "fee": "5.00",
        "estimated_minutes": 35,
        "is_active": True,
    }
    res = client.post("/api/v1/delivery-zones", json=payload, headers=admin_token_headers)
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert data["name"] == "Centro"
    assert data["fee"] == "5.00"
    assert data["estimated_minutes"] == 35
    assert data["is_active"] is True
    assert "id" in data


def test_create_delivery_zone_duplicate_rejected(client, admin_token_headers):
    payload = {
        "name": "Jardim América",
        "fee": "7.50",
    }
    r1 = client.post("/api/v1/delivery-zones", json=payload, headers=admin_token_headers)
    assert r1.status_code == status.HTTP_201_CREATED

    r2 = client.post("/api/v1/delivery-zones", json=payload, headers=admin_token_headers)
    assert r2.status_code == status.HTTP_400_BAD_REQUEST


def test_create_delivery_zone_unauthorized(client):
    payload = {
        "name": "Vila Nova",
        "fee": "6.00",
    }
    res = client.post("/api/v1/delivery-zones", json=payload)
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


def test_update_delivery_zone(client, admin_token_headers):
    create_res = client.post(
        "/api/v1/delivery-zones",
        json={"name": "Bela Vista", "fee": "8.00", "estimated_minutes": 45},
        headers=admin_token_headers,
    )
    zone_id = create_res.json()["id"]

    update_payload = {"fee": "9.50", "estimated_minutes": 40}
    up_res = client.put(f"/api/v1/delivery-zones/{zone_id}", json=update_payload, headers=admin_token_headers)
    assert up_res.status_code == status.HTTP_200_OK
    assert up_res.json()["fee"] == "9.50"
    assert up_res.json()["estimated_minutes"] == 40


def test_toggle_delivery_zone_active(client, admin_token_headers):
    create_res = client.post(
        "/api/v1/delivery-zones",
        json={"name": "Zona Rural", "fee": "20.00"},
        headers=admin_token_headers,
    )
    zone_id = create_res.json()["id"]

    toggle_res = client.patch(f"/api/v1/delivery-zones/{zone_id}/toggle-active", headers=admin_token_headers)
    assert toggle_res.status_code == status.HTTP_200_OK
    assert toggle_res.json()["is_active"] is False

    # Inactive zone does not appear in public active list
    pub_list = client.get("/api/v1/delivery-zones?active_only=true")
    assert not any(z["id"] == zone_id for z in pub_list.json())

    # Appears in admin list
    admin_list = client.get("/api/v1/delivery-zones/admin-list", headers=admin_token_headers)
    assert any(z["id"] == zone_id for z in admin_list.json())


def test_delete_delivery_zone(client, admin_token_headers):
    create_res = client.post(
        "/api/v1/delivery-zones",
        json={"name": "Zona Desativada", "fee": "10.00"},
        headers=admin_token_headers,
    )
    zone_id = create_res.json()["id"]

    del_res = client.delete(f"/api/v1/delivery-zones/{zone_id}", headers=admin_token_headers)
    assert del_res.status_code == status.HTTP_204_NO_CONTENT

    get_res = client.get(f"/api/v1/delivery-zones/{zone_id}")
    assert get_res.status_code == status.HTTP_404_NOT_FOUND
