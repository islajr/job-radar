# Technical Design Document
## Job Radar — Personalised Remote Job Alert Service
**Version:** 2.0
**Status:** Draft
**Last Updated:** June 2026

---

## 1. System Overview

Job Radar is two independently deployed processes sharing one PostgreSQL database. They never call each other directly.

**Web Application** — A FastAPI backend serving a React SPA. Handles authentication, user profile management, the match dashboard, Telegram connection, and a GitHub Actions dispatch trigger for manual scraper runs. Deployed on Render (free tier).

**Scraper + Notifier** — A pure Python async process. Fetches listings from job boards, deduplicates, matches against all active user profiles, and dispatches notifications. Has no HTTP server. Runs entirely inside GitHub Actions on a cron schedule.

```
┌───────────────────────────────────────┐    ┌───────────────────────────────────┐
│           Web Application             │    │        Scraper + Notifier         │
│           (Render free tier)          │    │        (GitHub Actions cron)      │
│                                       │    │                                   │
│  FastAPI  ──►  React SPA (built)      │    │  asyncio.gather(                  │
│  /api/*   ◄──  fetch() from browser   │    │    remoteok(),                    │
│                                       │    │    himalayas(),                   │
│  Auth, Profile, Dashboard,            │    │    ycombinator(),                 │
│  Telegram webhook, GHA dispatch       │    │  )                                │
└──────────────────┬────────────────────┘    └────────────────┬──────────────────┘
                   │                                          │
                   │          Both read/write                 │
                   └─────────────────┬────────────────────────┘
                                     │
                           ┌─────────▼──────────┐
                           │  Supabase Postgres  │
                           │  (free tier)        │
                           └─────────────────────┘
```

---

## 2. Repository Structure

```
job-radar/
│
├── backend/                          # FastAPI application
│   ├── main.py                       # App factory, router registration, lifespan
│   ├── config.py                     # Pydantic-settings; all env vars in one place
│   ├── database.py                   # Async SQLAlchemy engine, session dependency
│   ├── models/                       # SQLAlchemy ORM models (one file per table group)
│   │   ├── user.py                   # User
│   │   ├── profile.py                # UserProfile, NotificationSettings
│   │   ├── listing.py                # Listing
│   │   └── match.py                  # UserMatch, ScraperRun
│   ├── schemas/                      # Pydantic request/response models
│   │   ├── auth.py                   # RegisterRequest, LoginRequest, SessionResponse
│   │   ├── profile.py                # ProfileUpdate, NotificationSettingsUpdate
│   │   ├── listing.py                # ListingOut, MatchOut
│   │   └── admin.py                  # AdminUserView, ScraperRunView
│   ├── routers/
│   │   ├── auth.py                   # POST /api/auth/register, /login, /logout, /reset-password
│   │   ├── profile.py                # GET/PUT /api/profile, GET/PUT /api/notifications
│   │   ├── dashboard.py              # GET /api/matches, PATCH /api/alerts/pause
│   │   ├── telegram.py               # POST /api/telegram/webhook, GET /api/telegram/connect
│   │                                 # GET /api/notifications/telegram-status
│   │   └── admin.py                  # GET /api/admin/*, POST /api/admin/trigger-scrape
│   ├── services/
│   │   ├── auth_service.py           # Password hashing, session token creation/validation
│   │   ├── telegram_service.py       # One-time token generation, deep link construction
│   │   └── dispatch_service.py       # GitHub Actions workflow dispatch via REST API
│   └── dependencies.py               # get_current_user, require_admin (FastAPI deps)
│
├── frontend/                         # React application (Vite)
│   ├── index.html
│   ├── vite.config.ts
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx                   # Router, auth context provider
│   │   ├── api/                      # Typed fetch wrappers (one file per domain)
│   │   │   ├── auth.ts
│   │   │   ├── profile.ts
│   │   │   ├── matches.ts
│   │   │   └── admin.ts
│   │   ├── pages/
│   │   │   ├── Landing.tsx
│   │   │   ├── Register.tsx
│   │   │   ├── Login.tsx
│   │   │   ├── Onboarding.tsx        # Multi-step; Step1Role, Step2Keywords, Step3Notifications
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Settings.tsx
│   │   │   └── Admin.tsx
│   │   ├── components/
│   │   │   ├── MatchCard.tsx
│   │   │   ├── KeywordInput.tsx      # Tag-style comma-separated input
│   │   │   ├── TelegramConnect.tsx   # Deep link display + polling logic
│   │   │   ├── AlertToggle.tsx
│   │   │   └── BoardStatus.tsx       # Stage 2
│   │   └── contexts/
│   │       └── AuthContext.tsx       # Stores current user, exposes login/logout
│
├── scraper/                          # Standalone scraper process
│   ├── main.py                       # Entry point; called by GitHub Actions
│   ├── config.py                     # Same env vars as backend/config.py (subset)
│   ├── database.py                   # Sync psycopg3 connection (no ORM needed here)
│   ├── boards/
│   │   ├── base.py                   # BaseScraper ABC, Listing dataclass
│   │   ├── remoteok.py
│   │   ├── himalayas.py
│   │   └── ycombinator.py
│   ├── deduplicator.py               # Fingerprint generation, batch upsert
│   ├── matcher.py                    # Keyword matching, user × listing cross-product
│   └── notifier/
│       ├── __init__.py               # dispatch_notifications(); asyncio.gather over channels
│       └── telegram.py               # Telegram Bot API calls, message formatting
│
├── migrations/                       # Alembic
│   ├── env.py
│   └── versions/
│       └── 0001_initial_schema.py
│
├── .github/
│   └── workflows/
│       ├── scraper.yml               # Cron: every 6h; env from secrets
│       └── digest.yml                # Cron: 07:00 UTC daily; runs notifier only
│
├── .env.example
├── alembic.ini
├── requirements.txt                  # Backend deps
├── requirements-scraper.txt          # Scraper deps (no FastAPI, no asyncpg)
└── README.md
```

---

## 3. Database

### 3.1 Full Schema

```sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─── Users ────────────────────────────────────────────────────────────────────

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           TEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    full_name       TEXT NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    is_admin        BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─── Profiles ─────────────────────────────────────────────────────────────────

CREATE TABLE user_profiles (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_title          TEXT,
    skills_summary      TEXT,                   -- free text; used in Stage 3 for LLM prompt
    experience_years    INT,
    inclusion_keywords  TEXT[] NOT NULL DEFAULT '{}',
    exclusion_keywords  TEXT[] NOT NULL DEFAULT '{}',
    salary_min          INT,                    -- Stage 2; NULL means no filter
    salary_max          INT,                    -- Stage 2; NULL means no filter
    work_type           TEXT NOT NULL DEFAULT 'remote',   -- 'remote' | 'hybrid' | 'any'
    preferred_regions   TEXT[] NOT NULL DEFAULT '{}',
    alerts_paused       BOOLEAN NOT NULL DEFAULT FALSE,
    onboarding_complete BOOLEAN NOT NULL DEFAULT FALSE,   -- gates dashboard access
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id)
);

-- ─── Notification settings ────────────────────────────────────────────────────

CREATE TABLE notification_settings (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    channels            TEXT[] NOT NULL DEFAULT '{"telegram"}',     -- ['telegram']
    frequency           TEXT NOT NULL DEFAULT 'immediate', -- 'immediate' | 'digest'
    telegram_chat_id    TEXT,
    telegram_connected  BOOLEAN NOT NULL DEFAULT FALSE,
    telegram_token      TEXT,                  -- short-lived connect token (32-byte random)
    telegram_token_exp  TIMESTAMPTZ,           -- 15 minutes from generation
    UNIQUE(user_id)
);

-- ─── Listings ─────────────────────────────────────────────────────────────────

CREATE TABLE listings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    board           TEXT NOT NULL,             -- 'remoteok' | 'himalayas' | 'ycombinator' | ...
    title           TEXT NOT NULL,
    company         TEXT,
    location        TEXT,
    description     TEXT,
    url             TEXT NOT NULL,
    salary_text     TEXT,                      -- raw string as returned by board; not normalised in Stage 1
    posted_at       TIMESTAMPTZ,               -- NULL if board does not provide it
    fingerprint     TEXT UNIQUE NOT NULL,      -- SHA-256(board|company_lower|title_lower)
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─── Matches ──────────────────────────────────────────────────────────────────

CREATE TABLE user_matches (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    listing_id      UUID NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    match_score     FLOAT,                     -- NULL in Stage 1; populated by LLM in Stage 3
    match_reason    TEXT,                      -- Stage 3; one-sentence LLM rationale
    notified_at     TIMESTAMPTZ,               -- NULL = not yet sent
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, listing_id)                -- prevents double-matching on re-run
);

-- ─── Scraper run log ──────────────────────────────────────────────────────────

CREATE TABLE scraper_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    board           TEXT NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL,
    completed_at    TIMESTAMPTZ,
    listings_found  INT NOT NULL DEFAULT 0,
    new_listings    INT NOT NULL DEFAULT 0,
    errors          TEXT,                      -- NULL on success; full traceback on failure
    status          TEXT NOT NULL DEFAULT 'running'  -- 'running' | 'success' | 'partial' | 'failed'
);

-- ─── Indexes ──────────────────────────────────────────────────────────────────

CREATE INDEX idx_listings_fingerprint  ON listings(fingerprint);
CREATE INDEX idx_listings_fetched_at   ON listings(fetched_at DESC);
CREATE INDEX idx_matches_user_id       ON user_matches(user_id);
CREATE INDEX idx_matches_unnotified    ON user_matches(user_id) WHERE notified_at IS NULL;
CREATE INDEX idx_scraper_runs_board    ON scraper_runs(board, started_at DESC);
```

### 3.2 Alembic Migration Setup

```bash
# Run once locally with DATABASE_URL set to Supabase connection string
alembic init migrations
# Edit migrations/env.py to import your SQLAlchemy Base and set target_metadata

alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

The `migrations/env.py` file must import all ORM models before `target_metadata` is set, otherwise Alembic does not detect the tables. A common pattern:

```python
# migrations/env.py
from backend.models.user import User       # noqa: F401
from backend.models.profile import UserProfile, NotificationSettings  # noqa: F401
from backend.models.listing import Listing # noqa: F401
from backend.models.match import UserMatch, ScraperRun  # noqa: F401
from backend.database import Base

target_metadata = Base.metadata
```

---

## 4. Backend — FastAPI

### 4.1 App Factory

```python
# backend/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from backend.database import init_db
from backend.routers import auth, profile, dashboard, telegram, admin

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()   # Verify DB connection on startup; do NOT run migrations here
    yield

app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)  # disable docs in prod

# API routes
app.include_router(auth.router,      prefix="/api/auth")
app.include_router(profile.router,   prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(telegram.router,  prefix="/api/telegram")
app.include_router(admin.router,     prefix="/api/admin")

# Serve the built React app for all non-API routes (SPA catch-all)
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
```

The React build output (`frontend/dist`) is committed to the repo or generated in the Render build step before `uvicorn` starts. The Render build command is:

```
cd frontend && npm ci && npm run build && cd .. && pip install -r requirements.txt
```

### 4.2 Configuration

```python
# backend/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str                         # Supabase connection string
    secret_key: str                           # Session signing; generate with secrets.token_hex(32)
    telegram_bot_token: str
    github_dispatch_token: str                # Fine-grained PAT with workflow scope
    github_repo: str                          # e.g. "username/job-radar"
    environment: str = "production"
    session_max_age_seconds: int = 604800     # 7 days

    class Config:
        env_file = ".env"

settings = Settings()
```

### 4.3 Database Layer

```python
# backend/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# Supabase uses postgres://; SQLAlchemy async requires postgresql+asyncpg://
DATABASE_URL = settings.database_url.replace("postgres://", "postgresql+asyncpg://")

engine = create_async_engine(DATABASE_URL, pool_size=5, max_overflow=0)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: c.execute("SELECT 1"))  # connection check only

async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
```

### 4.4 ORM Models

```python
# backend/models/user.py
from sqlalchemy import Column, String, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from backend.database import Base
import uuid

class User(Base):
    __tablename__ = "users"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email         = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name     = Column(String, nullable=False)
    is_active     = Column(Boolean, nullable=False, default=True)
    is_admin      = Column(Boolean, nullable=False, default=False)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
```

```python
# backend/models/profile.py
from sqlalchemy import Column, String, Boolean, Integer, DateTime, ARRAY, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from backend.database import Base
import uuid

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id             = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    role_title          = Column(String)
    skills_summary      = Column(String)
    experience_years    = Column(Integer)
    inclusion_keywords  = Column(ARRAY(String), nullable=False, default=list)
    exclusion_keywords  = Column(ARRAY(String), nullable=False, default=list)
    salary_min          = Column(Integer)
    salary_max          = Column(Integer)
    work_type           = Column(String, nullable=False, default="remote")
    preferred_regions   = Column(ARRAY(String), nullable=False, default=list)
    alerts_paused       = Column(Boolean, nullable=False, default=False)
    onboarding_complete = Column(Boolean, nullable=False, default=False)
    updated_at          = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

class NotificationSettings(Base):
    __tablename__ = "notification_settings"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id            = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    channels           = Column(ARRAY(String), nullable=False, default=lambda: ["telegram"])
    frequency          = Column(String, nullable=False, default="immediate")
    telegram_chat_id   = Column(String)
    telegram_connected = Column(Boolean, nullable=False, default=False)
    telegram_token     = Column(String)
    telegram_token_exp = Column(DateTime(timezone=True))
```

### 4.5 Pydantic Schemas

```python
# backend/schemas/auth.py
from pydantic import BaseModel, EmailStr

class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str           # min length validated in router

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class SessionResponse(BaseModel):
    id: str
    email: str
    full_name: str
    is_admin: bool
    onboarding_complete: bool
```

```python
# backend/schemas/profile.py
from pydantic import BaseModel
from typing import Optional

class ProfileUpdate(BaseModel):
    role_title:         Optional[str]         = None
    skills_summary:     Optional[str]         = None
    experience_years:   Optional[int]         = None
    inclusion_keywords: Optional[list[str]]   = None
    exclusion_keywords: Optional[list[str]]   = None
    salary_min:         Optional[int]         = None
    salary_max:         Optional[int]         = None
    work_type:          Optional[str]         = None
    preferred_regions:  Optional[list[str]]   = None
    alerts_paused:      Optional[bool]        = None

class NotificationSettingsUpdate(BaseModel):
    channels:   Optional[list[str]] = None    # ['telegram']
    frequency:  Optional[str]       = None    # 'immediate' | 'digest'
```

```python
# backend/schemas/listing.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class MatchOut(BaseModel):
    id:           str
    listing_id:   str
    title:        str
    company:      Optional[str]
    location:     Optional[str]
    url:          str
    salary_text:  Optional[str]
    board:        str
    created_at:   datetime

    class Config:
        from_attributes = True
```

### 4.6 Authentication

Sessions use signed cookies via `itsdangerous`. The cookie holds a serialised user UUID, signed with `SECRET_KEY`. No JWT. No refresh tokens. Session lifetime is 7 days by default.

```python
# backend/services/auth_service.py
from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from backend.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_serializer = URLSafeTimedSerializer(settings.secret_key)

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_session_token(user_id: str) -> str:
    return _serializer.dumps(user_id, salt="session")

def decode_session_token(token: str) -> str | None:
    """Returns user_id string, or None if invalid/expired."""
    try:
        return _serializer.loads(
            token,
            salt="session",
            max_age=settings.session_max_age_seconds
        )
    except (BadSignature, SignatureExpired):
        return None
```

```python
# backend/dependencies.py
from fastapi import Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_db
from backend.models.user import User
from backend.services.auth_service import decode_session_token

async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    token = request.cookies.get("session")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_id = decode_session_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Session expired")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")
    return user

async def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    return user
```

### 4.7 Auth Router

```python
# backend/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_db
from backend.models.user import User
from backend.models.profile import UserProfile, NotificationSettings
from backend.schemas.auth import RegisterRequest, LoginRequest, SessionResponse
from backend.services.auth_service import hash_password, verify_password, create_session_token
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
        httponly=True, secure=True, samesite="lax",
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
    response.set_cookie("session", token, httponly=True, secure=True, samesite="lax",
                        max_age=settings.session_max_age_seconds)
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
```

### 4.8 Telegram Router

```python
# backend/routers/telegram.py
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from backend.database import get_db
from backend.models.user import User
from backend.models.profile import NotificationSettings
from backend.services.telegram_service import generate_connect_token, build_deep_link, send_telegram_message
from backend.dependencies import get_current_user

router = APIRouter()

@router.get("/connect")
async def get_connect_link(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate a one-time connect token and return a Telegram deep link."""
    token, expiry = generate_connect_token()

    result = await db.execute(select(NotificationSettings).where(NotificationSettings.user_id == user.id))
    ns = result.scalar_one()
    ns.telegram_token = token
    ns.telegram_token_exp = expiry
    await db.commit()

    return {"deep_link": build_deep_link(token), "expires_at": expiry.isoformat()}

@router.get("/status")
async def telegram_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Polled by the frontend every 3s while the user completes Telegram connection."""
    result = await db.execute(select(NotificationSettings).where(NotificationSettings.user_id == user.id))
    ns = result.scalar_one()
    return {"connected": ns.telegram_connected}

@router.post("/webhook")
async def telegram_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Receives all messages sent to the bot.
    Only /start <token> is handled. All other messages get a generic reply.
    This route must NOT require authentication — Telegram calls it directly.
    """
    data = await request.json()
    message = data.get("message", {})
    text = message.get("text", "")
    chat_id = str(message.get("chat", {}).get("id", ""))

    if not chat_id:
        return {"ok": True}

    if text.startswith("/start "):
        token = text.split(" ", 1)[1].strip()
        result = await db.execute(
            select(NotificationSettings).where(
                NotificationSettings.telegram_token == token,
                NotificationSettings.telegram_token_exp > datetime.utcnow()
            )
        )
        ns = result.scalar_one_or_none()

        if ns:
            ns.telegram_chat_id = chat_id
            ns.telegram_connected = True
            ns.telegram_token = None
            ns.telegram_token_exp = None
            await db.commit()
            await send_telegram_message(chat_id, "✅ Connected! You'll receive job alerts here.")
        else:
            await send_telegram_message(chat_id, "That link has expired or is invalid. Please reconnect from the app.")
    else:
        await send_telegram_message(chat_id, "Hi! Manage your job alerts at the Job Radar app.")

    return {"ok": True}
```

### 4.9 Telegram Service

```python
# backend/services/telegram_service.py
import secrets
from datetime import datetime, timedelta
import httpx
from backend.config import settings

BOT_USERNAME = "YourBotUsername"   # Set in config; omit @

def generate_connect_token() -> tuple[str, datetime]:
    token = secrets.token_urlsafe(32)
    expiry = datetime.utcnow() + timedelta(minutes=15)
    return token, expiry

def build_deep_link(token: str) -> str:
    return f"https://t.me/{BOT_USERNAME}?start={token}"

async def send_telegram_message(chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        })
```

### 4.10 Admin — GitHub Actions Dispatch

The admin "Run scraper now" button POSTs to `/api/admin/trigger-scrape`, which calls the GitHub REST API to dispatch a `workflow_dispatch` event on `scraper.yml`. This requires a fine-grained personal access token with `Actions: write` scope stored as `GITHUB_DISPATCH_TOKEN`.

```python
# backend/services/dispatch_service.py
import httpx
from backend.config import settings

async def trigger_scraper_workflow() -> bool:
    url = f"https://api.github.com/repos/{settings.github_repo}/actions/workflows/scraper.yml/dispatches"
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {settings.github_dispatch_token}",
                "Accept": "application/vnd.github+json",
            },
            json={"ref": "main"},
        )
    return response.status_code == 204  # GitHub returns 204 on success
```

---

## 5. Frontend — React (Vite + TypeScript)

### 5.1 Tooling and Dependencies

```json
// Relevant package.json dependencies
{
  "dependencies": {
    "react": "^18",
    "react-dom": "^18",
    "react-router-dom": "^6",
    "react-query": "^5"
  },
  "devDependencies": {
    "@types/react": "^18",
    "typescript": "^5",
    "vite": "^5"
  }
}
```

No UI component library in Stage 1 — plain CSS modules keep the bundle small and give full control over the minimal UI. Add a library in Stage 2 or 3 if the UI grows complex.

### 5.2 Vite Config (API Proxy for Development)

During development, the React dev server runs on port 5173 and the FastAPI server on port 8000. Configure a proxy so `fetch("/api/...")` calls in the browser go to FastAPI without CORS issues:

```typescript
// vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
```

In production this is irrelevant — FastAPI serves the built React app from `frontend/dist` at the same origin.

### 5.3 Auth Context

```typescript
// src/contexts/AuthContext.tsx
import { createContext, useContext, useState, useEffect, ReactNode } from "react";

interface User {
  id: string;
  email: string;
  full_name: string;
  is_admin: boolean;
  onboarding_complete: boolean;
}

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  setUser: (u: User | null) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // On mount, check if a valid session cookie exists
    fetch("/api/auth/me")
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => setUser(data))
      .finally(() => setLoading(false));
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
```

### 5.4 Router Setup

```typescript
// src/App.tsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import Landing from "./pages/Landing";
import Register from "./pages/Register";
import Login from "./pages/Login";
import Onboarding from "./pages/Onboarding";
import Dashboard from "./pages/Dashboard";
import Settings from "./pages/Settings";
import Admin from "./pages/Admin";

function ProtectedRoute({ children }: { children: JSX.Element }) {
  const { user, loading } = useAuth();
  if (loading) return <div>Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (!user.onboarding_complete) return <Navigate to="/onboarding" replace />;
  return children;
}

function AdminRoute({ children }: { children: JSX.Element }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user?.is_admin) return <Navigate to="/dashboard" replace />;
  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/"           element={<Landing />} />
          <Route path="/register"   element={<Register />} />
          <Route path="/login"      element={<Login />} />
          <Route path="/onboarding" element={<Onboarding />} />
          <Route path="/dashboard"  element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/settings"   element={<ProtectedRoute><Settings /></ProtectedRoute>} />
          <Route path="/admin"      element={<AdminRoute><Admin /></AdminRoute>} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
```

### 5.5 API Layer

All backend calls go through typed wrapper functions. No raw `fetch()` calls in components.

```typescript
// src/api/auth.ts
export async function registerUser(body: { full_name: string; email: string; password: string }) {
  const res = await fetch("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw await res.json();
  return res.json();
}

export async function loginUser(body: { email: string; password: string }) {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw await res.json();
  return res.json();
}

export async function logoutUser() {
  await fetch("/api/auth/logout", { method: "POST" });
}
```

```typescript
// src/api/matches.ts
export async function getMatches(): Promise<Match[]> {
  const res = await fetch("/api/matches");
  if (!res.ok) throw await res.json();
  return res.json();
}

export async function toggleAlertPause(paused: boolean) {
  const res = await fetch("/api/alerts/pause", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ paused }),
  });
  if (!res.ok) throw await res.json();
  return res.json();
}
```

### 5.6 Onboarding Flow

The onboarding page is a single-page multi-step form. State lives in the component; no global state management needed.

```typescript
// src/pages/Onboarding.tsx (structure only)
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

type Step = 1 | 2 | 3;

export default function Onboarding() {
  const [step, setStep] = useState<Step>(1);
  const [role, setRole] = useState({ role_title: "", experience_years: "" });
  const [keywords, setKeywords] = useState({ inclusion: [], exclusion: [], summary: "" });
  const [notifications, setNotifications] = useState({ channels: [], frequency: "immediate" });
  const { setUser } = useAuth();
  const navigate = useNavigate();

  async function handleFinish() {
    // PATCH /api/profile with role + keywords
    // PATCH /api/notifications with channels + frequency
    // PATCH /api/profile with { onboarding_complete: true }
    // setUser(updatedUser)
    // navigate("/dashboard")
  }

  return (
    <div>
      {step === 1 && <Step1Role data={role} onChange={setRole} onNext={() => setStep(2)} />}
      {step === 2 && <Step2Keywords data={keywords} onChange={setKeywords} onBack={() => setStep(1)} onNext={() => setStep(3)} />}
      {step === 3 && <Step3Notifications data={notifications} onChange={setNotifications} onBack={() => setStep(2)} onFinish={handleFinish} />}
    </div>
  );
}
```

### 5.7 Telegram Connect Component

The connect flow involves polling — the React component shows the deep link, then polls `/api/telegram/status` every 3 seconds until connected or the 2-minute timeout expires.

```typescript
// src/components/TelegramConnect.tsx
import { useState, useEffect, useRef } from "react";

export default function TelegramConnect({ onConnected }: { onConnected: () => void }) {
  const [deepLink, setDeepLink] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "waiting" | "connected" | "timeout">("idle");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  async function startConnect() {
    const res = await fetch("/api/telegram/connect");
    const data = await res.json();
    setDeepLink(data.deep_link);
    setStatus("waiting");

    let elapsed = 0;
    pollRef.current = setInterval(async () => {
      elapsed += 3;
      if (elapsed > 120) {
        clearInterval(pollRef.current!);
        setStatus("timeout");
        return;
      }
      const statusRes = await fetch("/api/telegram/status");
      const statusData = await statusRes.json();
      if (statusData.connected) {
        clearInterval(pollRef.current!);
        setStatus("connected");
        onConnected();
      }
    }, 3000);
  }

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  return (
    <div>
      {status === "idle" && (
        <button onClick={startConnect}>Connect Telegram</button>
      )}
      {status === "waiting" && deepLink && (
        <div>
          <p>1. Click the button below to open your Telegram bot.</p>
          <a href={deepLink} target="_blank" rel="noreferrer">Open in Telegram</a>
          <p>2. Press Start in Telegram. This page will update automatically.</p>
          <p>Waiting for connection...</p>
        </div>
      )}
      {status === "connected" && <p>✅ Telegram connected!</p>}
      {status === "timeout" && (
        <div>
          <p>Connection timed out. Please try again.</p>
          <button onClick={startConnect}>Try again</button>
        </div>
      )}
    </div>
  );
}
```

---

## 6. Scraper

### 6.1 Entry Point

The scraper's `main.py` is called directly by GitHub Actions. It owns the full run lifecycle: fetch → deduplicate → match → notify → log.

```python
# scraper/main.py
import asyncio
import logging
from scraper.boards.remoteok import RemoteOKScraper
from scraper.boards.himalayas import HimalayasScraper
from scraper.boards.ycombinator import YCScraper
from scraper.deduplicator import deduplicate_and_store
from scraper.matcher import match_all_users
from scraper.notifier import dispatch_immediate_notifications
from scraper.database import get_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

SCRAPERS = [RemoteOKScraper, HimalayasScraper, YCScraper]

async def run():
    db = get_connection()

    # Run all scrapers concurrently; failures are captured, not raised
    results = await asyncio.gather(
        *[cls().fetch(db) for cls in SCRAPERS],
        return_exceptions=True
    )

    all_listings = []
    for scraper_cls, result in zip(SCRAPERS, results):
        if isinstance(result, Exception):
            log.error(f"[{scraper_cls.board_name}] Failed: {result}")
        else:
            log.info(f"[{scraper_cls.board_name}] Fetched {len(result)} listings")
            all_listings.extend(result)

    new_listings = deduplicate_and_store(db, all_listings)
    log.info(f"New listings stored: {len(new_listings)}")

    if new_listings:
        matches = match_all_users(db, new_listings)
        log.info(f"Matches found: {len(matches)}")
        dispatch_immediate_notifications(db, matches)

    db.close()

if __name__ == "__main__":
    asyncio.run(run())
```

### 6.2 Listing Dataclass and Base Scraper

```python
# scraper/boards/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import logging

log = logging.getLogger(__name__)

@dataclass
class Listing:
    board:        str
    title:        str
    url:          str
    company:      Optional[str] = None
    location:     Optional[str] = None
    description:  Optional[str] = None
    salary_text:  Optional[str] = None
    posted_at:    Optional[datetime] = None

class BaseScraper(ABC):
    board_name: str = ""

    @abstractmethod
    async def fetch(self, db) -> list[Listing]:
        """
        Fetch all current listings from the board.
        Must log a scraper_runs row on both success and failure.
        Must not raise — return an empty list on failure and log the error.
        """
        ...

    def _start_run(self, db) -> str:
        """Insert a scraper_runs row with status='running'. Returns the run ID."""
        from datetime import datetime
        result = db.execute(
            """INSERT INTO scraper_runs (board, started_at, status)
               VALUES (%s, %s, 'running') RETURNING id""",
            (self.board_name, datetime.utcnow())
        ).fetchone()
        db.commit()
        return result[0]

    def _end_run(self, db, run_id: str, found: int, new: int, error: str = None):
        from datetime import datetime
        status = "failed" if error and found == 0 else ("partial" if error else "success")
        db.execute(
            """UPDATE scraper_runs
               SET completed_at=%s, listings_found=%s, new_listings=%s, errors=%s, status=%s
               WHERE id=%s""",
            (datetime.utcnow(), found, new, error, status, run_id)
        )
        db.commit()
```

### 6.3 RemoteOK Scraper

RemoteOK's API prepends one metadata object to the JSON array. All real job objects have a `"slug"` key; the metadata object does not. The `User-Agent` header is required — the API returns 403 without it.

```python
# scraper/boards/remoteok.py
import httpx
from datetime import datetime
from scraper.boards.base import BaseScraper, Listing
import logging

log = logging.getLogger(__name__)

class RemoteOKScraper(BaseScraper):
    board_name = "remoteok"
    _URL = "https://remoteok.com/remote-jobs.json"
    _HEADERS = {"User-Agent": "job-radar/1.0 (personal aggregator)"}

    async def fetch(self, db) -> list[Listing]:
        run_id = self._start_run(db)
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(self._URL, headers=self._HEADERS)
                response.raise_for_status()
                data = response.json()

            jobs = [item for item in data if item.get("slug")]

            listings = []
            for job in jobs:
                salary = None
                lo, hi = job.get("salary_min"), job.get("salary_max")
                if lo and hi:
                    salary = f"${lo:,} – ${hi:,}"

                listings.append(Listing(
                    board=self.board_name,
                    title=job.get("position", "").strip(),
                    company=job.get("company"),
                    location=job.get("location") or "Remote",
                    description=job.get("description"),
                    url=job.get("url") or f"https://remoteok.com/l/{job['slug']}",
                    salary_text=salary,
                    posted_at=datetime.utcfromtimestamp(job["epoch"]) if job.get("epoch") else None,
                ))

            self._end_run(db, run_id, found=len(listings), new=0)  # 'new' updated by deduplicator
            return listings

        except Exception as e:
            self._end_run(db, run_id, found=0, new=0, error=str(e))
            log.error(f"[remoteok] {e}")
            return []
```

### 6.4 Himalayas Scraper

```python
# scraper/boards/himalayas.py
import httpx
from scraper.boards.base import BaseScraper, Listing
import logging

log = logging.getLogger(__name__)

class HimalayasScraper(BaseScraper):
    board_name = "himalayas"
    _URL = "https://himalayas.app/jobs/api?limit=100"

    async def fetch(self, db) -> list[Listing]:
        run_id = self._start_run(db)
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(self._URL)
                response.raise_for_status()
                data = response.json()

            jobs = data.get("jobs", [])
            listings = [
                Listing(
                    board=self.board_name,
                    title=job.get("title", "").strip(),
                    company=job.get("company", {}).get("name"),
                    location="Remote",
                    description=job.get("description"),
                    url=job.get("applicationLink") or job.get("url", ""),
                    salary_text=None,
                    posted_at=None,
                )
                for job in jobs
            ]

            self._end_run(db, run_id, found=len(listings), new=0)
            return listings

        except Exception as e:
            self._end_run(db, run_id, found=0, new=0, error=str(e))
            log.error(f"[himalayas] {e}")
            return []
```

### 6.5 YC Jobs Scraper

YC Jobs is server-rendered HTML. The selectors below are correct as of June 2026 but should be verified against the live page before first run. If the page structure changes, only this file needs updating.

```python
# scraper/boards/ycombinator.py
import httpx
from bs4 import BeautifulSoup
from scraper.boards.base import BaseScraper, Listing
import logging

log = logging.getLogger(__name__)

class YCScraper(BaseScraper):
    board_name = "ycombinator"
    _URL = "https://www.ycombinator.com/jobs"

    async def fetch(self, db) -> list[Listing]:
        run_id = self._start_run(db)
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                response = await client.get(self._URL)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            listings = []

            # Each job is in a <div class="flex flex-row ..."> wrapping an <a> tag
            # Selectors must be validated against the live page
            for card in soup.select("div.job"):
                title_el = card.select_one("a.job-name")
                company_el = card.select_one("span.company-name")
                link_el = card.select_one("a")

                if not title_el:
                    continue

                href = link_el["href"] if link_el else ""
                url = ("https://www.ycombinator.com" + href) if href.startswith("/") else href

                listings.append(Listing(
                    board=self.board_name,
                    title=title_el.text.strip(),
                    company=company_el.text.strip() if company_el else None,
                    location="Remote",
                    description=None,   # YC Jobs does not expose description in listing view
                    url=url,
                    salary_text=None,
                    posted_at=None,
                ))

            self._end_run(db, run_id, found=len(listings), new=0)
            return listings

        except Exception as e:
            self._end_run(db, run_id, found=0, new=0, error=str(e))
            log.error(f"[ycombinator] {e}")
            return []
```

### 6.6 Deduplicator

```python
# scraper/deduplicator.py
import hashlib
from scraper.boards.base import Listing

def make_fingerprint(listing: Listing) -> str:
    """
    Deterministic fingerprint for deduplication.
    Combines board + company + title, all lowercased, to handle
    the same job appearing across multiple runs.
    Does NOT include date — jobs re-posted with the same title/company
    are treated as duplicates, which is the desired behaviour.
    """
    raw = "|".join([
        listing.board,
        (listing.company or "").lower().strip(),
        listing.title.lower().strip(),
    ])
    return hashlib.sha256(raw.encode()).hexdigest()

def deduplicate_and_store(db, listings: list[Listing]) -> list[dict]:
    """
    For each listing, attempt an INSERT. If the fingerprint already exists,
    skip (ON CONFLICT DO NOTHING). Return only newly inserted listings as dicts
    with their DB-assigned UUIDs, for the matcher to consume.
    """
    new_listings = []

    for listing in listings:
        fp = make_fingerprint(listing)
        result = db.execute("""
            INSERT INTO listings
                (board, title, company, location, description, url, salary_text, posted_at, fingerprint)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (fingerprint) DO NOTHING
            RETURNING id
        """, (
            listing.board, listing.title, listing.company, listing.location,
            listing.description, listing.url, listing.salary_text,
            listing.posted_at, fp
        )).fetchone()
        db.commit()

        if result:  # None means the ON CONFLICT path was taken — already exists
            new_listings.append({
                "id": str(result[0]),
                "board": listing.board,
                "title": listing.title,
                "company": listing.company,
                "location": listing.location,
                "description": listing.description,
                "url": listing.url,
                "salary_text": listing.salary_text,
            })

    return new_listings
```

### 6.7 Matcher

The matcher performs a cross-product of new listings × active users. It is intentionally simple in Stage 1 — the matching logic lives in one function that can be swapped for LLM scoring in Stage 3 without changing the surrounding structure.

```python
# scraper/matcher.py
import logging

log = logging.getLogger(__name__)

def listing_matches_profile(listing: dict, profile: dict) -> bool:
    """
    Returns True if the listing passes the user's keyword filters.
    Matching is against a concatenation of title, description, and company.
    Case-insensitive. Partial word match is intentional.
    """
    if profile.get("alerts_paused"):
        return False

    searchable = " ".join(filter(None, [
        listing.get("title", ""),
        listing.get("description") or "",
        listing.get("company") or "",
    ])).lower()

    inclusion = [kw.lower().strip() for kw in profile.get("inclusion_keywords", []) if kw.strip()]
    exclusion = [kw.lower().strip() for kw in profile.get("exclusion_keywords", []) if kw.strip()]

    if inclusion and not any(kw in searchable for kw in inclusion):
        return False

    if any(kw in searchable for kw in exclusion):
        return False

    return True

def match_all_users(db, new_listings: list[dict]) -> list[dict]:
    """
    Cross-product of new_listings × active users.
    Inserts matching rows into user_matches (ON CONFLICT DO NOTHING handles
    re-runs safely). Returns match records for users on 'immediate' frequency.
    """
    users = db.execute("""
        SELECT
            u.id, u.email,
            up.inclusion_keywords, up.exclusion_keywords, up.alerts_paused,
            ns.channels, ns.frequency, ns.telegram_chat_id, ns.telegram_connected
        FROM users u
        JOIN user_profiles up ON up.user_id = u.id
        JOIN notification_settings ns ON ns.user_id = u.id
        WHERE u.is_active = TRUE
          AND up.alerts_paused = FALSE
          AND up.onboarding_complete = TRUE
    """).fetchall()

    immediate_matches = []

    for listing in new_listings:
        for user in users:
            profile = {
                "inclusion_keywords": user.inclusion_keywords,
                "exclusion_keywords": user.exclusion_keywords,
                "alerts_paused": user.alerts_paused,
            }

            if not listing_matches_profile(listing, profile):
                continue

            db.execute("""
                INSERT INTO user_matches (user_id, listing_id)
                VALUES (%s, %s)
                ON CONFLICT (user_id, listing_id) DO NOTHING
            """, (user.id, listing["id"]))
            db.commit()

            if user.frequency == "immediate":
                immediate_matches.append({
                    "user_id": str(user.id),
                    "listing_id": listing["id"],
                    "listing": listing,
                    "channels": user.channels or [],
                    "telegram_chat_id": user.telegram_chat_id if user.telegram_connected else None,
                    "email": user.email,
                })

    log.info(f"Total immediate matches to notify: {len(immediate_matches)}")
    return immediate_matches
```

### 6.8 Notifier

```python
# scraper/notifier/__init__.py
import asyncio
import logging
from scraper.notifier.telegram import send_telegram_message, format_listing_telegram

log = logging.getLogger(__name__)

async def _send_one(match: dict) -> None:
    tasks = []
    listing = match["listing"]

    if "telegram" in match["channels"] and match.get("telegram_chat_id"):
        tasks.append(send_telegram_message(
            chat_id=match["telegram_chat_id"],
            text=format_listing_telegram(listing)
        ))

    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                log.error(f"Notification failed for user {match['user_id']}: {r}")

def dispatch_immediate_notifications(db, matches: list[dict]) -> None:
    async def run():
        await asyncio.gather(*[_send_one(m) for m in matches], return_exceptions=True)
        # Mark all as notified in one round-trip
        for m in matches:
            db.execute(
                "UPDATE user_matches SET notified_at = now() WHERE user_id = %s AND listing_id = %s",
                (m["user_id"], m["listing_id"])
            )
        db.commit()

    asyncio.run(run())
```

```python
# scraper/notifier/telegram.py
import httpx
from scraper.config import settings

_API = f"https://api.telegram.org/bot{settings.telegram_bot_token}"

async def send_telegram_message(chat_id: str, text: str) -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(f"{_API}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        })
        response.raise_for_status()

def format_listing_telegram(listing: dict) -> str:
    salary = f"\n💰 {listing['salary_text']}" if listing.get("salary_text") else ""
    company = listing.get("company") or "Unknown company"
    location = listing.get("location") or "Remote"
    board = listing.get("board", "").capitalize()
    return (
        f"<b>{listing['title']}</b>\n"
        f"🏢 {company}\n"
        f"📍 {location}"
        f"{salary}\n"
        f"📋 via {board}\n"
        f"🔗 <a href=\"{listing['url']}\">View listing →</a>"
    )
```

```python
# scraper/notifier/email.py (Removed)
# Email notifier is removed as alerts are sent via Telegram exclusively.
```

---

## 7. Daily Digest

The digest is a separate GitHub Actions workflow that runs at 07:00 UTC daily. It does not re-run the scraper — it only looks at `user_matches WHERE notified_at IS NULL` for users with `frequency = 'digest'`, formats all pending matches into a single message per user, and dispatches.

```python
# scraper/digest.py  (entry point for digest.yml workflow)
import asyncio
import logging
from scraper.database import get_connection
from scraper.notifier.telegram import send_telegram_message

log = logging.getLogger(__name__)

async def send_digest():
    db = get_connection()

    pending = db.execute("""
        SELECT
            u.id AS user_id, u.email,
            um.listing_id, um.id AS match_id,
            l.title, l.company, l.location, l.url, l.salary_text, l.board,
            ns.channels, ns.telegram_chat_id, ns.telegram_connected, ns.frequency
        FROM user_matches um
        JOIN users u ON u.id = um.user_id
        JOIN listings l ON l.id = um.listing_id
        JOIN notification_settings ns ON ns.user_id = u.id
        JOIN user_profiles up ON up.user_id = u.id
        WHERE um.notified_at IS NULL
          AND ns.frequency = 'digest'
          AND up.alerts_paused = FALSE
          AND u.is_active = TRUE
        ORDER BY u.id, um.created_at
    """).fetchall()

    # Group by user
    from collections import defaultdict
    by_user: dict[str, list] = defaultdict(list)
    for row in pending:
        by_user[str(row.user_id)].append(row)

    tasks = []
    match_ids_to_mark = []

    for user_id, rows in by_user.items():
        channels = rows[0].channels or []
        telegram_chat_id = rows[0].telegram_chat_id if rows[0].telegram_connected else None

        listings = [dict(r._mapping) for r in rows]
        match_ids_to_mark.extend([r.match_id for r in rows])

        if "telegram" in channels and telegram_chat_id:
            text = f"📋 <b>Your daily job digest — {len(listings)} new match(es)</b>\n\n"
            for i, l in enumerate(listings, 1):
                salary = f" · {l['salary_text']}" if l.get("salary_text") else ""
                text += f"{i}. <b>{l['title']}</b> at {l.get('company','?')}{salary}\n<a href=\"{l['url']}\">View →</a>\n\n"
            tasks.append(send_telegram_message(telegram_chat_id, text))

    await asyncio.gather(*tasks, return_exceptions=True)

    # Mark all as notified
    for match_id in match_ids_to_mark:
        db.execute("UPDATE user_matches SET notified_at = now() WHERE id = %s", (match_id,))
    db.commit()
    db.close()
    log.info(f"Digest sent to {len(by_user)} user(s), covering {len(match_ids_to_mark)} match(es)")

if __name__ == "__main__":
    asyncio.run(send_digest())
```

---

## 8. GitHub Actions Workflows

### 8.1 Scraper (every 6 hours)

```yaml
# .github/workflows/scraper.yml
name: Job Radar — Scraper

on:
  schedule:
    - cron: '0 */6 * * *'
  workflow_dispatch:          # Allows manual trigger from admin UI and from GitHub

jobs:
  scrape:
    runs-on: ubuntu-latest
    timeout-minutes: 15

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: pip

      - name: Install dependencies
        run: pip install -r requirements-scraper.txt

      - name: Run scraper
        env:
          DATABASE_URL:       ${{ secrets.DATABASE_URL }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
        run: python -m scraper.main
```

### 8.2 Digest (daily at 07:00 UTC)

```yaml
# .github/workflows/digest.yml
name: Job Radar — Daily Digest

on:
  schedule:
    - cron: '0 7 * * *'
  workflow_dispatch:

jobs:
  digest:
    runs-on: ubuntu-latest
    timeout-minutes: 5

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: pip

      - name: Install dependencies
        run: pip install -r requirements-scraper.txt

      - name: Send digest
        env:
          DATABASE_URL:       ${{ secrets.DATABASE_URL }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
        run: python -m scraper.digest
```

---

## 9. Deployment

### 9.1 First-Time Setup Sequence

Follow this order. Doing it out of order (e.g. deploying the app before running migrations) will cause startup errors.

1. **Create Supabase project.** Copy the connection string from Project Settings → Database → URI. It begins with `postgres://`.

2. **Run migrations locally.** Set `DATABASE_URL` in `.env`, then:
   ```bash
   alembic upgrade head
   ```

3. **Create Telegram bot.** Message `@BotFather` on Telegram: `/newbot`. Copy the token. Note the bot's username (without `@`).

4. **Create GitHub repository.** Keep it private. Add repository secrets:
   - `DATABASE_URL`
   - `TELEGRAM_BOT_TOKEN`

5. **(Removed)** Resend setup is no longer required.

6. **Deploy to Render.** Connect the repository. Set the following:
   - Build command: `cd frontend && npm ci && npm run build && cd .. && pip install -r requirements.txt`
   - Start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - Environment variables (same values as GitHub secrets, plus `SECRET_KEY` and `GITHUB_DISPATCH_TOKEN`)

7. **Register the Telegram webhook.** Run once after Render deployment:
   ```bash
   curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://<your-render-url>.onrender.com/api/telegram/webhook"}'
   ```
   Verify with:
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
   ```

8. **Create the first admin account.** Register via the app UI, then in Supabase SQL Editor:
   ```sql
   UPDATE users SET is_admin = TRUE WHERE email = 'your@email.com';
   ```

9. **Trigger the first manual scraper run** from the admin dashboard or GitHub Actions tab.

### 9.2 Environment Variables Reference

| Variable | Used By | How to Get |
|---|---|---|
| `DATABASE_URL` | Backend, Scraper | Supabase → Project Settings → Database → URI |
| `SECRET_KEY` | Backend | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `TELEGRAM_BOT_TOKEN` | Backend, Scraper | BotFather → `/newbot` |
| `GITHUB_DISPATCH_TOKEN` | Backend | GitHub → Settings → Developer Settings → Fine-grained PAT → Actions: write |
| `GITHUB_REPO` | Backend | `"yourusername/job-radar"` |

### 9.3 Local Development Setup

```bash
# Clone and install
git clone https://github.com/yourname/job-radar
cd job-radar

# Backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Fill in real values

# Run migrations
alembic upgrade head

# Start FastAPI
uvicorn backend.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev    # Proxies /api to localhost:8000
```

---

## 10. Dependency Lists

### Backend (`requirements.txt`)

```
fastapi>=0.111.0
uvicorn[standard]>=0.30.0
sqlalchemy[asyncio]>=2.0.30
asyncpg>=0.29.0
alembic>=1.13.1
passlib[bcrypt]>=1.7.4
itsdangerous>=2.2.0
httpx>=0.27.0
pydantic>=2.7.0
pydantic-settings>=2.2.1
python-multipart>=0.0.9
```

### Scraper (`requirements-scraper.txt`)

```
httpx>=0.27.0
beautifulsoup4>=4.12.3
psycopg[binary]>=3.1.19
pydantic-settings>=2.2.1
```

Playwright is intentionally absent from Stage 1. It will be added to this file in Stage 3 when the Wellfound scraper is introduced.

---

## 11. Error Handling and Known Failure Modes

### 11.1 Scraper Resilience

Each board scraper is wrapped in a try/except. `asyncio.gather(..., return_exceptions=True)` in `main.py` ensures one board failure does not abort the others. Every run writes a `scraper_runs` row regardless of outcome.

### 11.2 Silent Degradation

The most dangerous failure mode is a scraper that runs successfully but returns 0 results because a page structure changed. This looks like "no new jobs today" to the user. The admin view flags any board that has returned 0 listings in its last three consecutive runs.

### 11.3 Duplicate Notification Prevention

The `UNIQUE(user_id, listing_id)` constraint on `user_matches` means that even if the scraper runs twice in quick succession (e.g. a manual trigger overlapping a cron trigger), a match is never inserted twice. Notifications are only dispatched for rows where `notified_at IS NULL`, so a crash mid-dispatch cannot cause re-sending on the next run for already-notified matches.

### 11.4 Render Cold-Start

Render free tier sleeps after 15 minutes of inactivity. The first request after sleep takes 20–40 seconds. The React app should display a loading skeleton rather than a blank screen during this time. Onboarding documentation should set this expectation for users.

### 11.5 Telegram Webhook Conflicts

Only one webhook URL can be registered per bot token at a time. If you test locally using polling (`getUpdates`), you must first delete the webhook:
```bash
curl "https://api.telegram.org/bot<TOKEN>/deleteWebhook"
```
Then re-register the Render webhook after finishing local testing.

---

## 12. Stage 2 — What Changes

Stage 2 adds user board selection and salary filtering. No architectural changes are required; both features are additive.

**Board selection:** Add a `enabled_boards TEXT[]` column to `user_profiles`. The matcher filters listings by checking `listing["board"] in user.enabled_boards` before running keyword matching. The scraper still fetches all boards regardless. The Settings page gains a board toggle UI.

**Salary filtering:** The `salary_min` and `salary_max` columns already exist in the schema. Stage 2 adds parsing logic in the matcher to extract numeric values from `salary_text` strings, compare against the user's range, and skip listings outside it when salary data is present.

---

## 13. Stage 3 — What Changes

Stage 3 introduces LLM-assisted scoring, Wellfound scraping, and optionally LinkedIn.

**LLM scoring:** Add `match_score FLOAT` and `match_reason TEXT` columns to `user_matches` (already in schema). After keyword matching, submit `(user.skills_summary, listing.description)` to the Claude API with a structured prompt. Store the score and reason. Add a `minimum_match_score FLOAT` column to `user_profiles`. Notifications are only sent for matches above the user's threshold.

**Wellfound:** Add `requirements-scraper.txt` entry for `playwright>=1.44.0`. Add `playwright install chromium` to the GitHub Actions install step. Add `WellfoundScraper` to `SCRAPERS` list in `main.py`. The scraper implementation uses `async_playwright` with a shared browser instance per run.

**LinkedIn:** Evaluated in Stage 3. If included, it runs as a separate optional scraper with an explicit rate-limit delay between page requests (minimum 5 seconds), a `User-Agent` rotation list, and a hard failure cap — if the scraper fails 3 consecutive times, it disables itself and alerts the admin rather than being silently degraded.
