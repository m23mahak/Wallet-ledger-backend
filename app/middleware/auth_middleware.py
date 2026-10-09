"""Authentication is enforced through FastAPI dependencies, not ASGI middleware.

See app/core/dependencies.py (get_current_user / get_current_admin). Dependencies give
per-route control, OpenAPI "Authorize" support and typed access to the user, which a
global middleware cannot. This module is kept to match the agreed folder structure.
"""
