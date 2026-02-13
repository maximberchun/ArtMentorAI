"""
The `models.responses` package defines the data structures used for outgoing responses.

This package typically includes:
- Response models that structure and validate the data returned by the API.
- Schemas for success payloads, pagination, or metadata.
- Standardized error response formats (if not handled in `exceptions`).

Files placed here should focus only on representing the data sent back
to the client. They should remain independent from request validation
(`models.requests`) and business logic (`services`).
"""
