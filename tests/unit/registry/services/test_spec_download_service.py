"""Unit tests for SpecDownloadService."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from jentic_one.registry.services.errors import (
    ApiNotFoundError,
    NoCurrentRevisionError,
    RevisionNotFoundError,
)
from jentic_one.registry.services.spec_download_service import SpecDownloadService


def _make_ctx() -> MagicMock:
    ctx = MagicMock()
    mock_session = AsyncMock()
    ctx.registry_db.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    ctx.registry_db.session.return_value.__aexit__ = AsyncMock(return_value=False)
    return ctx


@pytest.mark.asyncio
async def test_get_live_spec_happy_path() -> None:
    ctx = _make_ctx()
    mock_api = MagicMock()
    mock_api.current_revision_id = uuid.uuid4()

    mock_spec_file = MagicMock()
    mock_spec_file.content = {"openapi": "3.1.0", "info": {"title": "Test"}}

    with (
        patch(
            "jentic_one.registry.services.spec_download_service.ApiRepository.get_by_identifier_with_current_revision",
            new_callable=AsyncMock,
            return_value=mock_api,
        ),
        patch(
            "jentic_one.registry.services.spec_download_service.SpecFileRepository.get_for_revision",
            new_callable=AsyncMock,
            return_value=mock_spec_file,
        ),
    ):
        svc = SpecDownloadService(ctx)
        doc = await svc.get_live_spec("acme", "petstore", "1.0")

    assert doc.content == {"openapi": "3.1.0", "info": {"title": "Test"}}
    assert doc.filename_stem == "acme-petstore-1.0"


@pytest.mark.asyncio
async def test_get_live_spec_api_not_found() -> None:
    ctx = _make_ctx()

    with patch(
        "jentic_one.registry.services.spec_download_service.ApiRepository.get_by_identifier_with_current_revision",
        new_callable=AsyncMock,
        return_value=None,
    ):
        svc = SpecDownloadService(ctx)
        with pytest.raises(ApiNotFoundError):
            await svc.get_live_spec("acme", "missing", "1.0")


@pytest.mark.asyncio
async def test_get_live_spec_no_current_revision() -> None:
    ctx = _make_ctx()
    mock_api = MagicMock()
    mock_api.current_revision_id = None

    with patch(
        "jentic_one.registry.services.spec_download_service.ApiRepository.get_by_identifier_with_current_revision",
        new_callable=AsyncMock,
        return_value=mock_api,
    ):
        svc = SpecDownloadService(ctx)
        with pytest.raises(NoCurrentRevisionError):
            await svc.get_live_spec("acme", "petstore", "1.0")


@pytest.mark.asyncio
async def test_get_revision_spec_happy_path() -> None:
    ctx = _make_ctx()
    revision_id = uuid.uuid4()

    mock_api = MagicMock()
    mock_api.id = uuid.uuid4()

    mock_revision = MagicMock()
    mock_revision.id = revision_id

    mock_spec_file = MagicMock()
    mock_spec_file.content = {"openapi": "3.1.0", "paths": {}}

    with (
        patch(
            "jentic_one.registry.services.spec_download_service.ApiRepository.get_by_identifier",
            new_callable=AsyncMock,
            return_value=mock_api,
        ),
        patch(
            "jentic_one.registry.services.spec_download_service.ApiRevisionRepository.get_for_api",
            new_callable=AsyncMock,
            return_value=mock_revision,
        ),
        patch(
            "jentic_one.registry.services.spec_download_service.SpecFileRepository.get_for_revision",
            new_callable=AsyncMock,
            return_value=mock_spec_file,
        ),
    ):
        svc = SpecDownloadService(ctx)
        doc = await svc.get_revision_spec("acme", "petstore", "1.0", str(revision_id))

    assert doc.content == {"openapi": "3.1.0", "paths": {}}
    assert doc.filename_stem == "acme-petstore-1.0"


@pytest.mark.asyncio
async def test_get_revision_spec_invalid_uuid() -> None:
    ctx = _make_ctx()
    svc = SpecDownloadService(ctx)
    with pytest.raises(RevisionNotFoundError):
        await svc.get_revision_spec("acme", "petstore", "1.0", "not-a-uuid")


@pytest.mark.asyncio
async def test_get_revision_spec_revision_not_found() -> None:
    ctx = _make_ctx()
    revision_id = uuid.uuid4()

    mock_api = MagicMock()
    mock_api.id = uuid.uuid4()

    with (
        patch(
            "jentic_one.registry.services.spec_download_service.ApiRepository.get_by_identifier",
            new_callable=AsyncMock,
            return_value=mock_api,
        ),
        patch(
            "jentic_one.registry.services.spec_download_service.ApiRevisionRepository.get_for_api",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        svc = SpecDownloadService(ctx)
        with pytest.raises(RevisionNotFoundError):
            await svc.get_revision_spec("acme", "petstore", "1.0", str(revision_id))
