"""Optional HTTP Basic Auth, enforced as middleware (not a route dependency)
so it covers *everything* — API routes and the static frontend mount alike.
Only activates if BASIC_AUTH_USERNAME and BASIC_AUTH_PASSWORD are both set;
otherwise the app behaves exactly as it does for local/laptop use, with no
auth prompt at all.

This protects credentials from casual/opportunistic access, but Basic Auth
sends credentials base64-encoded (trivially decoded, not encrypted) on every
request. If exposing this on the public internet rather than an IP-restricted
security group, put a TLS-terminating reverse proxy (e.g. Caddy) in front —
see the README's EC2 section.
"""
from __future__ import annotations

import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings

_UNAUTHORIZED = Response(
    content="Authentication required.",
    status_code=401,
    headers={"WWW-Authenticate": 'Basic realm="Career Agent"'},
)


class BasicAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not settings.basic_auth_enabled:
            return await call_next(request)

        auth = request.headers.get("authorization", "")
        if not auth.startswith("Basic "):
            return _UNAUTHORIZED

        import base64

        try:
            decoded = base64.b64decode(auth[6:]).decode("utf-8")
            username, _, password = decoded.partition(":")
        except Exception:
            return _UNAUTHORIZED

        user_ok = secrets.compare_digest(username, settings.basic_auth_username)
        pass_ok = secrets.compare_digest(password, settings.basic_auth_password)
        if not (user_ok and pass_ok):
            return _UNAUTHORIZED

        return await call_next(request)
