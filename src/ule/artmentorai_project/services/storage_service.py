"""Supabase Storage service for artwork files."""

from typing import TYPE_CHECKING, Any
from uuid import uuid4

from ..config import AppConfig
from ..db.supabase_client import create_sync_supabase_service_client

if TYPE_CHECKING:
    from supabase import Client


class StorageService:
    """Wrap Supabase Storage operations used by API endpoints."""

    def __init__(self, config: AppConfig) -> None:
        """Initialize storage client from application config."""
        self._config = config
        self._logger = config.logger
        self._bucket = config.supabase.storage_bucket
        self._client: Client = create_sync_supabase_service_client(config)

    def upload_image(
        self,
        *,
        user_id: str,
        image_bytes: bytes,
        filename: str,
        mime_type: str,
    ) -> str:
        """Upload image bytes to Supabase Storage and return object path."""
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'bin'
        object_path = f'{user_id}/{uuid4().hex}.{ext}'

        options: dict[str, Any] = {
            'content-type': mime_type,
            'upsert': 'false',
        }

        try:
            self._client.storage.from_(self._bucket).upload(
                path=object_path,
                file=image_bytes,
                file_options=options,
            )
        except Exception as exc:
            self._logger.exception(
                'Storage upload failed for user_id=%s path=%s',
                user_id,
                object_path,
            )
            msg = f'Failed to upload image to storage: {exc!s}'
            raise RuntimeError(msg) from exc

        self._logger.debug(
            'Uploaded image to storage bucket=%s path=%s user_id=%s',
            self._bucket,
            object_path,
            user_id,
        )
        return object_path

    def create_signed_url(self, object_path: str) -> str | None:
        """Create a temporary signed URL for a stored object path."""
        try:
            response = self._client.storage.from_(self._bucket).create_signed_url(
                path=object_path,
                expires_in=self._config.supabase.signed_url_ttl_seconds,
            )
        except Exception:
            self._logger.exception('Failed to sign storage path=%s', object_path)
            return None

        if isinstance(response, dict):
            signed_url = response.get('signedURL') or response.get('signedUrl')
            if isinstance(signed_url, str) and signed_url:
                return signed_url
        return None

    def delete_file(self, object_path: str) -> bool:
        """Delete one stored object path from Supabase Storage."""
        try:
            self._client.storage.from_(self._bucket).remove([object_path])
        except Exception:
            self._logger.exception('Failed to delete storage path=%s', object_path)
            return False
        else:
            self._logger.debug(
                'Deleted storage object bucket=%s path=%s',
                self._bucket,
                object_path,
            )
            return True
