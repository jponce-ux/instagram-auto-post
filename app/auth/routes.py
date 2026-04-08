from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.auth.security import verify_password, get_password_hash, create_access_token
from app.auth.dependencies import get_current_user_optional
from app.auth.schemas import UserRegister, UserResponse, Token
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


@router.post("/register", response_model=UserResponse)
async def register(
    request: Request, user_data: UserRegister, db: AsyncSession = Depends(get_db)
):
    generic_error = "Error en el registro"

    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        return JSONResponse(
            content={"error": generic_error},
            status_code=400,
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
    """Login endpoint - returns redirect with cookie for server-side authentication."""
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        return RedirectResponse(url="/auth/login?error=1", status_code=303)

    access_token = create_access_token(data={"sub": user.email})

    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return response


@router.get("/logout")
async def logout():
    """Logout endpoint - clears the access_token cookie and redirects to /."""
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("access_token")
    return response
