"""Sandbox financial journal invariants and transition guards."""
from types import SimpleNamespace
from unittest.mock import Mock
import pytest

from app.core.exceptions import ConflictError, ForbiddenError
from app.services.saga.orchestrator import SandboxSagaService, SagaState, NEXT


def test_all_saga_end_states_have_no_forward_edges():
    for state in (SagaState.COMPLETED, SagaState.CANCELLED_REFUNDED, SagaState.REVIEW_REQUIRED):
        assert NEXT[state] == set()


def test_rejects_skipped_forward_and_unconfirmed_refunds(monkeypatch):
    from app.services.saga import orchestrator
    monkeypatch.setattr(orchestrator.settings, "APP_ENV", "test")
    monkeypatch.setattr(orchestrator.settings, "PAYMENTS_ENABLED", False)
    db = Mock()
    order = SimpleNamespace(id="order-1", order_type="customer_order", buyer_user_id="buyer-1",
                            seller_user_id="tailor-1", total_amount=100, currency="NGN")
    actor = SimpleNamespace(id="buyer-1", role="customer")
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = order
    db.query.return_value.filter.return_value.first.side_effect = [None, order]
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
    service = SandboxSagaService(db)
    with pytest.raises(ConflictError):
        service.advance(order_id=order.id, actor=actor, target=SagaState.COMPLETED,
                        event_key="evt-skipped")
    with pytest.raises(ConflictError, match="Provider confirmation"):
        service.advance(order_id=order.id, actor=actor, target=SagaState.ESCROW_HELD,
                        event_key="evt-no-confirm")
    db.commit.assert_not_called()


def test_production_prohibits_simulation(monkeypatch):
    from app.services.saga import orchestrator
    monkeypatch.setattr(orchestrator.settings, "APP_ENV", "production")
    with pytest.raises(ForbiddenError):
        SandboxSagaService(Mock()).state("order")


def test_all_journal_events_are_balanced_by_construction(monkeypatch):
    from app.services.saga import orchestrator
    monkeypatch.setattr(orchestrator.settings, "APP_ENV", "test")
    monkeypatch.setattr(orchestrator.settings, "PAYMENTS_ENABLED", False)
    db = Mock()
    order = SimpleNamespace(id="order-1", order_type="customer_order", buyer_user_id="buyer",
                            seller_user_id="tailor", total_amount=100, currency="NGN")
    actor = SimpleNamespace(id="buyer", role="customer")
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = order
    db.query.return_value.filter.return_value.first.side_effect = [None, order]
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
    SandboxSagaService(db).advance(order_id="order-1", actor=actor,
                                  target=SagaState.ESCROW_HELD,
                                  event_key="mock-only", provider_confirmed=True)
    from app.models.saga import LedgerEntry
    entries = [c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], LedgerEntry)]
    assert len(entries) == 2
    assert {x.direction for x in entries} == {"debit", "credit"}
    assert entries[0].amount_minor == entries[1].amount_minor
