# Implementation Checklist
## Job Radar — Build Guide
**Version:** 1.0
**Last Updated:** June 2026

---

> **How to use this checklist.**
> Items are grouped into tiers that mirror the three product stages in the PRD and TDD. Complete each tier fully before moving to the next — later tiers assume the earlier ones are working. Each item is written to be self-contained: you should be able to read it, know exactly what to do, and know how to verify it worked. Where the TDD has the full implementation detail, this checklist tells you what file to look at. Where a step is purely operational (accounts, secrets, config), the full steps are here.

---

## Tier 0 — Project Setup and External Accounts

These are prerequisites. Nothing else can start until this tier is done.

### Accounts and Services

- [ ] **Create a GitHub account** (if you don't have one) and create a new **private** repository named `job-radar`. Private is important — your `.env` and workflow secrets are attached to this repo.

- [ ] **Create a Supabase account** at supabase.com. Create a new project; choose the free tier; pick any region (Frankfurt or US East are reliable). Once the project is provisioned, go to **Project Settings → Database → Connection String → URI** and copy it. It will begin with `postgres://`. Store it somewhere safe — this is your `DATABASE_URL`.

- [ ] **(Removed)** Resend account and domains setup are no longer needed.

- [ ] **Create a Telegram bot** via BotFather. Open Telegram, search for `@BotFather`, and send `/newbot`. Follow the prompts: give the bot a display name and a username (the username must end in `bot`, e.g. `jobradar_yourname_bot`). BotFather will reply with a token that looks like `123456789:ABCdef...`. Store this as `TELEGRAM_BOT_TOKEN`. Also note the username — you'll need it in `telegram_service.py`.

- [ ] **Create a Render account** at render.com. Connect it to your GitHub account. You won't deploy yet — just connect the accounts so that when the time comes, Render can pull from your repo.

### Local Environment

- [ ] **Confirm Python 3.12** is installed: `python --version`. If not, install it via pyenv (`pyenv install 3.12.x && pyenv global 3.12.x`) or directly from python.org.

- [ ] **Confirm Node.js 20+** is installed: `node --version`. If not, install it via nvm (`nvm install 20 && nvm use 20`).

- [ ] **Clone the (empty) repository** locally:
  ```bash
  git clone https://github.com/yourusername/job-radar
  cd job-radar
  ```

- [ ] **Create the top-level directory structure** as defined in TDD Section 2. You can do this manually or with:
  ```bash
  mkdir -p backend/{models,schemas,routers,services} \
            frontend/src/{api,pages,components,contexts} \
            scraper/{boards,notifier} \
            migrations/versions \
            .github/workflows
  ```

- [ ] **Create a `.env` file** in the project root by copying `.env.example` (which you'll create below). Populate it with the values collected above:
  ```
  DATABASE_URL=postgres://...
  SECRET_KEY=    # generate with: python -c "import secrets; print(secrets.token_hex(32))"
  TELEGRAM_BOT_TOKEN=...
  GITHUB_DISPATCH_TOKEN=    # leave blank for now; filled in Tier 3
  GITHUB_REPO=yourusername/job-radar
  ```

- [ ] **Create a Python virtual environment** and install backend dependencies:
  ```bash
  python -m venv .venv
  source .venv/bin/activate      # Windows: .venv\Scripts\activate
  pip install -r requirements.txt
  ```
  The `requirements.txt` contents are in TDD Section 10.

- [ ] **Add `.env` and `.venv` to `.gitignore`**:
  ```
  .env
  .venv/
  __pycache__/
  *.pyc
  frontend/node_modules/
  frontend/dist/
  ```

---

## Tier 1 — Database

The database schema must exist before any application code can run against it.

### Alembic Setup

- [ ] **Create `alembic.ini`** in the project root. The key line to set is:
  ```ini
  sqlalchemy.url = %(DATABASE_URL)s
  ```
  Then in `migrations/env.py`, load the URL from the environment:
  ```python
  import os
  from dotenv import load_dotenv
  load_dotenv()
  config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
  ```
  This means Alembic always reads `DATABASE_URL` from your `.env`, so you never hardcode a connection string.

- [ ] **Write all four ORM model files** as specified in TDD Section 4.4:
  - `backend/models/user.py` — the `User` table
  - `backend/models/profile.py` — `UserProfile` and `NotificationSettings`
  - `backend/models/listing.py` — the `Listing` table
  - `backend/models/match.py` — `UserMatch` and `ScraperRun`

  All models must import from `backend.database.Base` and use `UUID(as_uuid=True)` as primary keys.

- [ ] **Configure `migrations/env.py`** to import all models before setting `target_metadata`. This is the step people most often forget — if a model isn't imported, Alembic doesn't see the table and won't generate a migration for it. See the import block in TDD Section 3.2.

- [ ] **Generate the initial migration**:
  ```bash
  alembic revision --autogenerate -m "initial schema"
  ```
  Open the generated file in `migrations/versions/` and verify it contains `CREATE TABLE` statements for all six tables: `users`, `user_profiles`, `notification_settings`, `listings`, `user_matches`, `scraper_runs`. If any are missing, you forgot to import that model in `env.py`.

- [ ] **Apply the migration to Supabase**:
  ```bash
  alembic upgrade head
  ```
  If this succeeds without errors, go to your Supabase project's **Table Editor** and confirm all six tables exist with the correct columns.

- [ ] **Verify indexes exist** by running this in the Supabase SQL editor:
  ```sql
  SELECT indexname FROM pg_indexes WHERE tablename IN
  ('listings', 'user_matches', 'scraper_runs');
  ```
  You should see `idx_listings_fingerprint`, `idx_listings_fetched_at`, `idx_matches_user_id`, `idx_matches_unnotified`, and `idx_scraper_runs_board`.

---

## Tier 2 — Backend (FastAPI)

Build the API layer. At the end of this tier you should be able to run the backend locally and hit all endpoints with curl or a browser.

### Foundation

- [ ] **Write `backend/config.py`** using `pydantic-settings` as shown in TDD Section 4.2. All environment variables are read here and nowhere else in the backend. Any file that needs a config value imports `from backend.config import settings`.

- [ ] **Write `backend/database.py`** as shown in TDD Section 4.3. Note the URL rewrite: Supabase gives you a `postgres://` URL but SQLAlchemy's async driver requires `postgresql+asyncpg://`. The `replace()` call handles this. The `get_db` async generator is the FastAPI dependency that all routers use.

- [ ] **Write `backend/main.py`** as shown in TDD Section 4.1. The `lifespan` context manager runs `init_db()` on startup — this is a connection check only, not a migration runner. Never run `alembic upgrade head` inside the app; always run it as a separate step.

- [ ] **Write `backend/dependencies.py`** containing `get_current_user` and `require_admin` as shown in TDD Section 4.6. These are FastAPI dependencies injected into route handlers. `get_current_user` reads the `session` cookie, decodes the signed token, and queries the database for the user. `require_admin` chains off `get_current_user` and raises 403 if `user.is_admin` is false.

### Authentication

- [ ] **Write `backend/services/auth_service.py`** as shown in TDD Section 4.6. The two key functions are `hash_password` (bcrypt via passlib) and `create_session_token` / `decode_session_token` (itsdangerous `URLSafeTimedSerializer`). The `salt="session"` argument is important — it namespaces the token so it can't be reused in other contexts.

- [ ] **Write all Pydantic schemas** in `backend/schemas/` as shown in TDD Section 4.5. These are the request and response shapes for every endpoint. Getting these right before writing routers saves a lot of back-and-forth.

- [ ] **Write `backend/routers/auth.py`** as shown in TDD Section 4.7. The four routes are `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, and `GET /api/auth/me`. Pay attention to the registration handler — it creates empty `UserProfile` and `NotificationSettings` rows in the same transaction as the user, using `db.flush()` to get the user ID before committing. This ensures those rows always exist for every user.

- [ ] **Test authentication manually** by running the backend locally:
  ```bash
  uvicorn backend.main:app --reload
  ```
  Then in a separate terminal:
  ```bash
  # Register
  curl -c cookies.txt -X POST http://localhost:8000/api/auth/register \
    -H "Content-Type: application/json" \
    -d '{"full_name":"Test User","email":"test@example.com","password":"password123"}'

  # Check session
  curl -b cookies.txt http://localhost:8000/api/auth/me
  ```
  The `/me` endpoint should return the user object. The `-c` and `-b` flags save and send the session cookie.

### Profile and Dashboard Routes

- [ ] **Write `backend/routers/profile.py`** with `GET /api/profile` and `PUT /api/profile`, and `GET /api/notifications` and `PUT /api/notifications`. All four routes require `get_current_user`. The PUT handlers use SQLAlchemy's `update()` with `synchronize_session=False` and only update fields that are not `None` in the request body — this is what makes the `Optional` fields in `ProfileUpdate` meaningful.

- [ ] **Write `backend/routers/dashboard.py`** with `GET /api/matches` and `PATCH /api/alerts/pause`. The matches query joins `user_matches` → `listings`, filters by `user_id`, orders by `created_at DESC`, and limits to 20. The pause route updates `user_profiles.alerts_paused`.

### Telegram

- [ ] **Write `backend/services/telegram_service.py`** as shown in TDD Section 4.9. The `BOT_USERNAME` value must match the username you got from BotFather exactly (without the `@`). The `generate_connect_token()` function returns a 32-byte URL-safe random string and a 15-minute expiry datetime.

- [ ] **Write `backend/routers/telegram.py`** as shown in TDD Section 4.8. Three routes: `GET /api/telegram/connect` (generates token, stores it, returns deep link), `GET /api/telegram/status` (polled by the frontend), and `POST /api/telegram/webhook` (called by Telegram's servers — must not require authentication). The webhook handler validates the token against the database, then sets `telegram_chat_id` and `telegram_connected = True`.

- [ ] **Test the Telegram webhook locally** using a tunnelling tool like [ngrok](https://ngrok.com) or [localtunnel](https://theboroer.github.io/localtunnel-www/):
  ```bash
  ngrok http 8000
  ```
  Register the temporary tunnel URL as the webhook:
  ```bash
  curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
    -d "url=https://<ngrok-id>.ngrok.io/api/telegram/webhook"
  ```
  Then send `/start test` to your bot on Telegram and confirm the webhook receives the message. Remember to delete the webhook after testing:
  ```bash
  curl "https://api.telegram.org/bot<TOKEN>/deleteWebhook"
  ```

### Admin

- [ ] **Write `backend/services/dispatch_service.py`** as shown in TDD Section 4.10. This calls the GitHub REST API to dispatch the `scraper.yml` workflow. It requires `GITHUB_DISPATCH_TOKEN` (a fine-grained PAT) which you'll create in Tier 3 when the workflow file exists.

- [ ] **Write `backend/routers/admin.py`** with at minimum `GET /api/admin/users` (all registered users), `GET /api/admin/scraper-runs` (most recent run per board), and `POST /api/admin/trigger-scrape` (calls `dispatch_service`). All routes use `require_admin`.

---

## Tier 3 — Frontend (React)

The frontend is a React SPA served by FastAPI in production. In development it runs on Vite's dev server with a proxy to the local FastAPI instance.

### Vite Project Setup

- [ ] **Initialise the Vite project** inside the `frontend/` directory:
  ```bash
  cd frontend
  npm create vite@latest . -- --template react-ts
  npm install
  npm install react-router-dom react-query
  ```

- [ ] **Configure the dev proxy** in `vite.config.ts` as shown in TDD Section 5.2. This lets `fetch("/api/...")` in the browser resolve to `http://localhost:8000` during development without CORS errors.

- [ ] **Install CSS modules support** — it's built into Vite. Name your stylesheets `ComponentName.module.css` and import them as `import styles from './ComponentName.module.css'`.

### Auth Context and Router

- [ ] **Write `src/contexts/AuthContext.tsx`** as shown in TDD Section 5.3. The context stores the current user object and exposes `setUser`. The `useEffect` on mount calls `GET /api/auth/me` to restore session state on page refresh — without this, every refresh would log the user out.

- [ ] **Write `src/App.tsx`** with the full router as shown in TDD Section 5.4. The `ProtectedRoute` component checks both authentication and `onboarding_complete` — unauthenticated users go to `/login`, authenticated users who haven't finished onboarding go to `/onboarding`, authenticated and complete users pass through. The `AdminRoute` component additionally checks `is_admin`.

### API Layer

- [ ] **Write all API wrapper files** in `src/api/` as shown in TDD Section 5.5. Every backend call goes through these typed functions — no raw `fetch()` calls in components. Each function throws the parsed error body on non-OK responses so components can display error messages without parsing them.

### Pages

- [ ] **Write `src/pages/Register.tsx`** — a form with three fields (full name, email, password) that calls `registerUser()`, then calls `setUser()` with the response and navigates to `/onboarding`.

- [ ] **Write `src/pages/Login.tsx`** — a form with email and password that calls `loginUser()`, then navigates to `/dashboard` if `onboarding_complete` is true, or `/onboarding` if not.

- [ ] **Write `src/pages/Onboarding.tsx`** as a multi-step form as shown in TDD Section 5.6. Three steps: role, keywords, notifications. State for all three steps lives in the parent `Onboarding` component. Only the final "Finish" button submits to the backend — do not submit on every "Next" click, as the user should be able to go back and change things freely. On finish, make three sequential API calls: `PUT /api/profile`, `PUT /api/notifications`, then `PUT /api/profile` with `{ onboarding_complete: true }`.

- [ ] **Write `src/components/KeywordInput.tsx`** — a tag-style input that lets users type a keyword, press Enter or comma to add it, and click an `×` to remove it. Store tags as a `string[]` in local state and call an `onChange` prop when the array changes. This component is used for both inclusion and exclusion keywords.

- [ ] **Write `src/components/TelegramConnect.tsx`** as shown in TDD Section 5.7. The component has four states: `idle` (show a "Connect Telegram" button), `waiting` (show the deep link and instructions, start polling), `connected` (show a success message), and `timeout` (show a retry prompt). The polling interval must be cleared in a `useEffect` cleanup function to avoid memory leaks.

- [ ] **Write `src/pages/Dashboard.tsx`** — fetches matches via `getMatches()` on mount, renders them as a list of `MatchCard` components, and includes the alert pause toggle.

- [ ] **Write `src/components/MatchCard.tsx`** — displays a single match: job title (linking to the original listing), company, board source badge, location, salary if present, and the date it was found. Keep it compact.

- [ ] **Write `src/pages/Settings.tsx`** — the same fields as the onboarding steps but in a single scrollable page, with current values pre-filled from `GET /api/profile` and `GET /api/notifications`. Each section saves independently (separate buttons per section, not one global save).

- [ ] **Write `src/pages/Admin.tsx`** — visible only to admin users. Shows the scraper run log per board (status, last run time, listings found), user list with alert status, and the "Run scraper now" button. Render this page at `/admin`; do not link it in the main navigation.

### Build Verification

- [ ] **Run the dev server** and manually walk through the full user journey: register → onboarding (including Telegram connect via ngrok) → dashboard (empty state) → settings → logout → login → dashboard.

- [ ] **Verify the production build** compiles without errors:
  ```bash
  cd frontend && npm run build
  ```
  Then start FastAPI and confirm it serves the built app:
  ```bash
  uvicorn backend.main:app
  # Visit http://localhost:8000 — should load the React app
  # Visit http://localhost:8000/api/auth/me — should return JSON
  ```

---

## Tier 4 — Scraper

The scraper is a standalone Python process, entirely separate from the FastAPI app. It has its own database connection (sync psycopg3, not async SQLAlchemy), its own config, and its own entry points.

### Foundation

- [ ] **Install scraper dependencies** in the same virtual environment:
  ```bash
  pip install -r requirements-scraper.txt
  ```
  The contents are in TDD Section 10.

- [ ] **Write `scraper/config.py`** — identical structure to `backend/config.py` but only the subset of variables the scraper needs: `DATABASE_URL`, `TELEGRAM_BOT_TOKEN`, `RESEND_API_KEY`.

- [ ] **Write `scraper/database.py`** — a sync psycopg3 connection factory. The scraper does not need async SQLAlchemy; direct psycopg3 is simpler and sufficient:
  ```python
  import psycopg
  from scraper.config import settings

  def get_connection():
      return psycopg.connect(settings.database_url)
  ```
  Note: psycopg3 (`psycopg`) uses `psycopg.connect()`, not `psycopg2.connect()`. The `DATABASE_URL` from Supabase works directly with psycopg3 without the `postgresql+asyncpg://` rewrite.

### Base Classes

- [ ] **Write `scraper/boards/base.py`** as shown in TDD Section 6.2. The `Listing` dataclass is the normalised shape every board scraper must produce — this is the contract between scrapers and the deduplicator. The `BaseScraper` ABC enforces that every scraper implements `fetch()`. The `_start_run()` and `_end_run()` helper methods write to `scraper_runs` — call them in every scraper so the admin view always has a run log regardless of outcome.

### Board Scrapers

- [ ] **Write `scraper/boards/remoteok.py`** as shown in TDD Section 6.3. Important details: the `User-Agent` header is required (the API returns 403 without it). The first element of the JSON response is a metadata object, not a job — filter it out by checking for the `slug` key. Salary data is in `salary_min` and `salary_max` as integers; format them into a human-readable string.

- [ ] **Test RemoteOK manually** before wiring it into the full pipeline:
  ```bash
  python -c "
  import asyncio
  from scraper.boards.remoteok import RemoteOKScraper
  from scraper.database import get_connection
  db = get_connection()
  results = asyncio.run(RemoteOKScraper().fetch(db))
  print(f'Fetched {len(results)} listings')
  print(results[0])
  db.close()
  "
  ```
  You should see a count and a `Listing` object. If you get 0 results or an error, fix it before continuing.

- [ ] **Write `scraper/boards/himalayas.py`** as shown in TDD Section 6.4. Add `?limit=100` to the URL to get a meaningful page of results rather than the default smaller set.

- [ ] **Test Himalayas manually** using the same pattern as above.

- [ ] **Write `scraper/boards/ycombinator.py`** as shown in TDD Section 6.5. This is the only board that uses HTML parsing rather than an API. The CSS selectors in the TDD are approximate — **you must open `https://www.ycombinator.com/jobs` in a browser, inspect the DOM, and confirm the correct selectors before running this scraper**. If the page has changed structure, update the selectors in this file only. Use `follow_redirects=True` in the httpx client — YC Jobs redirects HTTP to HTTPS.

- [ ] **Test YC Jobs manually** and confirm the selectors return real listings.

### Deduplicator and Matcher

- [ ] **Write `scraper/deduplicator.py`** as shown in TDD Section 6.6. The fingerprint is a SHA-256 hash of `board|company_lower|title_lower`. The `ON CONFLICT (fingerprint) DO NOTHING` on the INSERT means this function is idempotent — running it twice with the same listings produces no duplicates. The return value is only the newly inserted listings; this is what gets passed to the matcher.

- [ ] **Write `scraper/matcher.py`** as shown in TDD Section 6.7. Two functions: `listing_matches_profile()` (pure logic, no DB, easy to unit test) and `match_all_users()` (queries all active users, runs the match logic, writes to `user_matches`). The `ON CONFLICT (user_id, listing_id) DO NOTHING` prevents duplicate match rows if the scraper runs more than once before a digest is sent.

- [ ] **Unit test `listing_matches_profile()`** directly — it takes two dicts and returns a bool, so it needs no database:
  ```python
  from scraper.matcher import listing_matches_profile

  assert listing_matches_profile(
      {"title": "Python Backend Engineer", "description": "Django, REST API"},
      {"inclusion_keywords": ["python"], "exclusion_keywords": ["on-site"], "alerts_paused": False}
  ) == True

  assert listing_matches_profile(
      {"title": "Python Backend Engineer", "description": "on-site role"},
      {"inclusion_keywords": ["python"], "exclusion_keywords": ["on-site"], "alerts_paused": False}
  ) == False
  ```

### Notifier

- [ ] **Write `scraper/notifier/telegram.py`** as shown in TDD Section 6.8. The `format_listing_telegram()` function uses HTML parse mode — valid tags are `<b>`, `<i>`, `<a href="...">`. Do not use Markdown parse mode; it requires escaping many characters that commonly appear in job titles.

- [ ] **(Removed)** Email notifier file is no longer required.

- [ ] **Write `scraper/notifier/__init__.py`** as shown in TDD Section 6.8. The `dispatch_immediate_notifications()` function runs all notification sends concurrently via `asyncio.gather(..., return_exceptions=True)`, then marks all notified matches in a single batch update.

- [ ] **Test a Telegram notification manually** to a real chat before wiring it into the pipeline:
  ```bash
  python -c "
  import asyncio
  from scraper.notifier.telegram import send_telegram_message
  asyncio.run(send_telegram_message('YOUR_CHAT_ID', 'Test message from Job Radar'))
  "
  ```
  Your Telegram chat ID can be found by messaging `@userinfobot` on Telegram.

### Entry Point and Digest

- [ ] **Write `scraper/main.py`** as shown in TDD Section 6.1. The `SCRAPERS` list controls which boards are active. `asyncio.gather(..., return_exceptions=True)` means a single board failure logs an error and is skipped, but the other boards continue. Only new listings (returned by the deduplicator) are passed to the matcher — re-running the scraper will not re-notify users about listings they've already seen.

- [ ] **Write `scraper/digest.py`** as shown in TDD Section 7. This is the entry point for the daily digest workflow. It queries `user_matches WHERE notified_at IS NULL` for users with `frequency = 'digest'`, groups by user, and sends one batched message per user per channel.

- [ ] **Run a full local end-to-end test**:
  1. Ensure you have a registered, onboarding-complete user in the database with at least one inclusion keyword that will match a real job (e.g. "python" or "remote").
  2. Run the scraper: `python -m scraper.main`
  3. Check the `listings` table in Supabase — it should have new rows.
  4. Check the `user_matches` table — it should have rows for your user.
  5. Check `scraper_runs` — each board should have a row with `status = 'success'`.
  6. If your user is on `immediate` frequency, check your Telegram for a notification.

---

## Tier 5 — GitHub Actions and Deployment

The final tier wires everything together in production.

### GitHub Actions

- [ ] **Write `.github/workflows/scraper.yml`** as shown in TDD Section 8.1. The cron expression `0 */6 * * *` runs at 00:00, 06:00, 12:00, and 18:00 UTC. The `workflow_dispatch` trigger allows manual runs from the GitHub Actions tab and from the admin UI via the dispatch API.

- [ ] **Write `.github/workflows/digest.yml`** as shown in TDD Section 8.2. The cron `0 7 * * *` runs at 07:00 UTC daily, which is 08:00 WAT.

- [ ] **Add repository secrets** in GitHub: go to your repo → **Settings → Secrets and variables → Actions → New repository secret**. Add:
  - `DATABASE_URL`
  - `TELEGRAM_BOT_TOKEN`

- [ ] **Trigger a manual scraper run** from the GitHub Actions tab to verify it works in the Actions environment. Go to **Actions → Job Radar — Scraper → Run workflow**. Watch the logs. Confirm new listings appear in Supabase.

- [ ] **Create the GitHub fine-grained PAT** for the admin dispatch button. Go to GitHub → **Settings → Developer Settings → Personal access tokens → Fine-grained tokens → Generate new token**. Set the resource owner to your account, repository access to `job-radar` only, and permissions to **Actions: Read and write**. Copy the token and store it as `GITHUB_DISPATCH_TOKEN` in both your local `.env` and as a Render environment variable (next step).

### Render Deployment

- [ ] **Create a new Web Service** on Render. Connect your GitHub repository. Set:
  - **Runtime:** Python 3
  - **Build command:** `cd frontend && npm ci && npm run build && cd .. && pip install -r requirements.txt`
  - **Start command:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
  - **Instance type:** Free

- [ ] **Add environment variables** in the Render dashboard under **Environment**:
  - `DATABASE_URL`
  - `SECRET_KEY`
  - `TELEGRAM_BOT_TOKEN`
  - `GITHUB_DISPATCH_TOKEN`
  - `GITHUB_REPO` (e.g. `yourusername/job-radar`)

- [ ] **Deploy and confirm the build succeeds.** The first deploy will take several minutes — it installs Node deps, builds the React app, then installs Python deps. Check the deploy log for errors. A successful deploy ends with `Uvicorn running on http://0.0.0.0:10000`.

- [ ] **Register the Telegram webhook** pointing to the Render URL:
  ```bash
  curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
    -H "Content-Type: application/json" \
    -d '{"url": "https://<your-app>.onrender.com/api/telegram/webhook"}'
  ```
  Verify it registered:
  ```bash
  curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
  ```
  The response should show your Render URL as `url` and `pending_update_count: 0`.

- [ ] **Promote yourself to admin** via Supabase SQL Editor:
  ```sql
  UPDATE users SET is_admin = TRUE WHERE email = 'your@email.com';
  ```
  If you haven't registered yet, do so through the live app first, then run this query.

### Final Verification

- [ ] **Walk the full production flow** as a non-admin user on a real browser (not localhost). Register → onboard → connect Telegram → wait for (or manually trigger) a scraper run → confirm a notification arrives → check the dashboard shows the match.

- [ ] **Test the admin panel**: log in as the admin user, navigate to `/admin`, confirm user list is visible, confirm scraper run log is visible, click "Run scraper now" and confirm a new run appears in the log within a minute.

- [ ] **Test the Render cold-start** by waiting 20 minutes without visiting the app, then loading it. Confirm the loading state displays gracefully rather than showing a blank screen or error during the 20–40 second wake-up.

- [ ] **Invite your first non-technical user**. Send them the Render URL and walk them through registration once. Note any points of confusion — these are UX fixes for Stage 2.

---

## Tier 6 — Stage 2 Additions

Complete all of Tier 5 and confirm the system is stable before starting Stage 2. These items build on a working Stage 1.

- [ ] **Add `enabled_boards TEXT[]` column** to `user_profiles` via a new Alembic migration:
  ```bash
  alembic revision --autogenerate -m "add enabled_boards to user_profiles"
  alembic upgrade head
  ```
  The default value should be `'{remoteok,himalayas,ycombinator}'` — all boards enabled by default so existing users are unaffected.

- [ ] **Update the matcher** to filter by `user.enabled_boards` before running keyword matching. Add the board filter as the first check in `listing_matches_profile()` — if the listing's board is not in the user's enabled list, return False immediately.

- [ ] **Add board toggles to `src/pages/Settings.tsx`** — three checkboxes (one per board), saving to `PUT /api/profile` with the updated `enabled_boards` array.

- [ ] **Add `BoardStatus` component** to the dashboard showing last successful run timestamp and status per board, sourced from `GET /api/admin/scraper-runs` (or a new non-admin equivalent endpoint `GET /api/scraper-status` that returns a read-only summary).

- [ ] **Implement salary filtering in the matcher.** Write a `parse_salary(salary_text: str) -> int | None` utility that extracts a midpoint from strings like `"$80,000 – $100,000"` (returns 90000) or returns `None` for unparseable strings. In `listing_matches_profile()`, after keyword matching, check: if `user.salary_min` is set and `parse_salary(listing["salary_text"])` returns a value, skip the listing if it falls outside the range. Listings with no parseable salary are never excluded by this filter.

---

## Tier 7 — Stage 3 Additions

Stage 3 only after Stage 2 is stable.

- [ ] **Add Playwright** to `requirements-scraper.txt`:
  ```
  playwright>=1.44.0
  ```
  Add the install step to `.github/workflows/scraper.yml`:
  ```yaml
  - name: Install Playwright
    run: playwright install chromium && playwright install-deps chromium
  ```

- [ ] **Write `scraper/boards/wellfound.py`** using `async_playwright`. Initialise the browser once per run outside the scraper class (pass the `page` in, or use a shared browser context). Treat this scraper as non-critical: any exception must be caught, logged, and returned as an empty list — it must not abort the run.

- [ ] **Add LLM scoring (opt-in).** Add `minimum_match_score FLOAT` to `user_profiles` via migration. In `matcher.py`, after a keyword match is confirmed, if the user has `minimum_match_score` set and `user.skills_summary` is populated, call the Claude API with a structured prompt (see PRD Section 3.12) and store the returned score in `user_matches.match_score`. Only add the match to the immediate notification list if the score meets the threshold. This step adds latency — run it concurrently per match using `asyncio.gather`.

- [ ] **Evaluate LinkedIn.** Review current legal precedents and Wellfound/LinkedIn enforcement posture before writing any code. If proceeding, implement with a minimum 5-second delay between page requests, user-agent rotation, a consecutive-failure cap of 3 (after which the scraper marks itself disabled in the DB and sends an admin alert), and a note in the admin UI that this scraper carries legal risk.
