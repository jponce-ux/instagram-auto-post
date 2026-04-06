from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.auth.security import verify_password, get_password_hash, create_access_token
from app.auth.dependencies import get_current_user_optional
from app.auth.schemas import UserRegister, UserResponse, Token
from app.auth.utils import is_htmx_request
from app.models.user import User

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


@router.get("/login-form")
async def login_form(request: Request):
    """HTMX endpoint returning login form partial."""
    return templates.TemplateResponse(
        request=request,
        name="components/auth_form.html",
        headers={"HX-Retarget": "#auth-form-box"},
    )


@router.get("/register-form")
async def register_form(request: Request):
    """HTMX endpoint returning register form partial."""
    return templates.TemplateResponse(
        request=request,
        name="components/register_form.html",
        headers={"HX-Retarget": "#auth-form-box"},
    )


@router.post("/register", response_model=UserResponse)
async def register(
    request: Request, user_data: UserRegister, db: AsyncSession = Depends(get_db)
):
    # Generic error message - don't reveal if email exists
    generic_error = "Error en el registro"

    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        if is_htmx_request(request):
            return HTMLResponse(
                content=f'<div id="register-error" class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">{generic_error}</div>',
                status_code=200,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=generic_error,
        )

    hashed_password = get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        hashed_password=hashed_password,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Login endpoint with HTMX support."""
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        # Handle HTMX vs regular request
        if is_htmx_request(request):
            # Return generic error - don't reveal if email exists or not
            return HTMLResponse(
                content='<div id="error-message" class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">Error de autenticacion</div>',
                status_code=200,
                headers={"HX-Reswap": "innerHTML"},
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Error de autenticacion",
        )

    access_token = create_access_token(data={"sub": user.email})

    # Handle HTMX vs regular request
    if is_htmx_request(request):
        # Return redirect header for HTMX
        response = HTMLResponse(
            content="<html><body>Redirecting...</body></html>", status_code=200
        )
        response.headers["HX-Redirect"] = "/dashboard"
        return response

    # Regular response - set cookie and redirect
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=False,  # Set to True in production
        samesite="lax",
    )
    return response


@router.get("/logout")
async def logout():
    """Logout endpoint - clears the access_token cookie and redirects to /."""
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("access_token")
    return response
