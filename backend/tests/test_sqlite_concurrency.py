import concurrent.futures
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.core.database import get_db
from app.main import app
from app.models.category import Category
from app.models.delivery import DeliveryZone
from app.models.order import Order
from app.models.product import Product


def test_sqlite_concurrent_orders_and_reads_wal_mode(test_engine):
    """
    Threat T-06-05: Concurrency and stress test for SQLite in WAL mode.
    Dispatches 20 concurrent checkout writes and 20 concurrent catalog reads
    across multiple threads to verify zero 'database is locked' errors.
    """
    # Create thread-safe session factory bound to the WAL engine
    testing_session_factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )

    # Seed data with a dedicated session
    seed_session = testing_session_factory()
    cat = Category(name="Pizzas Jurássicas", slug="pizzas-jurassicas", order=1, is_active=True)
    seed_session.add(cat)
    seed_session.flush()

    prod = Product(
        title="Pizza T-Rex Suprema",
        description="Pepperoni e queijo duplo",
        price=Decimal("50.00"),
        is_promo=False,
        is_active=True,
        category_id=cat.id,
    )
    zone = DeliveryZone(name="Centro", fee=Decimal("5.00"), estimated_minutes=30, is_active=True)
    seed_session.add_all([prod, zone])
    seed_session.commit()
    prod_id = prod.id
    zone_id = zone.id
    seed_session.close()

    # Override get_db to provide an independent session per request/thread
    def multi_thread_get_db():
        session = testing_session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = multi_thread_get_db

    num_orders = 20
    num_reads = 20
    results = []

    def run_checkout(idx: int):
        with TestClient(app) as test_client:
            payload = {
                "customer_name": f"Customer {idx}",
                "customer_phone": f"(11) 90000-{idx:04d}",
                "customer_address": f"Rua Concorrência, {idx}",
                "delivery_type": "delivery",
                "delivery_zone_id": zone_id,
                "payment_method": "pix",
                "items": [{"item_type": "product", "item_id": prod_id, "quantity": 1}],
            }
            resp = test_client.post("/api/v1/orders", json=payload)
            return ("order", resp.status_code, resp.json() if resp.status_code == 201 else resp.text)

    def run_catalog_read(idx: int):
        with TestClient(app) as test_client:
            if idx % 2 == 0:
                resp = test_client.get("/api/v1/products?active_only=true")
            else:
                resp = test_client.get("/api/v1/categories?active_only=true")
            return ("read", resp.status_code, len(resp.json()) if resp.status_code == 200 else resp.text)

    tasks = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        for i in range(num_orders):
            tasks.append(executor.submit(run_checkout, i))
        for j in range(num_reads):
            tasks.append(executor.submit(run_catalog_read, j))

        for future in concurrent.futures.as_completed(tasks):
            results.append(future.result())

    app.dependency_overrides.clear()

    # Assert that all 20 orders succeeded with 201
    order_results = [r for r in results if r[0] == "order"]
    assert len(order_results) == num_orders
    for r in order_results:
        assert r[1] == 201, f"Expected 201 for order, got {r[1]}: {r[2]}"

    # Assert that all 20 reads succeeded with 200
    read_results = [r for r in results if r[0] == "read"]
    assert len(read_results) == num_reads
    for r in read_results:
        assert r[1] == 200, f"Expected 200 for read, got {r[1]}: {r[2]}"

    # Verify orders in DB with independent session
    verify_session = testing_session_factory()
    created_orders = verify_session.query(Order).all()
    assert len(created_orders) == num_orders
    order_ids = set(o.id for o in created_orders)
    assert len(order_ids) == num_orders  # All IDs are unique
    verify_session.close()
