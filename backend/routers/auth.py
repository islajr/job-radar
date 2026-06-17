from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_db
from backend.models.user import User
from backend.models.profile import UserProfile, NotificationSettings
from backend.schemas.auth import RegisterRequest, LoginRequest, SessionResponse
from backend.services.auth_service import hash_password, verify_password, create_session_token
from backend.dependencies import get_current_user
from backend.config import settings

router = APIRouter()

@router.post("/register", response_model=SessionResponse)
async def register(body: RegisterRequest, response: Response, db: AsyncSession = Depends(get_db)):
    if len(body.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")

    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Email already registered")

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
    )
    db.add(user)
    await db.flush()  # get user.id before committing

    # Create empty profile and notification settings rows immediately
    db.add(UserProfile(user_id=user.id))
    db.add(NotificationSettings(user_id=user.id))
    await db.commit()
    await db.refresh(user)

    token = create_session_token(str(user.id))
    response.set_cookie(
        "session", token,
        httponly=True, secure=settings.environment == "production", samesite="lax",
        max_age=settings.session_max_age_seconds
    )
    return SessionResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        is_admin=user.is_admin,
        onboarding_complete=False,
    )

@router.post("/login", response_model=SessionResponse)
async def login(body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")

    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )
    profile = profile_result.scalar_one_or_none()

    token = create_session_token(str(user.id))
    response.set_cookie(
        "session", token,
        httponly=True, secure=settings.environment == "production", samesite="lax",
        max_age=settings.session_max_age_seconds
    )
    return SessionResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        is_admin=user.is_admin,
        onboarding_complete=profile.onboarding_complete if profile else False,
    )

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("session")
    return {"ok": True}

@router.get("/me", response_model=SessionResponse)
async def me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    profile_result = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    profile = profile_result.scalar_one_or_none()
    return SessionResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        is_admin=user.is_admin,
        onboarding_complete=profile.onboarding_complete if profile else False,
    )
