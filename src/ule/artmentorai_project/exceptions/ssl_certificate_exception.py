class SSLCertificateError(Exception):
    """SSL certificate setup failed."""

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or 'SSL certificate setup failed.')
