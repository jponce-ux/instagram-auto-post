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
