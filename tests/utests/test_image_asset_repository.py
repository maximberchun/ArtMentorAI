"""Unit tests for image asset repository boundaries."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ule.artmentorai_project.repositories.image_asset_repository import ImageAssetRepository


def test_image_asset_soft_delete_raises_when_update_fails() -> None:
    """Image asset soft delete should wrap Supabase update errors."""
    client = MagicMock()
    repo = ImageAssetRepository(client)
    (
        client.table.return_value.update.return_value.eq.return_value.eq.return_value.is_.return_value.select.return_value.execute.side_effect
    ) = Exception('write failed')

    with pytest.raises(RuntimeError, match='Failed to delete image metadata'):
        repo.soft_delete('asset-1', 'user-1')
