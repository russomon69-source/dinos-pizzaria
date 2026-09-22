from decimal import Decimal
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.database import Base, get_db
from app.models.admin import AdminUser
from app.models.category import Category
from app.models.combo import Combo
from app.models.delivery import DeliveryZone
from app.models.order import Order, OrderItem
from app.models.product import Product


def test_sqlite_engine_wal_mode(test_engine):
    with test_engine.connect() as conn:
        result = conn.execute(text("PRAGMA journal_mode;")).scalar()
        assert result.lower() == "wal"


def test_sqlite_engine_busy_timeout(test_engine):
    with test_engine.connect() as conn:
        result = conn.execute(text("PRAGMA busy_timeout;")).scalar()
        assert result == 5000


def test_sqlite_foreign_keys_enabled(test_engine):
    with test_engine.connect() as conn:
        result = conn.execute(text("PRAGMA foreign_keys;")).scalar()
        assert result == 1


def test_get_db_yields_and_closes():
    db_gen = get_db()
    session = next(db_gen)
    assert session is not None
    # Generator should close cleanly
    with pytest.raises(StopIteration):
        next(db_gen)


def test_all_seven_tables_created():
    expected_tables = {
        "admin_users",
        "categories",
        "products",
        "combos",
        "delivery_zones",
        "orders",
        "order_items",
    }
    assert expected_tables.issubset(set(Base.metadata.tables.keys()))


def test_category_product_relationship(db_session):
    # Create category
    category = Category(
        name="Pizzas Tradicionais",
        slug="pizzas-tradicionais",
        order=1,
        is_active=True,
    )
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)

    # Create product under category
    product = Product(
        title="Pizza Calabresa Dino",
        description="Molho artesanal, mussarela, calabresa fatiada e cebola roxa",
        price=Decimal("49.90"),
        is_promo=False,
        is_active=True,
        category_id=category.id,
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    assert product.category.name == "Pizzas Tradicionais"
    assert len(category.products) == 1
    assert category.products[0].title == "Pizza Calabresa Dino"

    # Test cascade delete: deleting category deletes products
    db_session.delete(category)
    db_session.commit()

    remaining_products = db_session.query(Product).filter(Product.id == product.id).all()
    assert len(remaining_products) == 0


def test_order_order_items_relationship(db_session):
    # Create zone
    zone = DeliveryZone(
        name="Centro",
        fee=Decimal("7.50"),
        estimated_minutes=35,
        is_active=True,
    )
    db_session.add(zone)
    db_session.commit()
    db_session.refresh(zone)

    # Create order with items
    order = Order(
        customer_name="João Silva",
        customer_phone="11999998888",
        customer_address="Rua das Flores, 123",
        customer_reference="Próximo ao parque",
        delivery_type="delivery",
        delivery_zone_id=zone.id,
        delivery_fee=Decimal("7.50"),
        subtotal=Decimal("89.90"),
        total_amount=Decimal("97.40"),
        payment_method="pix",
        status="pending",
        whatsapp_status="pending",
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)

    item1 = OrderItem(
        order_id=order.id,
        title="Pizza T-Rex Especial",
        unit_price=Decimal("59.90"),
        quantity=1,
        total_price=Decimal("59.90"),
        notes="Sem cebola",
    )
    item2 = OrderItem(
        order_id=order.id,
        title="Refrigerante Guaraná 2L",
        unit_price=Decimal("15.00"),
        quantity=2,
        total_price=Decimal("30.00"),
    )
    db_session.add_all([item1, item2])
    db_session.commit()
    db_session.refresh(order)

    assert len(order.items) == 2
    assert sum(item.total_price for item in order.items) == Decimal("89.90")
    assert order.total_amount == order.subtotal + order.delivery_fee

    # Test cascade delete on order
    order_id = order.id
    db_session.delete(order)
    db_session.commit()

    remaining_items = db_session.query(OrderItem).filter(OrderItem.order_id == order_id).all()
    assert len(remaining_items) == 0


def test_delivery_zone_unique_name(db_session):
    zone1 = DeliveryZone(name="Bairro Alto", fee=Decimal("10.00"), is_active=True)
    db_session.add(zone1)
    db_session.commit()

    zone2 = DeliveryZone(name="Bairro Alto", fee=Decimal("12.00"), is_active=True)
    db_session.add(zone2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_admin_user_unique_username(db_session):
    admin1 = AdminUser(
        username="admin_dinos",
        hashed_password="hashed_pwd_example_1234567890",
        is_active=True,
    )
    db_session.add(admin1)
    db_session.commit()

    admin2 = AdminUser(
        username="admin_dinos",
        hashed_password="another_hashed_pwd_1234567890",
        is_active=True,
    )
    db_session.add(admin2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_combo_creation_and_fields(db_session):
    combo = Combo(
        title="Combo Família Jurássica",
        description="2 Pizzas Grandes + 1 Guaraná 2L",
        price=Decimal("99.90"),
        image_url="/uploads/combo-familia.webp",
        is_active=True,
        is_promo_of_day=True,
    )
    db_session.add(combo)
    db_session.commit()
    db_session.refresh(combo)

    assert combo.id is not None
    assert combo.price == Decimal("99.90")
    assert combo.is_promo_of_day is True
    assert combo.created_at is not None
