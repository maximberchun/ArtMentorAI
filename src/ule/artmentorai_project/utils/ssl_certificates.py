import sys

from ..config import AppConfig


def configure_ssl(config: AppConfig) -> None:
    """
    Configure SSL based on the given configuration.

    If both SSL key and certificate files are present and valid, SSL will
    be enabled. Otherwise, SSL is disabled and a warning is logged.

    Args:
        config (AppConfig): Configuration containing SSL settings.

    """
    logger = config.logger

    if not sys.platform.startswith('linux'):
        logger.info('Skipping SSL configuration: is only applicable on Linux platforms')
        return

    if config.ssl.key and config.ssl.cert:
        if all([config.ssl.key.is_file(), config.ssl.cert.is_file()]):
            logger.info('SSL enabled with key and cert files')
            config.ssl.setup()
        else:
            logger.warning('SSL key or cert file not found, disabling SSL')
            config.ssl.key = None
            config.ssl.cert = None
    else:
        logger.info('SSL disabled - no key/cert configured')
