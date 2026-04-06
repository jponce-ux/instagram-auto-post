"""
Security utilities for Meta webhook signature validation.

Implements HMAC-SHA1 signature verification for webhook authenticity.
Replay attack prevention is handled through idempotent business logic
in the webhook handler (check current state before updating).

Security model:
- HMAC signature validates payload authenticity (not tampered)
- HTTPS via Cloudflare tunnel encrypts traffic in transit
- Idempotent updates prevent duplicate processing from replayed webhooks
"""

import hmac
import hashlib
import logging
from functools import wraps
from typing import Callable

from fastapi import Request, HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)


def verify_webhook_signature(func: Callable) -> Callable:
    """
    Decorator that validates X-Hub-Signature header for Meta webhooks.

    Validation steps:
    1. Extract X-Hub-Signature header (format: "sha1=<hash>")
    2. Compute HMAC-SHA1(payload, META_APP_SECRET)
    3. Compare signatures using constant-time comparison

    Raises:
        HTTPException: 401 if signature is invalid or missing

    Note:
        Replay attack prevention is handled by idempotent business logic
        in the webhook handler, not by timestamp validation.

    Usage:
        @router.post("/webhooks/instagram")
        @verify_webhook_signature
        async def webhook_handler(request: Request):
            ...
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Find the Request object in args or kwargs
        request: Request | None = None
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break
        if request is None:
            request = kwargs.get("request")

        if request is None:
            raise HTTPException(
                status_code=500,
                detail="Request object not found for signature validation",
            )

        # Get signature header
        signature_header = request.headers.get("X-Hub-Signature")
        if not signature_header:
            raise HTTPException(
                status_code=401, detail="Missing X-Hub-Signature header"
            )

        # Parse signature (format: "sha1=<hash>")
        if not signature_header.startswith("sha1="):
            raise HTTPException(status_code=401, detail="Invalid signature format")

        expected_signature = signature_header[5:]  # Remove "sha1=" prefix

        # Read request body
        body = await request.body()

        # Compute HMAC-SHA1
        app_secret = settings.META_APP_SECRET.encode("utf-8")
        computed_hash = hmac.new(app_secret, body, hashlib.sha1).hexdigest()

        # Constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(computed_hash, expected_signature):
            raise HTTPException(status_code=401, detail="Invalid signature")

        return await func(*args, **kwargs)

    return wrapper
