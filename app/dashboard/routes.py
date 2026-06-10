from fastapi import APIRouter, Depends, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.auth.dependencies import get_current_user_optional
from app.models.user import User
from app.dashboard.service import get_user_accounts, get_user_posts, create_post, get_post_image_url
from app.services.sse import sse_manager, POST_UPDATE_CHANNEL

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")


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

    Includes presigned image URLs for each post's thumbnail.
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
        posts_data.append(post_data)

    return JSONResponse(
        content={"posts": posts_data}
    )


@router.get("/posts/stream")
async def posts_stream(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Server-Sent Events stream for real-time post status updates.

    Subscribes to Redis pub/sub channel and forwards events to the client.
    Filters events to only include posts belonging to the authenticated user.
    Sends heartbeats every 15 seconds to keep the connection alive.
    """
    user = await get_current_user_optional(request, db)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    async def event_generator():
        async for event in sse_manager.subscribe(POST_UPDATE_CHANNEL):
            # Filter: only forward events for this user
            if event.startswith(":heartbeat"):
                yield event
                continue
            try:
                # Parse the SSE event to check user_id
                # Format: "event: post_update\ndata: {...}\n\n"
                data_line = event.split("data: ")[1].strip()
                event_data = __import__("json").loads(data_line)
                if event_data.get("user_id") == user.id:
                    yield event
            except Exception:
                # If parsing fails, forward anyway (safe fallback)
                yield event

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
