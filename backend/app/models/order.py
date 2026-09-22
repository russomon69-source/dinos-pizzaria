from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    customer_name: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    customer_address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    customer_reference: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    delivery_type: Mapped[str] = mapped_column(String(20), default="delivery", nullable=False)
    delivery_zone_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("delivery_zones.id"), nullable=True
    )
    delivery_fee: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), nullable=False
    )
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), nullable=False
    )
    coupon_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    fulfillment_time_type: Mapped[str] = mapped_column(
        String(20), default="asap", nullable=False
    )
    scheduled_for: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    payment_method: Mapped[str] = mapped_column(String(30), nullable=False)
    change_for: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    order_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    whatsapp_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    product_id: Mapped[Optional[int]] = mapped_column(ForeignKey("products.id"), nullable=True)
    combo_id: Mapped[Optional[int]] = mapped_column(ForeignKey("combos.id"), nullable=True)
    item_type: Mapped[Optional[str]] = mapped_column(String(20), default="product", nullable=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="items",
    )

    def __init__(self, **kwargs):
        if "subtotal" in kwargs and "total_price" not in kwargs:
            kwargs["total_price"] = kwargs.pop("subtotal")
        elif "subtotal" in kwargs:
            kwargs.pop("subtotal")
        super().__init__(**kwargs)

    @property
    def subtotal(self) -> Decimal:
        return self.total_price
