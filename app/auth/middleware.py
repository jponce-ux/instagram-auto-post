"""
Rolling Session Middleware for FastAPI.

Intercepts responses and refreshes the JWT cookie when the user is authenticated.
This implements a sliding expiration mechanism: each valid request extends the
session by SESSION_INACTIVITY_LIMIT_HOURS.

The middleware only refreshes the cookie if:
1. The request has a valid JWT in the access_token cookie
2. The token is not expired
3. The token's iat is within the inactivity limit
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from jose import jwt, JWTError

from app.core.config import settings
from app.auth.security import create_access_token

logger = logging.getLogger(__name__)

# Paths that should NOT trigger session refresh
EXCLUDED_PATHS = {
    "/auth/login",
    "/auth/register",
    "/auth/logout",
    "/auth/confirm-email",
    "/auth/verify-email",
    "/auth/resend-verification-email",
    "/webhooks/instagram",
    "/api/v1/ping",
    "/static",
    "/docs",
    "/openapi.json",
    "/redoc",
}


def _should_refresh(path: str) -> bool:
    """Check if the request path should trigger a session refresh."""
    if path in EXCLUDED_PATHS:
        return False
    # Exclude paths that start with excluded prefixes
    for excluded in EXCLUDED_PATHS:
        if path.startswith(excluded + "/"):
            return False
    return True


def _extract_token_from_cookie(request: Request) -> str | None:
    """Extract JWT from the access_token cookie."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    if token.startswith("Bearer "):
        token = token[7:]
    return token


def _validate_token(token: str) -> dict | None:
    """Validate JWT and return payload. Returns None if invalid or expired."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        return None


def _is_within_inactivity_limit(payload: dict) -> bool:
    """Check if the token's iat is within the inactivity limit."""
    iat = payload.get("iat")
    if iat is None:
        # Old token without iat — treat as within limit (will be refreshed)
        return True
    # iat might be a float timestamp or a datetime string
    if isinstance(iat, (int, float)):
        iat_dt = datetime.fromtimestamp(iat, tz=timezone.utc)
    else:
        # Try to parse as ISO string
        try:
            iat_dt = datetime.fromisoformat(str(iat)).replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return True

    now = datetime.now(timezone.utc)
    limit = timedelta(hours=settings.SESSION_INACTIVITY_LIMIT_HOURS)
    return (now - iat_dt) < limit


class RollingSessionMiddleware(BaseHTTPMiddleware):
    """Middleware that refreshes JWT cookie on each authenticated request."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Only refresh for paths that should trigger it
        if not _should_refresh(request.url.path):
            return response

        # Only refresh for GET/POST requests (not OPTIONS, etc.)
        if request.method not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            return response

        # Extract and validate token
        token = _extract_token_from_cookie(request)
        if not token:
            return response

        payload = _validate_token(token)
        if payload is None:
            return response

        # Check inactivity limit
        if not _is_within_inactivity_limit(payload):
            return response

        # Generate new token with refreshed iat
        email = payload.get("sub")
        if not email:
            return response

        try:
            new_token = create_access_token(data={"sub": email})
            max_age = settings.SESSION_COOKIE_MAX_AGE_DAYS * 86400
            response.set_cookie(
                key="access_token",
                value=f"Bearer {new_token}",
                httponly=True,
                secure=True,
                samesite="lax",
                max_age=max_age,
            )
            logger.debug(f"Session refreshed for user {email}")
        except Exception as e:
            logger.warning(f"Failed to refresh session for {email}: {e}")

        return response
