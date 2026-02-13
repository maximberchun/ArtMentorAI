"""File upload configuration."""

import logging
from pathlib import Path

from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings


class UploadConfig(BaseSettings):
    """Configuration for file uploads."""

    model_config = ConfigDict(frozen=True)

    max_file_size_mb: int = Field(default=10, description='Maximum upload file size in MB')
    upload_dir: Path = Field(default=Path('./uploads'), description='Directory for uploaded files')
    allowed_extensions: list[str] = Field(
        default=['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'],
        description='Allowed file extensions',
    )
    allowed_mime_types: list[str] = Field(
        default=['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp'],
        description='Allowed MIME types',
    )

    def setup(self, logger: logging.Logger) -> None:
        """
        Setup upload configuration with logger.

        Args:
            logger: Logger instance for logging setup info
        """
        logger.info('Upload directory: %s', self.upload_dir)
        logger.info('Max file size: %dMB', self.max_file_size_mb)
        logger.debug('Allowed extensions: %s', ', '.join(self.allowed_extensions))

        # Create the upload directory if it doesn't exist
        self.upload_dir.mkdir(parents=True, exist_ok=True)
