from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.review import Review


def test_public_and_admin_reviews_flow(client: TestClient, db_session: Session, admin_token_headers: dict):
    # Setup initial reviews
    r1 = Review(customer_name="Carlos Silva", rating=5, comment="Melhor pizza de dinossauro!", is_published=True)
    r2 = Review(customer_name="Mariana Souza", rating=4, comment="Massa crocante e muito recheio.", is_published=False)
    db_session.add_all([r1, r2])
    db_session.commit()

    # Public list returns only published reviews
    r_pub = client.get("/api/v1/reviews")
    assert r_pub.status_code == 200
    pub_data = r_pub.json()
    assert len(pub_data) == 1
    assert pub_data[0]["customer_name"] == "Carlos Silva"

    # Admin list requires auth
    assert client.get("/api/v1/reviews/admin-list").status_code in (401, 403)

    # Admin list with auth returns all
    r_admin_list = client.get("/api/v1/reviews/admin-list", headers=admin_token_headers)
    assert r_admin_list.status_code == 200
    assert len(r_admin_list.json()) >= 2

    # Admin Create Review
    new_rev = {
        "customer_name": "Lucas P.",
        "rating": 5,
        "comment": "Entrega super rápida e quentinha.",
        "is_published": True,
    }
    r_create = client.post("/api/v1/reviews", json=new_rev, headers=admin_token_headers)
    assert r_create.status_code == 201
    created_id = r_create.json()["id"]

    # Admin Update Review
    r_up = client.put(f"/api/v1/reviews/{created_id}", json={"rating": 5, "comment": "Editado: Sensacional!"}, headers=admin_token_headers)
    assert r_up.status_code == 200
    assert r_up.json()["comment"] == "Editado: Sensacional!"

    # Admin Toggle Published
    r_tog = client.patch(f"/api/v1/reviews/{created_id}/toggle-published", headers=admin_token_headers)
    assert r_tog.status_code == 200
    assert r_tog.json()["is_published"] is False

    # Admin Delete Review
    r_del = client.delete(f"/api/v1/reviews/{created_id}", headers=admin_token_headers)
    assert r_del.status_code == 204
