from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.instagram import InstagramAccount
from app.services.instagram import (
    exchange_short_token,
    get_long_lived_token,
    get_instagram_account_id,
)

router = APIRouter(prefix="/auth/instagram", tags=["instagram"])


@router.get("/login")
async def instagram_login():
    redirect_uri = f"{settings.BASE_URL}/auth/instagram/callback"
    auth_url = (
        f"https://www.facebook.com/v18.0/dialog/oauth"
        f"?client_id={settings.META_APP_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&scope=instagram_basic,instagram_manage_comments"
    )
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def instagram_callback(
    code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    redirect_uri = f"{settings.BASE_URL}/auth/instagram/callback"

    short_token_data = await exchange_short_token(code, redirect_uri)
    short_token = short_token_data["access_token"]

    long_token_data = await get_long_lived_token(short_token)
    long_token = long_token_data["access_token"]
    expires_in = long_token_data.get("expires_in", 5184000)

    instagram_account_id = await get_instagram_account_id(long_token)

    result = await db.execute(
        select(InstagramAccount).where(
            InstagramAccount.instagram_account_id == instagram_account_id
        )
    )
    existing_account = result.scalar_one_or_none()

    token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

    if existing_account:
        existing_account.access_token = long_token
        existing_account.token_expires_at = token_expires_at
    else:
        instagram_account = InstagramAccount(
            user_id=current_user.id,
            instagram_account_id=instagram_account_id,
            access_token=long_token,
            token_expires_at=token_expires_at,
        )
        db.add(instagram_account)

    await db.commit()

    return {"status": "success", "instagram_account_id": instagram_account_id}
