from fastapi import APIRouter, Depends, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
import re
import logging

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.auth.dependencies import get_current_user_optional
from app.models.user import User
from app.dashboard.service import get_user_accounts, get_user_posts, create_post, get_post_image_url, retry_post
from app.services.sse import sse_manager, POST_UPDATE_CHANNEL, ACCOUNT_UPDATE_CHANNEL
from app.services.metrics import metrics_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")


def _sanitize_error_message(error_msg: str) -> str:
    """Remove sensitive data from error messages before showing to users.

    Strips out tokens, internal paths, and technical details while keeping
    the user-facing error description.
    """
    if not error_msg:
        return ""

    sanitized = error_msg
    # Remove access tokens (long alphanumeric strings)
    sanitized = re.sub(r'access_token[=:]\s*[A-Za-z0-9_-]{20,}', 'access_token=[REDACTED]', sanitized)
    # Remove internal URLs with query params
    sanitized = re.sub(r'(https?://[^\s]+\?)[^\s]+', r'\1[REDACTED]', sanitized)
    # Remove Python tracebacks
    if 'Traceback (most recent call last)' in sanitized:
        sanitized = sanitized.split('Traceback')[0].strip()
    # Remove Instagram API error codes/types but keep the message
    sanitized = re.sub(r'Instagram API error \d+: \w+ — ', '', sanitized)
    # Remove common internal error patterns
    sanitized = re.sub(r'Failed to (create media container|publish media): ', '', sanitized)

    # Truncate if too long
    if len(sanitized) > 200:
        sanitized = sanitized[:197] + "..."

    return sanitized


@router.get("/")
async def dashboard_index(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Main dashboard page with accounts, post form, and history."""
    user = await get_current_user_optional(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=303)

    accounts = await get_user_accounts(db, user)
    posts = await get_user_posts(db, user)

    return templates.TemplateResponse(
        request=request,
        name="dashboard/index.html",
        context={
            "user": user,
            "accounts": accounts,
            "posts": posts,
        },
    )


@router.get("/accounts")
async def dashboard_accounts(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Linked accounts — returns JSON for AJAX/HTMX requests."""
    user = await get_current_user_optional(request, db)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    accounts = await get_user_accounts(db, user)

    return JSONResponse(
        content={
            "accounts": [
                {
                    "id": acc.id,
                    "instagram_account_id": acc.instagram_account_id,
                    "username": acc.username,
                    "is_active": acc.is_active,
                }
                for acc in accounts
            ]
        }
    )


@router.get("/posts/feed")
async def posts_feed(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Post history feed — returns JSON for initial load and fallback.

    Includes presigned image URLs for each post's thumbnail and error messages
    for failed/retrying posts (sanitized to remove sensitive data).
    """
    user = await get_current_user_optional(request, db)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    posts = await get_user_posts(db, user)

    # Generate presigned URLs for each post's thumbnail and full-size image
    posts_data = []
    for post in posts:
        image_urls = await get_post_image_url(db, user, post)
        post_data = {
            "id": post.id,
            "caption": post.caption,
            "status": post.status.value,
            "created_at": post.created_at.isoformat(),
        }
        if image_urls:
            post_data["thumbnail_url"] = image_urls["thumbnail_url"]
            post_data["full_image_url"] = image_urls["full_image_url"]
        else:
            post_data["thumbnail_url"] = None
            post_data["full_image_url"] = None

        # Include error message for failed/retrying posts (sanitized)
        if post.status.value in ("failed", "retrying") and post.error_message:
            post_data["error_message"] = _sanitize_error_message(post.error_message)
        else:
            post_data["error_message"] = None

        posts_data.append(post_data)

    return JSONResponse(
        content={"posts": posts_data}
    )


@router.get("/posts/stream")
async def posts_stream(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Server-Sent Events stream for real-time post and account status updates.

    Subscribes to Redis pub/sub channels (post_update + account_update)
    and forwards events to the client. Filters events to only include
    items belonging to the authenticated user.
    Sends heartbeats every 15 seconds to keep the connection alive.
    """
    user = await get_current_user_optional(request, db)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    import asyncio

    queue: asyncio.Queue = asyncio.Queue()

    async def forward_events(channel_name: str) -> None:
        """Subscribe to a channel and put filtered events into the queue."""
        try:
            async for event in sse_manager.subscribe(channel_name):
                if event.startswith(":heartbeat"):
                    await queue.put(event)
                    continue
                try:
                    data_line = event.split("data: ")[1].strip()
                    event_data = __import__("json").loads(data_line)
                    if event_data.get("user_id") == user.id:
                        await queue.put(event)
                except Exception:
                    await queue.put(event)
        except asyncio.CancelledError:
            pass

    # Start both channel subscribers as background tasks
    post_task = asyncio.create_task(forward_events(POST_UPDATE_CHANNEL))
    account_task = asyncio.create_task(forward_events(ACCOUNT_UPDATE_CHANNEL))

    async def event_generator():
        try:
            while not post_task.done() or not account_task.done():
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield event
                except asyncio.TimeoutError:
                    yield ":heartbeat\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            post_task.cancel()
            account_task.cancel()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.post("/post")
async def create_post_endpoint(
    request: Request,
    caption: str = Form(""),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Create a new post with image upload. Returns JSON."""
    user = await get_current_user_optional(request, db)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    if not file or not file.filename:
        return JSONResponse(status_code=400, content={"error": "Image is required"})

    try:
        post = await create_post(db, user, file, caption)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

    return JSONResponse(
        content={
            "success": True,
            "post": {
                "id": post.id,
                "caption": post.caption,
                "status": post.status.value,
                "created_at": post.created_at.isoformat(),
            },
        }
    )


@router.post("/accounts/reconnect")
async def reconnect_account(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Reconnect an inactive Instagram account by redirecting to OAuth flow.

    POST handler that redirects the user to /auth/instagram/login
    to start the Instagram OAuth flow for reconnection.
    """
    user = await get_current_user_optional(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=303)

    return RedirectResponse(url="/auth/instagram/login", status_code=303)


@router.post("/posts/{post_id}/retry")
async def retry_post_endpoint(
    post_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Retry a failed post by re-dispatching it to the Celery worker.

    Verifies user ownership, post state (must be FAILED), and account active status.
    Returns 200 on success, 400/401/404 on errors.
    """
    user = await get_current_user_optional(request, db)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    try:
        post = await retry_post(db, user, post_id)
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            return JSONResponse(status_code=404, content={"error": error_msg})
        return JSONResponse(status_code=400, content={"error": error_msg})

    return JSONResponse(
        content={
            "success": True,
            "post": {
                "id": post.id,
                "status": post.status.value,
                "error_message": post.error_message,
            },
        }
    )


@router.get("/analytics/account")
async def get_account_analytics(
    request: Request,
    period: str = "days_28",
    db: AsyncSession = Depends(get_db),
):
    """
    Get account-level Instagram insights.

    Returns cached data if available (< 1 hour old), otherwise fetches fresh
    from the Instagram Graph API.
    """
    user = await get_current_user_optional(request, db)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    # Get user's Instagram accounts
    accounts = await get_user_accounts(db, user)
    if not accounts:
        return JSONResponse(
            status_code=400,
            content={"error": "No Instagram account connected"},
        )

    # Use the first active account
    active_accounts = [acc for acc in accounts if acc.is_active]
    if not active_accounts:
        return JSONResponse(
            status_code=403,
            content={"error": "Instagram account is inactive. Please reconnect your account."},
        )

    account = active_accounts[0]

    try:
        result = await metrics_service.get_account_analytics(
            instagram_account_id=account.instagram_account_id,
            account_id=account.id,
            period=period,
            access_token=account.access_token,
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error fetching account analytics: {e}")
        return JSONResponse(
            status_code=502,
            content={"error": "Analytics temporarily unavailable. Please try again later."},
        )


@router.get("/analytics/media/{post_id}")
async def get_media_analytics(
    post_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Get media-level Instagram insights for a specific post (on-demand).

    Fetches from cache if available, otherwise calls the Instagram Graph API.
    """
    user = await get_current_user_optional(request, db)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    # Verify post ownership
    from sqlalchemy import select
    from app.models.post import Post, PostStatus

    result = await db.execute(
        select(Post).where(Post.id == post_id, Post.user_id == user.id)
    )
    post = result.scalar_one_or_none()
    if not post:
        return JSONResponse(status_code=404, content={"error": "Post not found"})

    # Check if post is published
    if post.status != PostStatus.PUBLISHED or not post.ig_media_id:
        return JSONResponse(
            status_code=400,
            content={"error": "Metrics not yet available for this post"},
        )

    # Check account is active
    accounts = await get_user_accounts(db, user)
    active_accounts = [acc for acc in accounts if acc.is_active]
    if not active_accounts:
        return JSONResponse(
            status_code=403,
            content={"error": "Instagram account is inactive. Please reconnect your account."},
        )

    account = active_accounts[0]

    try:
        result = await metrics_service.get_media_analytics(
            media_id=post.ig_media_id,
            access_token=account.access_token,
        )
        result["post_id"] = post.id
        result["ig_media_id"] = post.ig_media_id
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error fetching media analytics for post {post_id}: {e}")
        return JSONResponse(
            status_code=502,
            content={"error": "Analytics temporarily unavailable. Please try again later."},
        )
