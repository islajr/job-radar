# Job Radar — Hand-off / Pick-up Guide

This guide details the current state of the Job Radar codebase, the changes implemented relative to the Approved Implementation Plan, and the checklist of actions required to deploy and activate the application.

---

## 📝 Implementation Changelog

Relative to the Approved [Implementation Plan](file:///home/isla-jr/.gemini/antigravity-cli/brain/b64e7686-4299-4a27-aa21-157f94dd39d0/implementation_plan.md), the following changes have been fully built, tested, and validated:

### 1. Database & Migrations (Tier 1)
- Provisioned local PostgreSQL schema using SQLAlchemy ORM models.
- Configured **[Alembic](file:///home/isla-jr/Documents/se-workspace/job-radar/alembic.ini)** to read `DATABASE_URL` dynamically from the environment.
- Applied the initial schema migration version `c72111f75db6`.

### 2. Backend FastAPI Application (Tier 2)
- Implemented core auth, user profile, and notification settings routers.
- **Bcrypt compatibility fix**: Replaced `passlib` context hashing with the modern direct `bcrypt` library, resolving runtime exceptions with Python 3.14 on newer systems.
- Created `/api/profile/test-email` endpoint to dispatch integration test notifications using the Resend API.
- Completely removed all Telegram webhook and connection status endpoints.

### 3. Frontend React App (Tier 3)
- Built Vite-TS dark-mode Apple system design interface (Auth, Guided Onboarding, Keywords Tag Input, and Settings panel).
- Resolved all type-safety compiler and CSS selector errors.
- **Global Header**: Created a global unified **[Header.tsx](file:///home/isla-jr/Documents/se-workspace/job-radar/frontend/src/components/Header.tsx)** navigation bar displaying active route highlights, dynamic session actions, the theme toggle, and Sign Out triggers.
- **Email Verification**: Redesigned Onboarding Step 3 and Settings to show a clean Email Alerts card containing a "Send Test Email" test button.

### 4. Scraper Engine (Tier 4)
- **[ycombinator.py](file:///home/isla-jr/Documents/se-workspace/job-radar/scraper/boards/ycombinator.py)**: Scrapes listings by parsing YC's embedded `data-page` JSON object, ensuring extreme stability against DOM shifts.
- **[remoteok.py](file:///home/isla-jr/Documents/se-workspace/job-radar/scraper/boards/remoteok.py)**: Updated endpoint to `/api` and enabled redirects to fetch correctly.
- **[deduplicator.py](file:///home/isla-jr/Documents/se-workspace/job-radar/scraper/deduplicator.py)**: Deterministically filters duplicates using SHA-256 hashes of `board|company|title`.
- **[matcher.py](file:///home/isla-jr/Documents/se-workspace/job-radar/scraper/matcher.py)**: Cross-references new listings with active users based on their keyword profiles.
- **Robust UUIDs**: Modified database insertions to generate UUID keys in Python, preventing `NotNullViolation` errors since database primary keys do not have default server-side generators.
- **Resend Notifier**: Implemented **[resend_notifier.py](file:///home/isla-jr/Documents/se-workspace/job-radar/scraper/notifier/resend_notifier.py)** to dispatch clean, responsive macOS/iOS-style HTML emails for immediate alerts.
- **[digest.py](file:///home/isla-jr/Documents/se-workspace/job-radar/scraper/digest.py)**: Aggregates daily summaries for digest-configured users and dispatches single compiled HTML email summaries via Resend.

### 5. Workflows & Configuration (Tier 5)
- Created **[scraper.yml](file:///home/isla-jr/Documents/se-workspace/job-radar/.github/workflows/scraper.yml)** (runs every 6 hours/manually) and **[digest.yml](file:///home/isla-jr/Documents/se-workspace/job-radar/.github/workflows/digest.yml)** (runs daily at 07:00 UTC).
- Updated **[README.md](file:///home/isla-jr/Documents/se-workspace/job-radar/README.md)** with clear setup, tech stack, and scraper execution details.

---

## 🚀 Next Steps: Operational Checklist

Follow these steps to deploy the application, configure Resend email notifications, and set up automated scraper cron schedules.

### Step 1: Resend Setup
1. Register/log in to [Resend.com](https://resend.com).
2. Go to **API Keys** and click **Create API Key**. Copy the key (starts with `re_`).
3. If you have a custom domain, verify it under **Domains** to send emails from your own domain (e.g. `alerts@yourdomain.com`).
4. Otherwise, for testing, you can use `onboarding@resend.dev` as your sender, which will dispatch emails to the single address registered to your Resend account.

### Step 2: GitHub Repository Setup
1. Push this local repository to a **private** GitHub repository named `job-radar`.
2. Go to **Settings → Secrets and variables → Actions → New repository secret**.
3. Create the following secrets:
   - `DATABASE_URL` (your Supabase connection string)
   - `RESEND_API_KEY` (your token from Step 1)

### Step 3: GitHub Dispatch Token (Admin Run Button)
1. Go to your GitHub account → **Settings → Developer Settings → Personal access tokens → Fine-grained tokens**.
2. Click **Generate new token**. Set repository access to `job-radar` only.
3. Grant **Read & Write** permissions for **Actions**.
4. Copy the generated token and save it in your local `.env` and Render config (see Step 4) as `GITHUB_DISPATCH_TOKEN`.

### Step 4: Deploy on Render
1. Create a new **Web Service** on [Render.com](https://render.com).
2. Connect your `job-radar` GitHub repository.
3. Set the following parameters:
   - **Runtime**: `Python 3`
   - **Build Command**: `cd frontend && npm ci && npm run build && cd .. && pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free`
4. Add the following **Environment Variables** in the Render settings:
   - `DATABASE_URL` (Supabase connection string)
   - `SECRET_KEY` (Generate a new secure hash string)
   - `RESEND_API_KEY` (From Step 1)
   - `RESEND_FROM_EMAIL` (e.g., `onboarding@resend.dev` or custom domain email)
   - `GITHUB_DISPATCH_TOKEN` (From Step 3)
   - `GITHUB_REPO` (e.g., `yourusername/job-radar`)

### Step 5: Verify the Operation Flow
1. Visit your Render URL (the Landing page should load).
2. Register a new user account.
3. Complete the Guided Onboarding (Role, Keywords, and email alerts verification).
4. Click **Send Test Email** on onboarding step 3 or settings to verify integration.
5. In the Admin settings tab, click **Run Scraper Now** (or run the workflow manually on GitHub).
6. Verify that listings matching your keywords populate the dashboard, and you receive corresponding email alerts.
