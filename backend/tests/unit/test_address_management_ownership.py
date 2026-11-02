"""Address owner scope and default-address behavior regression tests."""
from unittest.mock import Mock
from uuid import uuid4
import pytest
from fastapi import HTTPException
from app.api.v1.addresses import make_default, delete_address


def test_default_address_not_found_for_other_owner():
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        make_default(uuid4(), user=Mock(id=uuid4()), db=db)
    assert exc.value.status_code == 404
    db.commit.assert_not_called()


def test_delete_address_does_not_remove_unowned_record():
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        delete_address(uuid4(), user=Mock(id=uuid4()), db=db)
    assert exc.value.status_code == 404
    db.delete.assert_not_called()
    db.commit.assert_not_called()
