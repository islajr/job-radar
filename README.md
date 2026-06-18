# 🔎 Job Radar

Job Radar is a scheduled remote job aggregator, keyword filter, and instant notification service designed for personalized job search. It fetches listings from popular remote job boards, filters them against custom user keyword profiles, and delivers matching jobs **exclusively via Telegram** (either immediately or in a daily digest).

---

## 🏗️ Architecture

Job Radar is split into three main components:

1. **FastAPI Backend (`backend/`)**: Serves the REST API for user authentication, profile settings, matches dashboard, and Telegram bot webhook handlers.
2. **React SPA (`frontend/`)**: A glassmorphic dark-mode web dashboard built with React, TypeScript, and Vite. It is compiled and served statically by the FastAPI server in production.
3. **Scraper & Matcher Engine (`scraper/`)**: A standalone Python pipeline running:
   - **Fetchers**: Concurrently gathers listings from **RemoteOK**, **Himalayas**, and **Y Combinator Jobs**.
   - **Deduplicator**: Deterministically fingerprints listings using SHA-256 hashes to prevent processing duplicates.
   - **Matcher**: Evaluates new listings against active users' profile inclusion/exclusion keywords.
   - **Notifier**: Dispatches immediate alerts or daily digests via the Telegram Bot API.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.12+, FastAPI, SQLAlchemy 2.0 (Async), Asyncpg, Passlib, Itsdangerous
- **Frontend**: React 19, Vite, TypeScript, Vanilla CSS modules, React Router 7, TanStack React Query
- **Database**: PostgreSQL (sync for scraper/migrations, async for backend API)
- **Deployment & Actions**: GitHub Actions (cron schedules), Render (hosting)

---

## 🚀 Local Setup

### 1. Prerequisites
- **Python 3.12+**
- **Node.js 20+**
- **PostgreSQL** running locally or a Supabase instance.
- A **Resend** account and API Key.

### 2. Clone and Install Dependencies

```bash
# Clone the repository
git clone https://github.com/yourusername/job-radar.git
cd job-radar

# Create virtual environment and install Python packages
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-scraper.txt

# Install Frontend modules
cd frontend
npm install
cd ..
```

### 3. Environment Configuration
Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql://localhost/job_radar   # Or your Supabase connection string
SECRET_KEY=your-session-serializer-secret-key    # Generate with: python -c "import secrets; print(secrets.token_hex(32))"
RESEND_API_KEY=re_...                            # Your Resend API key
RESEND_FROM_EMAIL=onboarding@resend.dev          # Sender email address
GITHUB_DISPATCH_TOKEN=your-fine-grained-github-pat
GITHUB_REPO=yourusername/job-radar
SIGNUP_WHITELIST=user1@example.com,user2@example.com  # Optional: Comma-separated allowed email addresses for registration. If empty, registration is open to all.
```

### 4. Database Migrations
Initialize the tables on your PostgreSQL database using Alembic:

```bash
alembic upgrade head
```

### 5. Running the Application

#### Development (Run Backend + Frontend Proxy)

1. Start the FastAPI backend:
   ```bash
   uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. Start the Vite React development server:
   ```bash
   cd frontend
   npm run dev
   ```
   Open `http://localhost:5173` in your browser. The Vite proxy config routes `/api` calls directly to port 8000.

#### Production (Serve Built React App Statically)

1. Build the frontend assets:
   ```bash
   cd frontend
   npm run build
   cd ..
   ```

2. Run FastAPI:
   ```bash
   uvicorn backend.main:app --host 0.0.0.0 --port 8000
   ```
   Open `http://localhost:8000` to interact with the production deployment.

---

## 🤖 Scraper Operations

The scraper can be executed manually or as a scheduled process.

* **Run Aggregation & Immediate Alerts**:
  ```bash
  python -m scraper.main
  ```
  This fetches jobs, deduplicates them, matches keywords, and dispatches immediate Resend email alerts.

* **Run Daily Digest Dispatcher**:
  ```bash
  python -m scraper.digest
  ```
  This gathers all accumulated matches for users configured with a `digest` alert frequency and dispatches a single compiled HTML email.

---

## 🔒 Security Features

1. **Signup Whitelist (`SIGNUP_WHITELIST`)**:
   - Limit user registration strictly to a comma-separated list of approved emails.
   - If `SIGNUP_WHITELIST` is unset or empty, registration is open to anyone.

2. **Aggressive Anonymous Rate Limiting**:
   - All anonymous (non-signed-in) visitors are limited to **15 requests per minute** on API endpoints (`/api/*`).
   - Limits are tracked in-memory using a sliding-window algorithm based on the client IP address (retrieved via `X-Forwarded-For` with a fallback to `request.client.host`).
   - Signed-in sessions (requests with a valid `session` cookie) bypass this rate-limiting entirely.

---

Verify keyword matching logic and security features by running the test suite:

```bash
# Run all tests via pytest
PYTHONPATH=. .venv/bin/pytest
```

---

## ⚡ GitHub Actions Workflows
Two actions are configured in `.github/workflows/`:
1. **`scraper.yml`**: Runs `scraper.main` every 6 hours (`0 */6 * * *`) and is manually dispatchable.
2. **`digest.yml`**: Runs `scraper.digest` daily at 07:00 UTC (`0 7 * * *`).
