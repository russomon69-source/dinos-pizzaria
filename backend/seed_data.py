"""
DINOS Pizzaria — Autonomous & Idempotent Database Seeder
Seeds initial categories, products, combos, delivery zones, admin user,
and synthesizes WebP placeholder images using Pillow with the DINOS Dark & Neon brand palette.
"""

import os
import re
import sys
from decimal import Decimal
from typing import Dict

# Ensure backend root is on sys.path when executed directly as a script
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.admin import AdminUser
from app.models.category import Category
from app.models.combo import Combo
from app.models.delivery import DeliveryZone
from app.models.order import OrderItem
from app.models.product import Product
from dinos_source_menu import SOURCE_DINOS_COMBOS, SOURCE_DINOS_PRODUCTS


# Color Palette (DINOS Dark & Neon)
CHARRED_BLACK = (18, 18, 18)
CHARRED_CARD = (26, 26, 26)
NEON_GOLD = (255, 174, 25)
WARM_CLAY = (184, 107, 75)
RUSTIC_RED = (179, 57, 39)
OFF_WHITE = (249, 246, 240)
MUTED_GOLD = (200, 140, 20)


def slugify_filename(value: str, prefix: str = "placeholder") -> str:
    """Create a stable, filesystem-safe WebP placeholder filename."""
    normalized = value.lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    normalized = normalized.strip("_") or "item"
    return f"{prefix}_{normalized[:80]}.webp"


EXAMPLE_PRODUCT_TITLES = [
    "T-Rex Suprema",
    "Velociraptor Spicy",
    "Triceratops 4 Queijos",
    "Brontossauro Costela BBQ",
    "Pterodáctilo Frango & Catupiry",
    "Espinossauro Margherita Especial",
    "Carnotauro Calabresa Especial",
    "Vulcão de Nutella",
    "Meteoro de Chocolate Branco & M&Ms",
    "Dino Banana & Canela",
    "Coca-Cola 2 Litros",
    "Guaraná Antarctica 2L",
    "Premium Bacon Cheese + Geleia de Pimenta",
    "Premium Ninho com Morango",
    "Premium Morango Supremo",
    "Premium Clássica",
    "Premium Calabresa Defumada com Barbecue",
    "Premium Frango Cream Cheese",
    "Premium Costela Bovina com Queijo Coalho",
    "Premium Carne de Sol com Queijo Coalho",
    "Premium Cupim com Bacon",
    "Premium Lombo Canadense com Catupiry",
    "Premium 5 Queijos com Polenguinho",
    "Premium À Moda da Casa",
    "Premium Banana Nevada",
    "Bacon com Ovos",
    "Banana e Canela",
    "Calabresa com Catupiry",
    "Calabresa com Cheddar",
    "Frango com Catupiry",
    "Frango com Cheddar",
    "Gigante + média doce",
    "Moda Brasileira",
    "Pizza Gigante + Coca Cola",
    "Pizza do Chef",
    "Pizza gigante + Pizza doce + Coca Cola",
    "Romeu e Julieta",
]

EXAMPLE_COMBO_TITLES = [
    "Combo Fúria T-Rex",
    "Combo Ninho Raptor",
    "Combo Família Jurássica",
]


def ensure_source_menu_products() -> list[dict]:
    """Transform real source menu products into the internal seed product format."""
    source_products = []
    for item in SOURCE_DINOS_PRODUCTS:
        category_slug = item["category_slug"]
        source_products.append(
            {
                "title": item["title"],
                "description": item["description"],
                "price": Decimal(item["price"]),
                "image_filename": slugify_filename(item["title"], "source_item"),
                "is_promo": item["is_promo"],
                "category_slug": category_slug,
                "source_image_url": item.get("image_url") or None,
            }
        )
    return source_products


def ensure_source_menu_combos() -> list[dict]:
    """Transform real source menu combos into the internal seed combo format."""
    return [
        {
            "title": item["title"],
            "description": item["description"],
            "price": Decimal(item["price"]),
            "image_filename": slugify_filename(item["title"], "source_combo"),
            "is_promo_of_day": item["is_promo_of_day"],
            "source_image_url": item.get("image_url") or None,
        }
        for item in SOURCE_DINOS_COMBOS
    ]


def remove_example_catalog_items(db: Session):
    """Remove fictional sample products/combos previously created by older seeders."""
    example_products = db.query(Product).filter(Product.title.in_(EXAMPLE_PRODUCT_TITLES)).all()
    example_product_ids = [product.id for product in example_products]
    if example_product_ids:
        db.query(OrderItem).filter(OrderItem.product_id.in_(example_product_ids)).update(
            {OrderItem.product_id: None}, synchronize_session=False
        )
    for product in example_products:
        db.delete(product)

    example_combos = db.query(Combo).filter(Combo.title.in_(EXAMPLE_COMBO_TITLES)).all()
    for combo in example_combos:
        db.delete(combo)

    db.commit()
    print(f"  [Cleanup] Removed {len(example_products)} example products and {len(example_combos)} example combos.")


def ensure_placeholder_webp(
    title: str,
    filename: str,
    bg_color=CHARRED_CARD,
    accent_color=NEON_GOLD,
    text_color=OFF_WHITE,
    subtitle: str = "DINOS PIZZARIA",
) -> str:
    """
    Synthesize an optimized WebP image placeholder with DINOS branding
    and save it in static/uploads/ if it does not already exist.
    """
    uploads_dir = os.path.join(PROJECT_ROOT, "static", "uploads")
    os.makedirs(uploads_dir, exist_ok=True)

    file_path = os.path.join(uploads_dir, filename)
    relative_url = f"/static/uploads/{filename}"

    if os.path.exists(file_path):
        return relative_url

    # Create 800x600 canvas
    img = Image.new("RGB", (800, 600), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Outer border
    draw.rectangle([20, 20, 780, 580], outline=accent_color, width=3)
    # Inner subtle border
    draw.rectangle([30, 30, 770, 570], outline=WARM_CLAY, width=1)

    # Decorative corner accents
    corner_len = 40
    # Top-Left
    draw.line([(20, 20), (20 + corner_len, 20)], fill=NEON_GOLD, width=6)
    draw.line([(20, 20), (20, 20 + corner_len)], fill=NEON_GOLD, width=6)
    # Top-Right
    draw.line([(780, 20), (780 - corner_len, 20)], fill=NEON_GOLD, width=6)
    draw.line([(780, 20), (780, 20 + corner_len)], fill=NEON_GOLD, width=6)
    # Bottom-Left
    draw.line([(20, 580), (20 + corner_len, 580)], fill=NEON_GOLD, width=6)
    draw.line([(20, 580), (20, 580 - corner_len)], fill=NEON_GOLD, width=6)
    # Bottom-Right
    draw.line([(780, 580), (780 - corner_len, 580)], fill=NEON_GOLD, width=6)
    draw.line([(780, 580), (780, 580 - corner_len)], fill=NEON_GOLD, width=6)

    # Central Dinosaur / Pizza geometric badge
    draw.ellipse([340, 160, 460, 280], outline=accent_color, width=3, fill=(35, 30, 20))
    # Pizza slice / Claw polygon
    draw.polygon([(400, 190), (370, 250), (430, 250)], fill=accent_color, outline=WARM_CLAY)

    # Subtitle / Brand header text
    try:
        font_brand = ImageFont.truetype("arial.ttf", 22)
        font_title = ImageFont.truetype("arial.ttf", 34)
    except Exception:
        font_brand = ImageFont.load_default()
        font_title = ImageFont.load_default()

    draw.text((400, 320), subtitle, fill=accent_color, font=font_brand, anchor="mm")
    draw.text((400, 380), title, fill=text_color, font=font_title, anchor="mm")

    # Bottom decorative badge
    draw.text((400, 440), "★ SABOR LENDÁRIO & FOGO ARTESANAL ★", fill=WARM_CLAY, font=font_brand, anchor="mm")

    # Save as WebP
    img.save(file_path, format="WEBP", quality=85, optimize=True)
    return relative_url


def seed_categories(db: Session) -> Dict[str, Category]:
    """Seed default product categories if not already present."""
    categories_data = [
        {"name": "Pizzas Salgadas", "slug": "pizzas-salgadas", "order": 1, "is_active": True},
        {"name": "Pizzas Doces", "slug": "pizzas-doces", "order": 2, "is_active": True},
        {"name": "Combos Lendários", "slug": "combos-lendarios", "order": 3, "is_active": True},
        {"name": "Bebidas", "slug": "bebidas", "order": 4, "is_active": True},
        {"name": "Sobremesas", "slug": "sobremesas", "order": 5, "is_active": True},
    ]

    cat_map: Dict[str, Category] = {}
    created_count = 0

    for data in categories_data:
        existing = db.query(Category).filter(Category.slug == data["slug"]).first()
        if not existing:
            cat = Category(**data)
            db.add(cat)
            db.flush()
            cat_map[data["slug"]] = cat
            created_count += 1
        else:
            cat_map[data["slug"]] = existing

    db.commit()
    print(f"  [Categories] {created_count} created, {len(cat_map)} active in database.")
    return cat_map


def seed_products(db: Session, cat_map: Dict[str, Category]):
    """Seed standard DINOS menu items across categories."""
    products_data = ensure_source_menu_products()

    created_count = 0
    for item in products_data:
        existing = db.query(Product).filter(Product.title == item["title"]).first()
        if not existing:
            img_url = ensure_placeholder_webp(
                title=item["title"],
                filename=item["image_filename"],
                bg_color=CHARRED_CARD,
                accent_color=NEON_GOLD if item["is_promo"] else WARM_CLAY,
            )
            prod = Product(
                title=item["title"],
                description=item["description"],
                price=item["price"],
                image_url=item.get("source_image_url") or img_url,
                is_promo=item["is_promo"],
                is_active=True,
                category_id=item.get("category_id") or cat_map[item["category_slug"]].id,
            )
            db.add(prod)
            created_count += 1

    db.commit()
    print(f"  [Products] {created_count} products created ({len(products_data)} total seeded).")


def seed_combos(db: Session):
    """Seed real source menu combos."""
    combos_data = ensure_source_menu_combos()

    created_count = 0
    for item in combos_data:
        existing = db.query(Combo).filter(Combo.title == item["title"]).first()
        if not existing:
            img_url = ensure_placeholder_webp(
                title=item["title"],
                filename=item["image_filename"],
                bg_color=CHARRED_BLACK,
                accent_color=NEON_GOLD if item["is_promo_of_day"] else WARM_CLAY,
                subtitle="COMBO PROMOCIONAL",
            )
            combo = Combo(
                title=item["title"],
                description=item["description"],
                price=item["price"],
                image_url=item.get("source_image_url") or img_url,
                is_active=True,
                is_promo_of_day=item["is_promo_of_day"],
            )
            db.add(combo)
            created_count += 1

    db.commit()
    print(f"  [Combos] {created_count} combos created ({len(combos_data)} total seeded).")


def seed_delivery_zones(db: Session):
    """Seed default neighborhood delivery fee zones."""
    zones_data = [
        {"name": "Centro", "fee": Decimal("6.00"), "estimated_minutes": 35, "is_active": True},
        {"name": "Jardim Jurassic", "fee": Decimal("8.00"), "estimated_minutes": 40, "is_active": True},
        {"name": "Parque dos Dinossauros", "fee": Decimal("10.00"), "estimated_minutes": 45, "is_active": True},
        {"name": "Vila Triássica", "fee": Decimal("12.00"), "estimated_minutes": 50, "is_active": True},
        {"name": "Vale do Cretáceo", "fee": Decimal("15.00"), "estimated_minutes": 60, "is_active": True},
    ]

    created_count = 0
    for item in zones_data:
        existing = db.query(DeliveryZone).filter(DeliveryZone.name == item["name"]).first()
        if not existing:
            zone = DeliveryZone(**item)
            db.add(zone)
            created_count += 1

    db.commit()
    print(f"  [Delivery Zones] {created_count} zones created ({len(zones_data)} total seeded).")


def seed_admin_user(db: Session):
    """Seed default administrator credentials if no admin user exists."""
    username = settings.ADMIN_INITIAL_USERNAME
    existing = db.query(AdminUser).filter(AdminUser.username == username).first()

    if not existing:
        admin = AdminUser(
            username=username,
            hashed_password=hash_password(settings.ADMIN_INITIAL_PASSWORD),
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print(f"  [Admin User] Created default admin user: '{username}'")
    else:
        print(f"  [Admin User] Admin user '{username}' already exists.")


def seed_all():
    """Main execution function to run all seeding procedures idempotently."""
    print("=================================================================")
    print("  🦖 DINOS Pizzaria — Database Initialization & Seeding")
    print("=================================================================")

    # Ensure all tables exist in SQLite
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables verified/created via SQLAlchemy.")

    db = SessionLocal()
    try:
        cat_map = seed_categories(db)
        remove_example_catalog_items(db)
        seed_products(db, cat_map)
        seed_combos(db)
        seed_delivery_zones(db)
        seed_admin_user(db)
        print("\n✨ Seeding completed successfully! Database is ready for production.\n")
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error during database seeding: {e}\n", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_all()
