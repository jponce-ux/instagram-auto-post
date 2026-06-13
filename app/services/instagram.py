import httpx
from app.core.config import settings

META_API_BASE = "https://graph.instagram.com/v21.0"
INSTAGRAM_OAUTH_BASE = "https://api.instagram.com/oauth"

# Timeout for all Meta API requests (connect, read, write, pool)
API_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


async def exchange_short_token(code: str, redirect_uri: str) -> dict:
    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        response = await client.post(
            f"{INSTAGRAM_OAUTH_BASE}/access_token",
            data={
                "client_id": settings.META_APP_ID,
                "client_secret": settings.META_APP_SECRET,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
                "code": code,
            },
        )
        response.raise_for_status()
        return response.json()


async def get_long_lived_token(short_token: str) -> dict:
    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        response = await client.get(
            "https://graph.instagram.com/access_token",
            params={
                "grant_type": "ig_exchange_token",
                "client_secret": settings.META_APP_SECRET,
                "access_token": short_token,
            },
        )
        response.raise_for_status()
        return response.json()


async def get_instagram_account_id(access_token: str) -> tuple[str, str]:
    """Get the Instagram Business Account ID and username using the IG access token.

    Returns:
        tuple of (instagram_user_id, username)
    """
    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        response = await client.get(
            "https://graph.instagram.com/v25.0/me",
            params={
                "fields": "user_id,username",
                "access_token": access_token,
            },
        )
        response.raise_for_status()
        data = response.json()

        ig_user_id = data.get("user_id") or data.get("id", "")
        username = data.get("username", "")

        if not ig_user_id:
            raise ValueError(f"Could not get Instagram user ID from /me endpoint: {data}")

        return str(ig_user_id), username


async def create_media_container(
    ig_account_id: str, access_token: str, media_url: str, caption: str = ""
) -> str:
    """
    Create an IG Media Container for publishing.

    Returns:
        container_id: The ID of the created media container

    Raises:
        Exception: If the API request fails, with Instagram error details
    """
    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        response = await client.post(
            f"{META_API_BASE}/{ig_account_id}/media",
            params={
                "access_token": access_token,
                "image_url": media_url,
                "caption": caption,
            },
        )
        if response.status_code != 200:
            try:
                error_data = response.json().get("error", {})
                error_msg = error_data.get("message", response.text)
                error_code = error_data.get("code", response.status_code)
                error_type = error_data.get("type", "")
                raise Exception(
                    f"Instagram API error {error_code}: {error_type} — {error_msg}"
                )
            except ValueError:
                response.raise_for_status()
        data = response.json()
        return data.get("id")


async def get_container_status(container_id: str, access_token: str) -> dict:
    """
    Check the status of a media container.

    Returns:
        dict with 'status_code' key (e.g., 'FINISHED', 'IN_PROGRESS', 'ERROR')

    Raises:
        httpx.HTTPError: If the API request fails
    """
    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        response = await client.get(
            f"{META_API_BASE}/{container_id}",
            params={
                "access_token": access_token,
                "fields": "status_code",
            },
        )
        response.raise_for_status()
        return response.json()


async def publish_media_container(
    ig_account_id: str, access_token: str, container_id: str
) -> str:
    """
    Publish a media container to Instagram feed.

    Returns:
        media_id: The published IG Media ID

    Raises:
        Exception: If the API request fails, with Instagram error details
    """
    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        response = await client.post(
            f"{META_API_BASE}/{ig_account_id}/media_publish",
            params={
                "access_token": access_token,
                "creation_id": container_id,
            },
        )
        if response.status_code != 200:
            try:
                error_data = response.json().get("error", {})
                error_msg = error_data.get("message", response.text)
                error_code = error_data.get("code", response.status_code)
                error_type = error_data.get("type", "")
                raise Exception(
                    f"Instagram API error {error_code}: {error_type} — {error_msg}"
                )
            except ValueError:
                response.raise_for_status()
        data = response.json()
        return data.get("id")
