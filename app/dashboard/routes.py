from fastapi import APIRouter, Depends, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
import re
import logging
from datetime import time

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.auth.dependencies import get_current_user_optional
from app.models.user import User
from app.dashboard.service import (
    get_user_accounts, get_user_posts, create_post, get_post_image_url, retry_post,
    create_scheduled_post, get_scheduled_posts, update_scheduled_post, delete_scheduled_post,
    get_hashtag_collections, create_hashtag_collection, update_hashtag_collection, delete_hashtag_collection,
    get_content_templates, create_content_template, update_content_template, delete_content_template,
    get_recurring_schedules, create_recurring_schedule, update_recurring_schedule,
    pause_recurring_schedule, resume_recurring_schedule, delete_recurring_schedule,
    calculate_best_times, extract_placeholders, validate_placeholders,
    get_analytics_overview, get_top_performing_posts, get_media_insights,
)
from app.services.sse import sse_manager, POST_UPDATE_CHANNEL, ACCOUNT_UPDATE_CHANNEL
from app.services.metrics import metrics_service, TokenError, APIError

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


def _is_htmx_request(request: Request) -> bool:
    """Check if the request is an HTMX partial page request."""
    return request.headers.get("hx-request", "").lower() == "true"


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

    # HTMX requests return only the content fragment
    if _is_htmx_request(request):
        return templates.TemplateResponse(
            request=request,
            name="dashboard/partials/dashboard-content.html",
            context={
                "user": user,
                "accounts": accounts,
                "posts": posts,
            },
        )

    # Full page request
    return templates.TemplateResponse(
        request=request,
        name="dashboard/index.html",
        context={
            "user": user,
            "accounts": accounts,
            "posts": posts,
        },
    )


@router.get("/analytics")
async def analytics_page(
    request: Request,
    period: str = "days_28",
    db: AsyncSession = Depends(get_db),
):
    """Full-page Analytics dashboard with charts and trend indicators."""
    user = await get_current_user_optional(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=303)

    # HTMX requests return only the content fragment
    if _is_htmx_request(request):
        return templates.TemplateResponse(
            request=request,
            name="dashboard/partials/analytics-content.html",
            context={
                "user": user,
                "period": period,
            },
        )

    return templates.TemplateResponse(
        request=request,
        name="dashboard/analytics.html",
        context={
            "user": user,
            "period": period,
        },
    )


# ============================================================
# Analytics HTMX Partial Routes (spec-026)
# ============================================================

@router.get("/analytics/kpis")
async def analytics_kpis_partial(
    request: Request,
    period: str = "days_28",
    db: AsyncSession = Depends(get_db),
):
    """Return KPI cards partial for HTMX swap."""
    user = await get_current_user_optional(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=303)

    analytics_data = await get_analytics_overview(db, user, period)

    return templates.TemplateResponse(
        request=request,
        name="dashboard/partials/kpi_cards.html",
        context={
            "user": user,
            "analytics": analytics_data,
            "period": period,
        },
    )


@router.get("/analytics/reach-chart")
async def analytics_reach_chart_partial(
    request: Request,
    period: str = "days_28",
    db: AsyncSession = Depends(get_db),
):
    """Return reach line chart partial for HTMX swap."""
    user = await get_current_user_optional(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=303)

    analytics_data = await get_analytics_overview(db, user, period)

    return templates.TemplateResponse(
        request=request,
        name="dashboard/partials/reach_chart.html",
        context={
            "user": user,
            "analytics": analytics_data,
            "period": period,
        },
    )


@router.get("/analytics/growth-chart")
async def analytics_growth_chart_partial(
    request: Request,
    period: str = "days_28",
    db: AsyncSession = Depends(get_db),
):
    """Return follower growth bar chart partial for HTMX swap."""
    user = await get_current_user_optional(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=303)

    analytics_data = await get_analytics_overview(db, user, period)

    return templates.TemplateResponse(
        request=request,
        name="dashboard/partials/growth_chart.html",
        context={
            "user": user,
            "analytics": analytics_data,
            "period": period,
        },
    )


@router.get("/analytics/top-content")
async def analytics_top_content_partial(
    request: Request,
    period: str = "days_28",
    limit: int = 6,
    db: AsyncSession = Depends(get_db),
):
    """Return top content grid partial for HTMX swap."""
    user = await get_current_user_optional(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=303)

    posts = await get_top_performing_posts(db, user, limit)

    return templates.TemplateResponse(
        request=request,
        name="dashboard/partials/top_content.html",
        context={
            "user": user,
            "posts": posts,
            "period": period,
        },
    )


@router.get("/analytics/media/{post_id}")
async def analytics_media_modal(
    post_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Return detailed analytics modal for a specific post."""
    user = await get_current_user_optional(request, db)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    try:
        media_data = await get_media_insights(db, user, post_id)
    except ValueError as e:
        return JSONResponse(status_code=404, content={"error": str(e)})

    return templates.TemplateResponse(
        request=request,
        name="dashboard/partials/post_analytics_modal.html",
        context={
            "user": user,
            "media": media_data,
        },
    )


@router.get("/schedule")
async def schedule_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Schedule (Agenda) view for managing scheduled posts."""
    user = await get_current_user_optional(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=303)

    accounts = await get_user_accounts(db, user)
    scheduled_posts = await get_scheduled_posts(db, user)

    # Generate presigned URLs for each scheduled post's thumbnail
    for post in scheduled_posts:
        post.image_urls = await get_post_image_url(db, user, post)

    # Minimum selectable date for the schedule form (today, UTC, ISO format)
    from datetime import datetime, timezone
    min_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # HTMX requests return only the content fragment
    if _is_htmx_request(request):
        return templates.TemplateResponse(
            request=request,
            name="dashboard/partials/schedule-content.html",
            context={"user": user, "accounts": accounts, "scheduled_posts": scheduled_posts, "min_date": min_date},
        )

    return templates.TemplateResponse(
        request=request,
        name="dashboard/schedule.html",
        context={"user": user, "accounts": accounts, "scheduled_posts": scheduled_posts, "min_date": min_date},
    )


@router.post("/schedule/post")
async def create_scheduled_post_endpoint(
    request: Request,
    caption: str = Form(""),
    scheduled_date: str = Form(...),
    scheduled_time: str = Form(...),
    ig_account_id: int = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Create a new scheduled post with future publish date.

    Returns JSON. Front-end refreshes the scheduled-posts list via
    GET /dashboard/schedule/list (see refreshScheduledPosts()).
    """
    user = await get_current_user_optional(request, db)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    if not file or not file.filename:
        return JSONResponse(status_code=400, content={"error": "Image is required"})

    # Parse scheduled datetime from form data
    try:
        from datetime import datetime, timezone
        scheduled_dt = datetime.strptime(
            f"{scheduled_date} {scheduled_time}",
            "%Y-%m-%d %H:%M"
        ).replace(tzinfo=timezone.utc)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "Invalid date/time format"})

    try:
        post = await create_scheduled_post(
            db=db,
            user=user,
            file=file,
            caption=caption,
            scheduled_at=scheduled_dt,
            ig_account_id=ig_account_id,
        )
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

    return JSONResponse(
        content={
            "success": True,
            "post": {
                "id": post.id,
                "caption": post.caption,
                "status": post.status.value,
                "scheduled_at": post.scheduled_at.isoformat() if post.scheduled_at else None,
            },
        }
    )


@router.get("/schedule/list")
async def schedule_list_partial(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Return only the scheduled-posts list HTML fragment.

    Used by the front-end after a successful create/update/delete to refresh
    the right-side panel without a full page reload.
    """
    user = await get_current_user_optional(request, db)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    scheduled_posts = await get_scheduled_posts(db, user)

    # Generate presigned URLs for each scheduled post's thumbnail
    for post in scheduled_posts:
        post.image_urls = await get_post_image_url(db, user, post)

    return templates.TemplateResponse(
        request=request,
        name="dashboard/partials/scheduled_posts_list.html",
        context={"user": user, "scheduled_posts": scheduled_posts},
    )


@router.patch("/schedule/post/{post_id}")
async def update_scheduled_post_endpoint(
    post_id: int,
    request: Request,
    caption: str = Form(None),
    scheduled_date: str = Form(None),
    scheduled_time: str = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Update a scheduled post's caption or scheduled time.

    Returns HTMX trigger to refresh the agenda list on success.
    """
    user = await get_current_user_optional(request, db)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    # Parse scheduled datetime if provided
    scheduled_at = None
    if scheduled_date and scheduled_time:
        try:
            from datetime import datetime, timezone
            scheduled_at = datetime.strptime(
                f"{scheduled_date} {scheduled_time}",
                "%Y-%m-%d %H:%M"
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            return JSONResponse(status_code=400, content={"error": "Invalid date/time format"})

    try:
        post = await update_scheduled_post(
            db=db,
            user=user,
            post_id=post_id,
            caption=caption,
            scheduled_at=scheduled_at,
        )
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

    return JSONResponse(
        content={
            "success": True,
            "post": {
                "id": post.id,
                "caption": post.caption,
                "status": post.status.value,
                "scheduled_at": post.scheduled_at.isoformat() if post.scheduled_at else None,
            },
        }
    )


@router.delete("/schedule/post/{post_id}")
async def delete_scheduled_post_endpoint(
    post_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Delete a scheduled post.

    Returns HTMX trigger to refresh the agenda list on success.
    """
    user = await get_current_user_optional(request, db)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    try:
        await delete_scheduled_post(db=db, user=user, post_id=post_id)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

    return JSONResponse(
        content={
            "success": True,
        }
    )


@router.get("/automation")
async def automation_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Automation view for managing automation tools."""
    user = await get_current_user_optional(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=303)

    # Fetch all automation data
    hashtags = await get_hashtag_collections(db, user)
    content_templates = await get_content_templates(db, user)
    schedules = await get_recurring_schedules(db, user)
    accounts = await get_user_accounts(db, user)
    best_times = await calculate_best_times(db, user)

    # HTMX requests return only the content fragment
    if _is_htmx_request(request):
        return templates.TemplateResponse(
            request=request,
            name="dashboard/partials/automation-content.html",
            context={
                "user": user,
                "hashtags": hashtags,
                "templates": content_templates,
                "schedules": schedules,
                "accounts": accounts,
                "best_times": best_times,
            },
        )

    return templates.TemplateResponse(
        request=request,
        name="dashboard/automation.html",
        context={
            "user": user,
            "hashtags": hashtags,
            "templates": content_templates,
            "schedules": schedules,
            "accounts": accounts,
            "best_times": best_times,
        },
    )


# ============================================================
# Hashtag Collections API
# ============================================================

@router.get("/automation/hashtags")
async def list_hashtags(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """List all hashtag collections for the user."""
    user = await get_current_user_optional(request, db)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    hashtags = await get_hashtag_collections(db, user)
    return JSONResponse(content={
        "hashtags": [
            {"id": h.id, "name": h.name, "hashtags": h.hashtags, "created_at": h.created_at.isoformat()}
            for h in hashtags
        ]
    })


@router.post("/automation/hashtags")
async def create_hashtag(
    request: Request,
    name: str = Form(...),
    hashtags: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Create a new hashtag collection."""
    user = await get_current_user_optional(request, db)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    try:
        collection = await create_hashtag_collection(db, user, name, hashtags)
        return JSONResponse(content={
            "success": True,
            "hashtag": {
                "id": collection.id,
                "name": collection.name,
                "hashtags": collection.hashtags,
                "created_at": collection.created_at.isoformat(),
            }
        })
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@router.put("/automation/hashtags/{hashtag_id}")
async def update_hashtag(
    request: Request,
    hashtag_id: int,
    name: str = Form(None),
    hashtags: str = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Update a hashtag collection."""
    user = await get_current_user_optional(request, db)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    try:
        collection = await update_hashtag_collection(db, user, hashtag_id, name, hashtags)
        return JSONResponse(content={
            "success": True,
            "hashtag": {
                "id": collection.id,
                "name": collection.name,
                "hashtags": collection.hashtags,
                "created_at": collection.created_at.isoformat(),
            }
        })
    except ValueError as e:
        return JSONResponse(status_code=404, content={"error": str(e)})


@router.delete("/automation/hashtags/{hashtag_id}")
async def delete_hashtag(
    request: Request,
    hashtag_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a hashtag collection."""
    user = await get_current_user_optional(request, db)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    try:
        await delete_hashtag_collection(db, user, hashtag_id)
        return JSONResponse(content={"success": True})
    except ValueError as e:
        return JSONResponse(status_code=404, content={"error": str(e)})


# ============================================================
# Content Templates API
# ============================================================

@router.get("/automation/templates")
async def list_templates(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """List all content templates for the user."""
    user = await get_current_user_optional(request, db)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    templates = await get_content_templates(db, user)
    return JSONResponse(content={
        "templates": [
            {
                "id": t.id,
                "name": t.name,
                "caption_template": t.caption_template,
                "placeholders": extract_placeholders(t.caption_template),
                "created_at": t.created_at.isoformat(),
            }
            for t in templates
        ]
    })


@router.post("/automation/templates")
async def create_template(
    request: Request,
    name: str = Form(...),
    caption_template: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Create a new content template."""
    user = await get_current_user_optional(request, db)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    # Validate template syntax
    errors = validate_placeholders(caption_template)
    if errors:
        return JSONResponse(status_code=400, content={"error": f"Invalid template: {errors[0]}"})

    try:
        template = await create_content_template(db, user, name, caption_template)
        return JSONResponse(content={
            "success": True,
            "template": {
                "id": template.id,
                "name": template.name,
                "caption_template": template.caption_template,
                "placeholders": extract_placeholders(template.caption_template),
                "created_at": template.created_at.isoformat(),
            }
        })
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@router.put("/automation/templates/{template_id}")
async def update_template(
    request: Request,
    template_id: int,
    name: str = Form(None),
    caption_template: str = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Update a content template."""
    user = await get_current_user_optional(request, db)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    # Validate template syntax if provided
    if caption_template:
        errors = validate_placeholders(caption_template)
        if errors:
            return JSONResponse(status_code=400, content={"error": f"Invalid template: {errors[0]}"})

    try:
        template = await update_content_template(db, user, template_id, name, caption_template)
        return JSONResponse(content={
            "success": True,
            "template": {
                "id": template.id,
                "name": template.name,
                "caption_template": template.caption_template,
                "placeholders": extract_placeholders(template.caption_template),
                "created_at": template.created_at.isoformat(),
            }
        })
    except ValueError as e:
        return JSONResponse(status_code=404, content={"error": str(e)})


@router.delete("/automation/templates/{template_id}")
async def delete_template(
    request: Request,
    template_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a content template."""
    user = await get_current_user_optional(request, db)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    try:
        await delete_content_template(db, user, template_id)
        return JSONResponse(content={"success": True})
    except ValueError as e:
        return JSONResponse(status_code=404, content={"error": str(e)})


# ============================================================
# Recurring Schedules API
# ============================================================

@router.get("/automation/schedules")
async def list_schedules(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """List all recurring schedules for the user."""
    user = await get_current_user_optional(request, db)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    schedules = await get_recurring_schedules(db, user)
    return JSONResponse(content={
        "schedules": [
            {
                "id": s.id,
                "ig_account_id": s.ig_account_id,
                "frequency": s.frequency,
                "time_of_day": s.time_of_day.isoformat() if s.time_of_day else None,
                "day_of_week": s.day_of_week,
                "template_id": s.template_id,
                "hashtag_collection_id": s.hashtag_collection_id,
                "is_active": s.is_active,
                "created_at": s.created_at.isoformat(),
            }
            for s in schedules
        ]
    })


@router.post("/automation/schedules")
async def create_schedule(
    request: Request,
    ig_account_id: int = Form(...),
    frequency: str = Form(...),
    time_of_day: str = Form(...),
    day_of_week: int = Form(None),
    template_id: int = Form(None),
    hashtag_collection_id: int = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Create a new recurring schedule."""
    user = await get_current_user_optional(request, db)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    # Parse time_of_day from HH:MM format
    try:
        hour, minute = map(int, time_of_day.split(":"))
        parsed_time = time(hour=hour, minute=minute)
    except (ValueError, AttributeError):
        return JSONResponse(status_code=400, content={"error": "Invalid time format. Use HH:MM"})

    if frequency not in ("daily", "weekly"):
        return JSONResponse(status_code=400, content={"error": "Frequency must be 'daily' or 'weekly'"})

    if frequency == "weekly" and day_of_week is None:
        return JSONResponse(status_code=400, content={"error": "day_of_week required for weekly frequency"})

    try:
        schedule = await create_recurring_schedule(
            db, user, ig_account_id, frequency, parsed_time,
            day_of_week, template_id, hashtag_collection_id,
        )
        return JSONResponse(content={
            "success": True,
            "schedule": {
                "id": schedule.id,
                "ig_account_id": schedule.ig_account_id,
                "frequency": schedule.frequency,
                "time_of_day": schedule.time_of_day.isoformat() if schedule.time_of_day else None,
                "day_of_week": schedule.day_of_week,
                "template_id": schedule.template_id,
                "hashtag_collection_id": schedule.hashtag_collection_id,
                "is_active": schedule.is_active,
                "created_at": schedule.created_at.isoformat(),
            }
        })
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@router.put("/automation/schedules/{schedule_id}")
async def update_schedule(
    request: Request,
    schedule_id: int,
    frequency: str = Form(None),
    time_of_day: str = Form(None),
    day_of_week: int = Form(None),
    template_id: int = Form(None),
    hashtag_collection_id: int = Form(None),
    is_active: bool = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Update a recurring schedule."""
    user = await get_current_user_optional(request, db)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    # Parse time_of_day from HH:MM format if provided
    parsed_time = None
    if time_of_day:
        try:
            hour, minute = map(int, time_of_day.split(":"))
            parsed_time = time(hour=hour, minute=minute)
        except (ValueError, AttributeError):
            return JSONResponse(status_code=400, content={"error": "Invalid time format. Use HH:MM"})

    try:
        schedule = await update_recurring_schedule(
            db, user, schedule_id, frequency, parsed_time,
            day_of_week, template_id, hashtag_collection_id, is_active,
        )
        return JSONResponse(content={
            "success": True,
            "schedule": {
                "id": schedule.id,
                "ig_account_id": schedule.ig_account_id,
                "frequency": schedule.frequency,
                "time_of_day": schedule.time_of_day.isoformat() if schedule.time_of_day else None,
                "day_of_week": schedule.day_of_week,
                "template_id": schedule.template_id,
                "hashtag_collection_id": schedule.hashtag_collection_id,
                "is_active": schedule.is_active,
                "created_at": schedule.created_at.isoformat(),
            }
        })
    except ValueError as e:
        return JSONResponse(status_code=404, content={"error": str(e)})


@router.post("/automation/schedules/{schedule_id}/pause")
async def pause_schedule(
    request: Request,
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Pause a recurring schedule."""
    user = await get_current_user_optional(request, db)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    try:
        schedule = await pause_recurring_schedule(db, user, schedule_id)
        return JSONResponse(content={
            "success": True,
            "schedule": {
                "id": schedule.id,
                "is_active": schedule.is_active,
            }
        })
    except ValueError as e:
        return JSONResponse(status_code=404, content={"error": str(e)})


@router.post("/automation/schedules/{schedule_id}/resume")
async def resume_schedule(
    request: Request,
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Resume a paused recurring schedule."""
    user = await get_current_user_optional(request, db)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    try:
        schedule = await resume_recurring_schedule(db, user, schedule_id)
        return JSONResponse(content={
            "success": True,
            "schedule": {
                "id": schedule.id,
                "is_active": schedule.is_active,
            }
        })
    except ValueError as e:
        return JSONResponse(status_code=404, content={"error": str(e)})


@router.delete("/automation/schedules/{schedule_id}")
async def delete_schedule(
    request: Request,
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a recurring schedule."""
    user = await get_current_user_optional(request, db)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    try:
        await delete_recurring_schedule(db, user, schedule_id)
        return JSONResponse(content={"success": True})
    except ValueError as e:
        return JSONResponse(status_code=404, content={"error": str(e)})


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
        result = await metrics_service.get_account_analytics_with_trend(
            instagram_account_id=account.instagram_account_id,
            account_id=account.id,
            period=period,
            access_token=account.access_token,
        )
        return JSONResponse(content=result)
    except TokenError as e:
        logger.error(f"Token error fetching account analytics: {e}")
        return JSONResponse(
            status_code=401,
            content={"error": "Instagram session expired. Please reconnect your account."},
        )
    except APIError as e:
        logger.error(f"API error fetching account analytics: {e}")
        return JSONResponse(
            status_code=502,
            content={"error": "Analytics temporarily unavailable. Please try again later."},
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching account analytics: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "An unexpected error occurred. Please try again later."},
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
    except TokenError as e:
        logger.error(f"Token error fetching media analytics for post {post_id}: {e}")
        return JSONResponse(
            status_code=401,
            content={"error": "Instagram session expired. Please reconnect your account."},
        )
    except APIError as e:
        logger.error(f"API error fetching media analytics for post {post_id}: {e}")
        return JSONResponse(
            status_code=502,
            content={"error": "Analytics temporarily unavailable. Please try again later."},
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching media analytics for post {post_id}: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "An unexpected error occurred. Please try again later."},
        )
