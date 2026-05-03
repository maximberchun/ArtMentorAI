"""Repository for ``public.image_assets``."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from supabase import Client

from ..models.db_rows import ImageAssetRow
from ._rows import as_model, as_model_list, postgrest_returned_rows, single_row_dict


class ImageAssetRepository:
    """Record metadata for objects stored in Supabase Storage."""

    _table = 'image_assets'

    def __init__(self, client: Client, logger: logging.Logger | None = None) -> None:
        self._client = client
        self._logger = logger or logging.getLogger(__name__)

    def create(  # noqa: PLR0913
        self,
        *,
        user_id: str,
        storage_bucket: str,
        storage_object_path: str,
        mime_type: str | None,
        original_filename: str | None,
        byte_size: int | None,
    ) -> ImageAssetRow:
        """Insert metadata for one stored object."""
        payload = {
            'user_id': user_id,
            'storage_bucket': storage_bucket,
            'storage_object_path': storage_object_path,
            'mime_type': mime_type,
            'original_filename': original_filename,
            'byte_size': byte_size,
        }
        try:
            response = self._client.table(self._table).insert(payload).execute()
        except Exception as exc:
            self._logger.exception(
                'Failed to insert image_asset user_id=%s path=%s',
                user_id,
                storage_object_path,
            )
            msg = f'Failed to record image metadata: {exc!s}'
            raise RuntimeError(msg) from exc

        return as_model(ImageAssetRow, single_row_dict(response.data))

    def get_by_id(self, asset_id: str) -> ImageAssetRow | None:
        """Return an image asset by primary key (any ``deleted_at``). Internal sync use."""
        try:
            response = (
                self._client.table(self._table).select('*').eq('id', asset_id).limit(1).execute()
            )
        except Exception as exc:
            self._logger.exception('Failed to load image_asset id=%s', asset_id)
            msg = f'Failed to load image metadata: {exc!s}'
            raise RuntimeError(msg) from exc

        rows = as_model_list(ImageAssetRow, response.data)
        return rows[0] if rows else None

    def get_active(self, asset_id: str, user_id: str) -> ImageAssetRow | None:
        """Return a non-deleted asset owned by ``user_id``."""
        try:
            response = (
                self._client.table(self._table)
                .select('*')
                .eq('id', asset_id)
                .eq('user_id', user_id)
                .is_('deleted_at', 'null')
                .limit(1)
                .execute()
            )
        except Exception as exc:
            self._logger.exception('Failed to load image_asset id=%s', asset_id)
            msg = f'Failed to load image metadata: {exc!s}'
            raise RuntimeError(msg) from exc

        rows = as_model_list(ImageAssetRow, response.data)
        return rows[0] if rows else None

    def soft_delete(self, asset_id: str, user_id: str) -> bool:
        """Soft-delete an asset row if it belongs to ``user_id``."""
        stamp = datetime.now(tz=UTC).isoformat()
        try:
            response = (
                self._client.table(self._table)
                .update({'deleted_at': stamp})
                .eq('id', asset_id)
                .eq('user_id', user_id)
                .is_('deleted_at', 'null')
                .select('id')
                .execute()
            )
        except Exception as exc:
            self._logger.exception('Failed to soft-delete image_asset id=%s', asset_id)
            msg = f'Failed to delete image metadata: {exc!s}'
            raise RuntimeError(msg) from exc

        return postgrest_returned_rows(response.data)
