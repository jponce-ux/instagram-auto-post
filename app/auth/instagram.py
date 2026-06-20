from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
import logging

from app.core.config import settings
from app.core.database import get_db
from app.auth.dependencies import get_current_user_optional
from app.models.instagram import InstagramAccount
from app.services.instagram import (
    exchange_short_token,
    get_long_lived_token,
    get_instagram_account_id,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/instagram", tags=["instagram"])


@router.get("/login")
async def instagram_login():
    if settings.META_LOGIN_URL:
        return RedirectResponse(url=settings.META_LOGIN_URL)
    redirect_uri = f"{settings.BASE_URL}/auth/instagram/callback"
    auth_url = (
        f"https://www.instagram.com/oauth/authorize"
        f"?force_reauth=true"
        f"&client_id={settings.META_APP_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope=instagram_business_basic,instagram_business_manage_messages,instagram_business_manage_comments,instagram_business_content_publish,instagram_business_manage_insights"
    )
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def instagram_callback(
    code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    redirect_uri = settings.META_REDIRECT_URI or f"{settings.BASE_URL}/auth/instagram/callback"

    # User must be logged in to connect an Instagram account
    current_user = await get_current_user_optional(request, db)
    if current_user is None:
        # Save the callback URL so we can redirect back after login
        # The code param is single-use, so we can't re-use it after login.
        # Redirect to login with a message explaining the situation.
        return RedirectResponse(
            url="/auth/login?error=session_expired",
            status_code=303,
        )

    try:
        short_token_data = await exchange_short_token(code, redirect_uri)
        short_token = short_token_data["access_token"]

        long_token_data = await get_long_lived_token(short_token)
        long_token = long_token_data["access_token"]
        expires_in = long_token_data.get("expires_in", 5184000)

        instagram_account_id, ig_username = await get_instagram_account_id(long_token)

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
            existing_account.username = ig_username or existing_account.username
            # Reactivate account if it was deactivated due to token expiry
            if not existing_account.is_active:
                existing_account.is_active = True
                logger.info(f"Instagram account {existing_account.id} reactivated after OAuth reconnection")
        else:
            instagram_account = InstagramAccount(
                user_id=current_user.id,
                instagram_account_id=instagram_account_id,
                username=ig_username,
                access_token=long_token,
                token_expires_at=token_expires_at,
            )
            db.add(instagram_account)

        await db.commit()
    except Exception as e:
        logger.error(f"Instagram OAuth callback failed: {e}", exc_info=True)
        return RedirectResponse(
            url="/dashboard?error=instagram_auth_failed", status_code=303
        )

    return RedirectResponse(url="/dashboard?success=instagram_connected", status_code=303)
