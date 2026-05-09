from fastapi import APIRouter, Depends, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.auth.dependencies import get_current_user_optional
from app.models.user import User
from app.dashboard.service import get_user_accounts, get_user_posts, create_post

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
    """Post history feed — returns JSON for HTMX polling."""
    user = await get_current_user_optional(request, db)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    posts = await get_user_posts(db, user)

    return JSONResponse(
        content={
            "posts": [
                {
                    "id": post.id,
                    "caption": post.caption,
                    "status": post.status.value,
                    "created_at": post.created_at.isoformat(),
                }
                for post in posts
            ]
        }
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

    post = await create_post(db, user, file, caption)

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
