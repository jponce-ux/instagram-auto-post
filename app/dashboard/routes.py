from fastapi import APIRouter, Depends, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.auth.dependencies import get_current_user_optional
from app.models.user import User
from app.dashboard.service import get_user_accounts, get_user_posts, create_post

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard", response_class=HTMLResponse)
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


@router.get("/dashboard/accounts", response_class=HTMLResponse)
async def dashboard_accounts(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Linked accounts section — returns fragment for HTMX or full page."""
    user = await get_current_user_optional(request, db)
    if user is None:
        return RedirectResponse(url="/", status_code=303)

    accounts = await get_user_accounts(db, user)

    # Check if this is an HTMX request for partial content
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            request=request,
            name="dashboard/accounts_partial.html",
            context={"accounts": accounts},
        )

    return templates.TemplateResponse(
        request=request,
        name="dashboard/accounts.html",
        context={"accounts": accounts, "user": user},
    )


@router.get("/dashboard/posts/feed", response_class=HTMLResponse)
async def posts_feed(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Post history feed — HTMX fragment with polling support."""
    user = await get_current_user_optional(request, db)
    if user is None:
        return RedirectResponse(url="/", status_code=303)

    posts = await get_user_posts(db, user)

    return templates.TemplateResponse(
        request=request,
        name="dashboard/posts_feed.html",
        context={"posts": posts},
    )


@router.post("/dashboard/post", response_class=HTMLResponse)
async def create_post_endpoint(
    request: Request,
    caption: str = Form(""),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Create a new post with image upload via HTMX form submission."""
    user = await get_current_user_optional(request, db)
    if user is None:
        return RedirectResponse(url="/", status_code=303)
    # Validate that a file was provided
    if not file or not file.filename:
        return templates.TemplateResponse(
            request=request,
            name="dashboard/post_form.html",
            context={"error": "Image is required"},
        )

    post = await create_post(db, user, file, caption)

    # Return success feedback with the new post
    return templates.TemplateResponse(
        request=request,
        name="dashboard/post_form.html",
        context={"success": True, "post": post},
    )
