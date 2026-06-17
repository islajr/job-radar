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
- Created `/api/telegram/connect` deep link generator, `/api/telegram/status` poll check, and `/api/telegram/webhook` message hook handler.

### 3. Frontend React App (Tier 3)
- Built Vite-TS dark-mode glassmorphic interface (Auth, Guided Onboarding, Keywords Tag Input, Telegram Connect module, and Settings panel).
- Resolved all type-safety compiler and CSS selector errors.
- Added a real-time Telegram Bot Connection status badge (`Connected` / `Not Connected`) directly on the **[Settings page](file:///home/isla-jr/Documents/se-workspace/job-radar/frontend/src/pages/Settings.tsx)**.
- Verified that production build bundles compile cleanly into `frontend/dist/`.

### 4. Scraper Engine (Tier 4)
- **[ycombinator.py](file:///home/isla-jr/Documents/se-workspace/job-radar/scraper/boards/ycombinator.py)**: Scrapes listings by parsing YC's embedded `data-page` JSON object, ensuring extreme stability against DOM shifts.
- **[remoteok.py](file:///home/isla-jr/Documents/se-workspace/job-radar/scraper/boards/remoteok.py)**: Updated endpoint to `/api` and enabled redirects to fetch correctly.
- **[deduplicator.py](file:///home/isla-jr/Documents/se-workspace/job-radar/scraper/deduplicator.py)**: Deterministically filters duplicates using SHA-256 hashes of `board|company|title`.
- **[matcher.py](file:///home/isla-jr/Documents/se-workspace/job-radar/scraper/matcher.py)**: Cross-references new listings with active users based on their keyword profiles.
- **Robust UUIDs**: Modified database insertions to generate UUID keys in Python, preventing `NotNullViolation` errors since database primary keys do not have default server-side generators.
- **Async notifier dispatcher**: Updated immediate Telegram notifier functions to run natively asynchronous inside the main event loop to avoid `RuntimeError` loops.
- **[digest.py](file:///home/isla-jr/Documents/se-workspace/job-radar/scraper/digest.py)**: Aggregates daily summaries for digest-configured users and dispatches single compiled Telegram updates.

### 5. Workflows & Configuration (Tier 5)
- Created **[scraper.yml](file:///home/isla-jr/Documents/se-workspace/job-radar/.github/workflows/scraper.yml)** (runs every 6 hours/manually) and **[digest.yml](file:///home/isla-jr/Documents/se-workspace/job-radar/.github/workflows/digest.yml)** (runs daily at 07:00 UTC).
- Updated **[README.md](file:///home/isla-jr/Documents/se-workspace/job-radar/README.md)** with clear setup, tech stack, and scraper execution details.

---

## 🚀 Next Steps: Operational Checklist

Follow these steps to deploy the application, configure Telegram bot routing, and set up automated scraper cron schedules.

### Step 1: Telegram Bot Setup
1. Open Telegram and search for `@BotFather`.
2. Send `/newbot` and follow the prompts to create your bot.
3. Save the returned `TELEGRAM_BOT_TOKEN` (looks like `123456789:ABCdef...`).
4. Update your local `.env` and Render dashboard (see Step 4) with this token.

### Step 2: GitHub Repository Setup
1. Push this local repository to a **private** GitHub repository named `job-radar`.
2. Go to **Settings → Secrets and variables → Actions → New repository secret**.
3. Create the following secrets:
   - `DATABASE_URL` (your Supabase connection string)
   - `TELEGRAM_BOT_TOKEN` (your token from `@BotFather`)

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
   - `TELEGRAM_BOT_TOKEN` (From Step 1)
   - `GITHUB_DISPATCH_TOKEN` (From Step 3)
   - `GITHUB_REPO` (e.g., `yourusername/job-radar`)

### Step 5: Telegram Bot Webhook Registration
Once your Render service is live, register its API endpoint as your Telegram Bot webhook. Run this curl command (replace `<TOKEN>` and `<your-render-domain>`):

```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d "url=https://<your-render-domain>.onrender.com/api/telegram/webhook"
```

### Step 6: Verify the Operation Flow
1. Visit your Render URL (the Landing page should load).
2. Register a new user account.
3. Complete the Guided Onboarding (Role, Keywords, and Telegram Bot link connection).
4. Go to the dashboard.
5. In the Admin settings tab, click **Run Scraper Now** (or run the workflow manually on GitHub).
6. Verify that listings populate the dashboard matching your keywords, and your Telegram client receives immediate messages.
