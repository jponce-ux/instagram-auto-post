"""
Pydantic schemas for Meta webhook payloads.

Defines the structure of webhook payloads received from Meta,
including validation models for entry, changes, and values.
"""

from typing import Optional, List
from pydantic import BaseModel


class WebhookValue(BaseModel):
    """
    The value object within a webhook change.

    Contains the actual webhook data including media/container IDs,
    status information, and optional error messages.

    Attributes:
        media_id: The Instagram media ID (ig_media_id)
        container_id: The Instagram container ID (ig_container_id)
        status: The status (PUBLISHED, ERROR, etc.)
        error_message: Optional error message for failed operations
        timestamp: Unix timestamp for replay protection
    """

    media_id: Optional[str] = None
    container_id: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    timestamp: Optional[int] = None


class WebhookChange(BaseModel):
    """
    A single change within a webhook entry.

    Attributes:
        value: The webhook value containing status/data
        field: The field type (e.g., "mentions", "story_insights")
    """

    value: WebhookValue
    field: str


class WebhookEntry(BaseModel):
    """
    A webhook entry representing one Instagram Business Account.

    Attributes:
        id: The Instagram Business Account ID
        time: Unix timestamp when the event occurred
        changes: List of changes for this account
    """

    id: str
    time: int
    changes: List[WebhookChange]


class WebhookPayload(BaseModel):
    """
    The complete webhook payload from Meta.

    Attributes:
        object: The object type ("instagram")
        entry: List of entries, one per affected account
    """

    object: str
    entry: List[WebhookEntry]


class WebhookChallengeResponse(BaseModel):
    """
    Response model for webhook challenge verification.

    Used only for documentation; actual response is plain text.

    Attributes:
        challenge: The challenge string to return to Meta
    """

    challenge: str
