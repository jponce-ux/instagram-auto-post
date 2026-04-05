import httpx
from app.core.config import settings

META_API_BASE = "https://graph.facebook.com/v18.0"


async def exchange_short_token(code: str, redirect_uri: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{META_API_BASE}/oauth/access_token",
            params={
                "client_id": settings.META_APP_ID,
                "client_secret": settings.META_APP_SECRET,
                "redirect_uri": redirect_uri,
                "code": code,
            },
        )
        response.raise_for_status()
        return response.json()


async def get_long_lived_token(short_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{META_API_BASE}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": settings.META_APP_ID,
                "client_secret": settings.META_APP_SECRET,
                "fb_exchange_token": short_token,
            },
        )
        response.raise_for_status()
        return response.json()


async def get_instagram_account_id(access_token: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{META_API_BASE}/me/accounts",
            params={"access_token": access_token},
        )
        response.raise_for_status()
        data = response.json()
        return data.get("data", [{}])[0].get("id", "")


async def create_media_container(
    ig_account_id: str, access_token: str, media_url: str, caption: str = ""
) -> str:
    """
    Create an IG Media Container for publishing.

    Returns:
        container_id: The ID of the created media container

    Raises:
        httpx.HTTPError: If the API request fails
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{META_API_BASE}/{ig_account_id}/media",
            params={
                "access_token": access_token,
                "image_url": media_url,
                "caption": caption,
            },
        )
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
    async with httpx.AsyncClient() as client:
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
        httpx.HTTPError: If the API request fails (including rate limits)
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{META_API_BASE}/{ig_account_id}/media_publish",
            params={
                "access_token": access_token,
                "creation_id": container_id,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data.get("id")
