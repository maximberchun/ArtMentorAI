"""Command-line interface for ArtMentor AI."""

import argparse
import logging
import sys

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.cors import CORSMiddleware

from .config import AppConfig
from .endpoints import create_analysis_router
from .exceptions import UserExceptionError
from .utils import configure_ssl


def create_app(config: AppConfig) -> FastAPI:
    """
    Create and configure the FastAPI application.

    Initializes all routes, middleware, and services.

    Args:
        config: Application configuration object

    Returns:
        FastAPI: Configured FastAPI application instance
    """
    app = FastAPI(
        title=config.app_name,
        description='Intelligent assistant for artwork analysis and critique using AI',
        version=config.app_version,
        debug=config.debug,
        docs_url='/docs',
        redoc_url='/redoc',
    )

    # ============== Include Routers ==============
    config.logger.info('Registering endpoints')

    # Analysis endpoint (includes critique and health checks)
    analysis_router = create_analysis_router(config)
    app.include_router(analysis_router)

    config.logger.debug('Analysis router registered at /analysis')

    # ============== Add Middleware ==============
    config.logger.info('Configuring middleware')

    # Add HTTP to HTTPS redirect if SSL is configured
    if config.ssl.cert is not None and config.ssl.key is not None:
        app.add_middleware(HTTPSRedirectMiddleware)
        config.logger.info('HTTPS redirect middleware enabled')

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.allowed_origins,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )
    config.logger.debug(
        'CORS middleware configured for origins: %s',
        ', '.join(config.allowed_origins),
    )

    # ============== Root Endpoints ==============
    @app.get('/', tags=['General'])
    async def root() -> dict:
        """Root endpoint with API information."""
        return {
            'name': config.app_name,
            'version': config.app_version,
            'environment': config.environment,
            'status': 'running',
            'docs': '/docs',
            'redoc': '/redoc',
            'endpoints': {
                'critique': 'POST /analysis/critique',
                'analysis_health': 'GET /analysis/health',
                'vector_db_health': 'GET /analysis/vector-db-health',
            },
        }

    @app.get('/health', tags=['General'])
    async def health() -> dict:
        """Global health check for the application."""
        return {
            'status': 'healthy',
            'app': config.app_name,
            'version': config.app_version,
            'environment': config.environment,
        }

    config.logger.info('Application endpoints registered successfully')

    return app


def _setup_logger(verbose: bool) -> logging.Logger:
    """
    Configure and return the logger.

    Args:
        verbose: Whether to enable verbose (DEBUG) logging.

    Returns:
        logging.Logger: Configured logger instance.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s | %(levelname)s | %(message)s',
        stream=sys.stdout,
    )
    return logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    """
    Parse command line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='ArtMentor AI - Intelligent artwork analysis server',
        prog='artmentor',
    )

    parser.add_argument(
        '--dev',
        action='store_true',
        help='Run in development mode (load vars from .env file)',
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose (DEBUG) logging',
    )

    return parser.parse_args()


def _run_server(logger: logging.Logger, dev: bool = False) -> None:
    """
    Run the server.

    Args:
        logger: Logger instance
        dev: Development mode. Used to read vars from `.env` file. Defaults to False.

    Raises:
        UserExceptionError: If configuration fails
    """
    if dev:
        load_dotenv(override=True)
        logger.info('Loaded environment variables from .env file')

    # Load and validate configuration
    try:
        config = AppConfig()
        config.set_logger(logger)
    except Exception as e:
        msg = f'Failed to load configuration: {e!s}'
        raise UserExceptionError(
            msg,
            exit_code=1,
        ) from e

    # Configure SSL
    configure_ssl(config)

    # Create FastAPI app with all endpoints
    app = create_app(config)

    # Run server
    logger.info(
        'Starting %s on %s:%s (environment: %s)',
        config.app_name,
        config.server.host,
        config.server.port,
        config.environment,
    )
    logger.info(
        'API Documentation available at http://%s:%s/docs',
        config.server.host,
        config.server.port,
    )

    uvicorn.run(
        app,
        host=config.server.host,
        port=config.server.port,
        ssl_keyfile=str(config.ssl.key) if config.ssl.key else None,
        ssl_certfile=str(config.ssl.cert) if config.ssl.cert else None,
        ssl_ca_certs=str(config.ssl.ca) if config.ssl.ca else None,
        reload=config.server.reload,
        log_level='debug' if config.debug else 'info',
    )


def main() -> int:
    """
    Parse arguments and run the server.

    Returns:
        int: Exit code.
            - 0 if the server ran successfully.
            - Non-zero if an error occurred.
    """
    args = _parse_args()
    logger = _setup_logger(args.verbose)

    try:
        _run_server(logger, dev=args.dev)
    except UserExceptionError as e:
        logger.exception('Error: %s', e.message)
        return e.exit_code
    except KeyboardInterrupt:
        logger.info('Server stopped by user')
        return 0
    except Exception:
        if args.verbose:
            logger.exception('An unexpected error occurred while running the api.')
        else:
            logger.exception(
                'An unexpected error occurred while running the api. '
                'Use --verbose to see the full traceback.'
            )
            logger.exception('Error')
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
