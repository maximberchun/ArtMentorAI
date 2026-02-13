import logging
import os
import shutil
import sys
from collections.abc import Generator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path

import certifi
from pydantic import FilePath
from pydantic_settings import BaseSettings, SettingsConfigDict


class SSLConfig(BaseSettings):
    """SSL configuration for the server."""

    model_config = SettingsConfigDict(env_prefix='SERVER_SSL_')

    cert: FilePath | None = None
    """Path to the SSL certificate file."""

    key: FilePath | None = None
    """Path to the SSL private key file."""

    ca: FilePath | None = None
    """Path to the SSL Certificate Authority (CA) bundle file."""

    def setup(self, logger: logging.Logger) -> None:
        """
        Set up SSL certificates by adding a custom CA bundle to certifi's store if SSL is enabled.

        This function checks if SSL is enabled and if a custom CA bundle path is provided.
        If so, it backs up the current certifi CA store, appends the custom CA bundle to it,
        and sets the SSL_CERT_FILE environment variable to point to the updated store.
        """
        if not sys.platform.startswith('linux'):
            logger.info('Skipping SSL configuration: is only applicable on Linux platforms')
            return

        if not (self.key and self.cert):
            return

        if not (self.ca and self.ca.is_file()):
            logger.warning('SSL is enabled but no CA bundle provided or file not found')
            return

        try:
            with self._manage_certifi_backup() as certifi_path:
                self.__append_custom_ca_to_certifi(self.ca, certifi_path)
        except (
            FileNotFoundError,
            PermissionError,
        ):  # pragma: no cover # This shouldn't be reachable
            logger.error('Failed to add custom CA bundle to certifi store')  # noqa: TRY400
            return

        os.environ['SSL_CERT_FILE'] = str(certifi_path)
        logger.info('Successfully added custom CA bundle to certifi store')

    @classmethod
    def _manage_certifi_backup(cls) -> AbstractContextManager[Path]:
        @contextmanager
        def _context() -> Generator[Path, None, None]:
            certifi_path = Path(certifi.where())
            backup_path = Path(f'{certifi_path}.backup')

            if not backup_path.exists():
                shutil.copy2(certifi_path, backup_path)

            try:
                yield certifi_path
            except Exception:  # pragma: no cover
                if backup_path.exists():
                    shutil.copy2(backup_path, certifi_path)
                raise

        return _context()

    @classmethod
    def __append_custom_ca_to_certifi(cls, ca_path: Path, certifi_path: Path) -> None:
        """Append custom CA bundle to the certifi CA store."""
        with ca_path.open('rb') as custom_ca, certifi_path.open('ab') as certifi_ca:
            certifi_ca.write(b'\n')
            certifi_ca.write(custom_ca.read())
