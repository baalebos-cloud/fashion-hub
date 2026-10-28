"""Role, ownership and idempotency guards for material order links."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.core.exceptions import ConflictError, ForbiddenError
from app.services.material_order_link_service import MaterialOrderLinkService


def _setup(*, actor_role="tailor", customer_status="paid", material_status="checkout", parent=None):
    customer = SimpleNamespace(id="customer-1", order_type="customer_order",
                               seller_user_id="tailor-1", status=customer_status)
    material = SimpleNamespace(id="material-1", order_type="vendor_order",
                               buyer_user_id="tailor-1", status=material_status,
                               parent_customer_order_id=parent)
    actor = SimpleNamespace(role=actor_role, id="tailor-1")
    db = Mock()
    db.query.return_value.filter.return_value.with_for_update.return_value.one_or_none.side_effect = [customer, material]
    return db, customer, material, actor


def test_owner_can_link_once_and_commit():
    db, _, material, actor = _setup()
    result = MaterialOrderLinkService(db).attach(
        customer_order_id="customer-1", material_order_id="material-1", actor=actor)
    assert result is material
    assert material.parent_customer_order_id == "customer-1"
    db.commit.assert_called_once()
    db.add.assert_called_once()


def test_cannot_link_other_professionals_order():
    db, _, _, actor = _setup(actor_role="vendor")
    with pytest.raises(ForbiddenError):
        MaterialOrderLinkService(db).attach(
            customer_order_id="customer-1", material_order_id="material-1", actor=actor)
    db.commit.assert_not_called()


def test_paid_material_order_cannot_be_attached():
    db, _, _, actor = _setup(material_status="paid")
    with pytest.raises(ConflictError):
        MaterialOrderLinkService(db).attach(
            customer_order_id="customer-1", material_order_id="material-1", actor=actor)
    db.commit.assert_not_called()


def test_repeat_same_link_is_idempotent():
    db, _, material, actor = _setup(parent="customer-1")
    assert MaterialOrderLinkService(db).attach(
        customer_order_id="customer-1", material_order_id="material-1", actor=actor) is material
    db.commit.assert_not_called()


def test_existing_link_cannot_be_reparented():
    db, _, _, actor = _setup(parent="other")
    with pytest.raises(ConflictError):
        MaterialOrderLinkService(db).attach(
            customer_order_id="customer-1", material_order_id="material-1", actor=actor)
    db.commit.assert_not_called()


def test_failed_commit_rolls_back():
    db, _, _, actor = _setup()
    db.commit.side_effect = RuntimeError("database unavailable")
    with pytest.raises(RuntimeError):
        MaterialOrderLinkService(db).attach(
            customer_order_id="customer-1", material_order_id="material-1", actor=actor)
    db.rollback.assert_called_once()
