def test_public_site_content_defaults(client):
    res = client.get("/api/v1/site-content")
    assert res.status_code == 200
    data = res.json()
    keys = {item["key"]: item["value"] for item in data}

    assert keys["hero_title"] == "Pizza artesanal forjada no fogo lendário"
    assert keys["hero_primary_cta"] == "Ver cardápio e pedir"


def test_admin_updates_site_content(client, admin_token_headers):
    payload = {
        "items": [
            {"key": "hero_title", "value": "Pizza DINOS editada pelo painel"},
            {"key": "hero_primary_cta", "value": "Pedir minha pizza agora"},
        ]
    }

    update_res = client.put("/api/v1/site-content", json=payload, headers=admin_token_headers)
    assert update_res.status_code == 200

    public_res = client.get("/api/v1/site-content")
    keys = {item["key"]: item["value"] for item in public_res.json()}

    assert keys["hero_title"] == "Pizza DINOS editada pelo painel"
    assert keys["hero_primary_cta"] == "Pedir minha pizza agora"


def test_site_content_update_requires_admin(client):
    res = client.put(
        "/api/v1/site-content",
        json={"items": [{"key": "hero_title", "value": "Sem autorização"}]},
    )
    assert res.status_code in (401, 403)
