"""
The `endpoints` package defines the entry points of the API.

This package typically includes:
- Route handlers (controllers) that expose the business logic via HTTP endpoints.
- Request/response models and validation tied to specific routes.
- Endpoint-specific dependencies (authentication, authorization, etc.).
- Routing configuration to organize the API structure.

Files placed here should handle request/response flow and delegate the
actual business rules to the `services` layer, keeping controllers thin
and focused on API communication.
"""
