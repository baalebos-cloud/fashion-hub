"""Image upload purposes and PostgreSQL delivery ownership regressions."""
from unittest.mock import Mock, patch
from types import SimpleNamespace
from uuid import uuid4
import pytest
from fastapi import HTTPException
from app.api.v1.media import upload_media


@pytest.mark.asyncio
async def test_design_upload_requires_professional_role():
    file = Mock()
    user = SimpleNamespace(id=uuid4(), role="customer")
    with pytest.raises(HTTPException) as exc:
        await upload_media(purpose="design", file=file, user=user)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_product_upload_requires_vendor_role():
    file = Mock()
    user = SimpleNamespace(id=uuid4(), role="tailor")
    with pytest.raises(HTTPException) as exc:
        await upload_media(purpose="product", file=file, user=user)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_portfolio_upload_uses_public_media_for_tailor():
    user = SimpleNamespace(id=uuid4(), role="tailor")
    with patch("app.api.v1.media.save_media", return_value={"url": "test"}) as save:
        # AsyncMock is supplied automatically for async save_media.
        result = await upload_media(purpose="portfolio", file=Mock(), user=user)
    assert result["url"] == "test"
    assert save.call_args.kwargs["public"] is True
    assert save.call_args.kwargs["purpose"] == "portfolio"
