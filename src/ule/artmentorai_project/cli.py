import argparse
import logging
import sys

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.cors import CORSMiddleware

from .config import AppConfig
from .exceptions import UserExceptionError
from .utils.ssl_certificates import configure_ssl


def create_app(config: AppConfig) -> FastAPI:
    """
    Create and configure the FastAPI application.

    Args:
        config: Application configuration object

    Returns:
        FastAPI: Configured FastAPI application instance

    """
    app = FastAPI(
        title='',
        description='',
        debug=False,
    )

    """Include endpoints"""

    """Create clients"""

    if config.ssl.cert is not None and config.ssl.key is not None:
        app.add_middleware(HTTPSRedirectMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    return app


def _setup_logger(verbose: bool) -> logging.Logger:
    """
    Configure and return the logger.

    Args:
        verbose (bool): Whether to enable verbose (DEBUG) logging.

    Returns:
        logging.Logger: Configured logger instance.

    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level, format='%(asctime)s | %(levelname)s | %(message)s', stream=sys.stdout
    )
    return logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run the FastAPI server')

    parser.add_argument(
        '--dev',
        action='store_true',
        help='Run in development mode (load vars from .env file)',
    )

    return parser.parse_args()


def _run_server(logger: logging.Logger, dev: bool = False) -> None:
    """
    Run the server.

    Attributes:
        dev: development mode. Used to read vars from `.env` file. Defaults to False.

    """
    if dev:
        load_dotenv(override=True)
        logger.info('Loaded environment variables from .env file')

    # Add needed configurations inside AppConfig
    config = AppConfig()
    config.set_logger(logger)

    """Add logger setup if needed"""

    configure_ssl(config)

    app = create_app(config)

    uvicorn.run(
        app,
        host=config.server.host,
        port=config.server.port,
        ssl_keyfile=config.ssl.key,
        ssl_certfile=config.ssl.cert,
        ssl_ca_certs=config.ssl.ca,
    )


def main() -> int:
    """
    Parse arguments and run the server.

    Returns:
        int: Exit code.
            - 0 if the worker ran successfully.
            - 1 if an unexpected error occurred.

    """
    args = _parse_args()
    logger = _setup_logger(args.verbose)

    try:
        _run_server(logger, dev=args.dev)
    except UserExceptionError as e:
        logger.error(e.message)  # noqa: TRY400
        return e.exit_code
    except Exception as e:  # pragma: no cover
        if args.verbose:
            logger.exception('An unexpected error occurred while running the api.')
        else:
            logger.error(  # noqa: TRY400
                'An unexpected error occurred while running the api.'
                'Use --verbose to see the full traceback.'
            )
            logger.error(e)  # noqa: TRY400
        return 1

    return 0


if __name__ == '__main__':
    main()
