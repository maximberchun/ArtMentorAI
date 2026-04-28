"""Unit tests for portfolio repository boundaries."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from ule.artmentorai_project.repositories.portfolio_item_repository import (
    PortfolioItemRepository,
)


def test_portfolio_create_returns_row_on_valid_single_insert_response() -> None:
    """Create should map a successful single-row Supabase insert payload."""
    client = MagicMock()
    repo = PortfolioItemRepository(client)
    row = {
        'id': 'item-1',
        'user_id': 'user-1',
        'image_asset_id': 'asset-1',
        'filename': 'study.png',
        'tags': ['gesture'],
        'description': 'line study',
    }
    client.table.return_value.insert.return_value.execute.return_value = SimpleNamespace(data=[row])

    result = repo.create(user_id='user-1', image_asset_id='asset-1', filename='study.png')

    assert result.id == 'item-1'
    assert result.user_id == 'user-1'
    assert result.filename == 'study.png'


def test_portfolio_create_wraps_insert_failures() -> None:
    """Create should wrap Supabase failures with repository-level RuntimeError."""
    client = MagicMock()
    repo = PortfolioItemRepository(client)
    client.table.return_value.insert.return_value.execute.side_effect = Exception('db down')

    with pytest.raises(RuntimeError, match='Failed to save portfolio item'):
        repo.create(user_id='user-1', image_asset_id='asset-1', filename='study.png')
