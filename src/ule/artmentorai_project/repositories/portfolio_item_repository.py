"""Repository for ``public.portfolio_items``."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from supabase import Client

from ..models.db_rows import PortfolioItemRow
from ._rows import as_model, as_model_list, single_row_dict


class PortfolioItemRepository:
    """Persist portfolio uploads linked to ``image_assets`` rows."""

    _table = 'portfolio_items'

    def __init__(self, client: Client, logger: logging.Logger | None = None) -> None:
        self._client = client
        self._logger = logger or logging.getLogger(__name__)

    def create(  # noqa: PLR0913
        self,
        *,
        user_id: str,
        image_asset_id: str,
        filename: str,
        tags: list[str] | None = None,
        description: str = '',
        vector_point_id: str | None = None,
    ) -> PortfolioItemRow:
        """Insert one portfolio item."""
        payload = {
            'user_id': user_id,
            'image_asset_id': image_asset_id,
            'filename': filename,
            'tags': tags or [],
            'description': description,
            'vector_point_id': vector_point_id,
        }
        try:
            response = self._client.table(self._table).insert(payload).execute()
        except Exception as exc:
            self._logger.exception('Failed to insert portfolio_item user_id=%s', user_id)
            msg = f'Failed to save portfolio item: {exc!s}'
            raise RuntimeError(msg) from exc

        return as_model(PortfolioItemRow, single_row_dict(response.data))

    def create_many(self, items: list[dict[str, Any]]) -> list[PortfolioItemRow]:
        """Bulk insert portfolio items (PostgREST array insert)."""
        if not items:
            return []
        try:
            response = self._client.table(self._table).insert(items).execute()
        except Exception as exc:
            self._logger.exception('Failed bulk insert portfolio_items count=%s', len(items))
            msg = f'Failed to save portfolio items: {exc!s}'
            raise RuntimeError(msg) from exc

        return as_model_list(PortfolioItemRow, response.data)

    def get_by_id(self, item_id: str) -> PortfolioItemRow | None:
        """Return a portfolio row by primary key (any ``deleted_at``). Internal sync use."""
        try:
            response = (
                self._client.table(self._table).select('*').eq('id', item_id).limit(1).execute()
            )
        except Exception as exc:
            self._logger.exception('Failed to load portfolio_item id=%s', item_id)
            msg = f'Failed to load portfolio item: {exc!s}'
            raise RuntimeError(msg) from exc

        rows = as_model_list(PortfolioItemRow, response.data)
        return rows[0] if rows else None

    def get_active(self, item_id: str, user_id: str) -> PortfolioItemRow | None:
        """Return a non-deleted portfolio row owned by ``user_id``."""
        try:
            response = (
                self._client.table(self._table)
                .select('*')
                .eq('id', item_id)
                .eq('user_id', user_id)
                .is_('deleted_at', 'null')
                .limit(1)
                .execute()
            )
        except Exception as exc:
            self._logger.exception('Failed to load portfolio_item id=%s', item_id)
            msg = f'Failed to load portfolio item: {exc!s}'
            raise RuntimeError(msg) from exc

        rows = as_model_list(PortfolioItemRow, response.data)
        return rows[0] if rows else None

    def list_active_for_user(self, user_id: str, *, limit: int = 100) -> list[PortfolioItemRow]:
        """List non-deleted portfolio items for a user, newest first."""
        try:
            response = (
                self._client.table(self._table)
                .select('*')
                .eq('user_id', user_id)
                .is_('deleted_at', 'null')
                .order('created_at', desc=True)
                .limit(limit)
                .execute()
            )
        except Exception as exc:
            self._logger.exception('Failed to list portfolio_items user_id=%s', user_id)
            msg = f'Failed to list portfolio items: {exc!s}'
            raise RuntimeError(msg) from exc

        return as_model_list(PortfolioItemRow, response.data)

    def set_vector_point_id(self, item_id: str, user_id: str, vector_point_id: str) -> None:
        """Attach the derived Qdrant point id after indexing."""
        try:
            self._client.table(self._table).update({'vector_point_id': vector_point_id}).eq(
                'id', item_id
            ).eq('user_id', user_id).is_('deleted_at', 'null').execute()
        except Exception as exc:
            self._logger.exception('Failed to link vector id for portfolio id=%s', item_id)
            msg = f'Failed to update portfolio vector id: {exc!s}'
            raise RuntimeError(msg) from exc

    def soft_delete(self, item_id: str, user_id: str) -> bool:
        """Soft-delete a portfolio item if it belongs to ``user_id``."""
        stamp = datetime.now(tz=UTC).isoformat()
        try:
            response = (
                self._client.table(self._table)
                .update({'deleted_at': stamp})
                .eq('id', item_id)
                .eq('user_id', user_id)
                .is_('deleted_at', 'null')
                .select('id')
                .execute()
            )
        except Exception as exc:
            self._logger.exception('Failed to soft-delete portfolio_item id=%s', item_id)
            msg = f'Failed to delete portfolio item: {exc!s}'
            raise RuntimeError(msg) from exc

        data = response.data
        if isinstance(data, list):
            return len(data) > 0
        return data is not None
