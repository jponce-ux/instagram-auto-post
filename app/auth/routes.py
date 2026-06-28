from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Form
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.config import settings
from app.auth.security import verify_password, get_password_hash, create_access_token
from app.auth.dependencies import get_current_user_optional
from app.auth.tokens import decode_verification_token, create_verification_token
from app.auth.schemas import UserRegister, Token
from app.models.user import User
from app.services.email import EmailService

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/login")
async def login_page(
    request: Request,
    user: User | None = Depends(get_current_user_optional),
):
    """Login page with router guard for authenticated users."""
    if user:
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse(request=request, name="auth/login.html")


@router.get("/register")
async def register_page(
    request: Request,
    user: User | None = Depends(get_current_user_optional),
):
    """Registration page with router guard for authenticated users."""
    if user:
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse(request=request, name="auth/register.html")


@router.get("/confirm-email")
async def confirm_email_page(
    request: Request,
    user: User | None = Depends(get_current_user_optional),
):
    """Confirm email page with router guard for authenticated users."""
    if user:
        return RedirectResponse(url="/dashboard", status_code=303)
    error = request.query_params.get("error")
    return templates.TemplateResponse(
        request=request,
        name="auth/confirm_email.html",
        context={"error": error},
    )


@router.get("/verify-email/{token}")
async def verify_email(
    request: Request,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Verify email using token from verification link."""
    payload = decode_verification_token(token)

    if payload is None:
        # Token is expired or invalid
        return RedirectResponse(
            url="/auth/confirm-email?error=expired",
            status_code=303,
        )

    user_id = int(payload.get("sub"))

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        return RedirectResponse(
            url="/auth/confirm-email?error=invalid",
            status_code=303,
        )

    if user.is_verified:
        # Already verified, just redirect to login
        return RedirectResponse(
            url="/auth/login?verified=1",
            status_code=303,
        )

    # Mark as verified
    from sqlalchemy.sql import func
    user.is_verified = True
    user.verified_at = func.now()
    await db.commit()

    return RedirectResponse(
        url="/auth/login?verified=1",
        status_code=303,
    )


@router.post("/resend-verification-email")
async def resend_verification_email(
    request: Request,
    email: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Resend verification email with rate limiting (1 per 2 minutes per email)."""
    # Check rate limit via Redis
    import redis
    from app.core.config import settings

    try:
        r = redis.Redis.from_url(settings.CELERY_BROKER_URL)
        rate_key = f"resend:{email}"
        if r.exists(rate_key):
            ttl = r.ttl(rate_key)
            return JSONResponse(
                content={"error": f"Espera {ttl} segundos antes de solicitar otro email"},
                status_code=429,
            )
    except Exception:
        # Redis unavailable — allow resend but log warning
        pass

    # Check user exists and is not verified
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        return JSONResponse(
            content={"error": "Si el email existe, se enviará un nuevo enlace"},
            status_code=200,
        )

    if user.is_verified:
        return JSONResponse(
            content={"error": "Tu cuenta ya está verificada. Puedes iniciar sesión."},
            status_code=400,
        )

    # Generate new token and send email
    EmailService.send_verification_email(
        to=email,
        user_name=email.split("@")[0],
        user_id=user.id,
    )

    # Set rate limit
    try:
        r.setex(rate_key, 120, "1")
    except Exception:
        pass

    return JSONResponse(
        content={"message": "Correo de verificación enviado. Revisa tu bandeja de entrada."},
        status_code=200,
    )


@router.post("/register")
async def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    if password != password_confirm:
        return RedirectResponse(url="/auth/register?error=1", status_code=303)

    result = await db.execute(select(User).where(User.email == email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        return RedirectResponse(url="/auth/register?error=1", status_code=303)

    hashed_password = get_password_hash(password)
    user = User(
        email=email,
        hashed_password=hashed_password,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Send verification email asynchronously (non-blocking via Celery)
    EmailService.send_verification_email(to=email, user_name=email.split("@")[0], user_id=user.id)

    return RedirectResponse(url="/auth/confirm-email", status_code=303)


@router.post("/login")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Login endpoint - returns redirect with cookie for server-side authentication."""
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        return RedirectResponse(url="/auth/login?error=1", status_code=303)

    if not user.is_verified:
        return RedirectResponse(
            url="/auth/confirm-email?error=not_verified",
            status_code=303,
        )

    access_token = create_access_token(data={"sub": user.email})

    response = RedirectResponse(url="/dashboard", status_code=303)
    max_age = settings.SESSION_COOKIE_MAX_AGE_DAYS * 86400
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=max_age,
    )
    return response


@router.get("/logout")
async def logout():
    """Logout endpoint - clears the access_token cookie and redirects to /."""
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("access_token")
    return response
