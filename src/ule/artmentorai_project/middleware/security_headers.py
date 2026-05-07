"""Baseline HTTP security headers for API responses."""

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach conservative security headers suitable for a JSON API."""

    @staticmethod
    def _csp_for_path(path: str) -> str:
        """Return a route-specific CSP policy."""
        if path == '/docs':
            return (
                "default-src 'self'; "
                "base-uri 'none'; "
                "frame-ancestors 'none'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https://fastapi.tiangolo.com"
            )
        if path == '/redoc':
            return (
                "default-src 'self'; "
                "base-uri 'none'; "
                "frame-ancestors 'none'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data:"
            )
        return "default-src 'none'; base-uri 'none'; frame-ancestors 'none'"

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Forward the request and add security headers to the outgoing response."""
        response = await call_next(request)
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.headers.setdefault(
            'Permissions-Policy',
            'camera=(), microphone=(), geolocation=()',
        )
        response.headers.setdefault(
            'Content-Security-Policy',
            self._csp_for_path(request.url.path),
        )
        return response
