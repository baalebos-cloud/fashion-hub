#!/usr/bin/env python
"""
Seeds the database with baseline reference data (order status definitions,
default categories) for local development. Idempotent -- safe to re-run.

Usage: python scripts/seed_database.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.constants import CustomerOrderStatus, VendorOrderStatus
from app.core.database import session_scope
from app.models.category import Category
from app.models.order_status import OrderStatusDefinition
from app.models.vendor_category import VendorCategory

DEFAULT_CATEGORIES = ["Native Wear", "Suits", "Bridal", "Casual Wear", "Uniforms"]
DEFAULT_VENDOR_CATEGORIES = ["Fabrics", "Buttons", "Zippers", "Threads", "Linings", "Trims"]


def seed_order_statuses(db):
    for i, status in enumerate(CustomerOrderStatus):
        exists = (
            db.query(OrderStatusDefinition)
            .filter(OrderStatusDefinition.order_type == "customer_order", OrderStatusDefinition.code == status.value)
            .first()
        )
        if not exists:
            db.add(
                OrderStatusDefinition(
                    order_type="customer_order", code=status.value, label=status.value.replace("_", " ").title(), sort_order=i
                )
            )
    for i, status in enumerate(VendorOrderStatus):
        exists = (
            db.query(OrderStatusDefinition)
            .filter(OrderStatusDefinition.order_type == "vendor_order", OrderStatusDefinition.code == status.value)
            .first()
        )
        if not exists:
            db.add(
                OrderStatusDefinition(
                    order_type="vendor_order", code=status.value, label=status.value.replace("_", " ").title(), sort_order=i
                )
            )


def seed_categories(db):
    for name in DEFAULT_CATEGORIES:
        slug = name.lower().replace(" ", "-")
        if not db.query(Category).filter(Category.slug == slug).first():
            db.add(Category(name=name, slug=slug))

    for name in DEFAULT_VENDOR_CATEGORIES:
        slug = name.lower().replace(" ", "-")
        if not db.query(VendorCategory).filter(VendorCategory.slug == slug).first():
            db.add(VendorCategory(name=name, slug=slug))


def main():
    with session_scope() as db:
        seed_order_statuses(db)
        seed_categories(db)
    print("Database seeded successfully.")


if __name__ == "__main__":
    main()
