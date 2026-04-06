"""Utility functions for authentication module."""

from fastapi import Request


def is_htmx_request(request: Request) -> bool:
    """Check if request came from HTMX.

    Args:
        request: The FastAPI Request object.

    Returns:
        True if the request has HX-Request header set to "true", False otherwise.
    """
    return request.headers.get("HX-Request") == "true"
