"""
The `models.requests` package defines the data structures used for incoming requests.

This package typically includes:
- Request models that validate and parse input payloads from clients.
- Schemas for query parameters, path parameters, and request bodies.
- Data validation logic beyond simple type checks (e.g., custom validators).

Files placed here should focus only on representing the expected
client input. They should not contain business logic (`services`) or
response definitions (`models.responses`).
"""
