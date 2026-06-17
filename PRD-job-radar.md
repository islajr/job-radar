# Product Requirements Document
## Job Radar — Personalised Remote Job Alert Service
**Version:** 2.0
**Status:** Draft
**Last Updated:** June 2026

---

## 1. Overview

### 1.1 Product Summary

Job Radar is a lightweight web application that monitors a curated set of remote job boards on a recurring schedule, matches new listings against each registered user's profile and preferences, and delivers relevant opportunities via Telegram — without the user needing to visit any job board manually.

### 1.2 Problem Statement

Remote job seekers spend disproportionate time manually refreshing multiple job boards with varying posting cadences and formats. This is especially burdensome for people in fields like social media management and content strategy, where relevant listings are spread across general remote boards, startup-focused platforms, and niche directories. There is no single surface that aggregates, filters, and proactively delivers relevant opportunities to a person's inbox or phone.

### 1.3 Goals

- Eliminate manual job board monitoring for registered users.
- Surface relevant listings before the user has to go looking.
- Require zero technical knowledge to use after initial setup.
- Operate at zero infrastructure cost for a user base of up to five people.
- Deliver features in stages — shipping something useful early, adding complexity only where a real gap is observed.

### 1.4 Non-Goals (All Stages)

- This is not a job application tool. It finds and surfaces listings; applying is the user's responsibility.
- This is not a recruiter-facing product.
- This is not a high-scale platform. Architecture is explicitly optimised for ≤5 users.
- ATS integration, resume parsing, and application tracking are out of scope.
- LinkedIn and Wellfound scraping are deferred until a later stage due to legal and maintenance complexity.

---

## 2. Users

### 2.1 Target Users

Job Radar is designed for a small, known group of people with varying technical backgrounds.

**User Type A — Technical (1 person)**
The primary user and de facto administrator of the instance. Backend engineering candidate. Comfortable with terminals and developer tooling but wants to stop manually checking boards every day.

**User Type B — Non-technical (up to 4 people)**
Social media managers, content strategists, copywriters, and similar roles. Expect a browser-based experience no more complex than signing up for any web service. Will not touch a terminal, config file, or environment variable.

### 2.2 User Needs by Stage

| Need | Stage 1 | Stage 2 | Stage 3 |
|---|---|---|---|
| Register via a web form | ✅ | ✅ | ✅ |
| Set role, keywords, exclusions | ✅ | ✅ | ✅ |
| Receive Telegram alerts | ✅ | ✅ | ✅ |
| Receive email alerts | ❌ | ❌ | ❌ |
| Choose immediate or daily digest | ✅ | ✅ | ✅ |
| View match history in a dashboard | ✅ | ✅ | ✅ |
| Pause and resume alerts | ✅ | ✅ | ✅ |
| Edit preferences at any time | ✅ | ✅ | ✅ |
| Choose which boards to monitor | — | ✅ | ✅ |
| See scraper health per board | — | ✅ | ✅ |
| LLM-assisted match scoring | — | — | ✅ |
| Wellfound scraping | — | — | ✅ |
| LinkedIn scraping | — | — | Evaluate |

---

## 3. Staged Feature Plan

The product is built in three stages. Each stage produces a fully working, usable system. Later stages extend it based on observed gaps rather than assumed needs.

---

### Stage 1 — Working Core

**Goal:** A functional end-to-end system. Users can register, set preferences, and receive matched job alerts. The scraper runs automatically. All boards covered are low-maintenance (public APIs or stable HTML).

#### 3.1 Authentication

Users register with name, email, and password. Sessions are managed with signed cookies. Password reset is handled manually by the administrator. No OAuth in Stage 1.

Validation rules:
- Email must be unique.
- Password minimum 8 characters.
- All fields required at registration.

#### 3.2 Onboarding Flow

After registration, new users are stepped through a short guided flow before reaching the dashboard. This flow is not skippable — users must complete a minimum profile to receive alerts.

**Step 1 — Role**
- Job title / role type (text input with suggestions: "Backend Engineer", "Social Media Manager", "Content Strategist", "Copywriter", "Data Analyst", etc.)
- Years of experience (dropdown: 0–1, 1–3, 3–5, 5–10, 10+)

**Step 2 — Keywords**
- Inclusion keywords (tag input; comma-separated; e.g. "python, remote, API")
- Exclusion keywords (tag input; e.g. "on-site, unpaid, senior")
- Brief free-text description of what they're looking for (used for display and later for LLM matching in Stage 3)

**Step 3 — Notifications**
- Channel selection: Telegram only (default)
- Frequency: immediate (per scraper run) or daily digest (08:00 WAT / 07:00 UTC)
- If Telegram selected: guided Telegram connect flow (see Section 5.3)

#### 3.3 Job Boards (Stage 1)

| Board | Method | Rationale |
|---|---|---|
| RemoteOK | Public JSON API | Zero scraping; just an HTTP GET |
| Himalayas | Public JSON API | Zero scraping; well-documented |
| YC Jobs | Static HTML scraping | Stable structure; low maintenance |

Wellfound and LinkedIn are explicitly excluded from Stage 1.

#### 3.4 Scraper Behaviour

- All board fetches run concurrently (async).
- A listing is considered new if its fingerprint does not already exist in the database. Fingerprint is a SHA-256 hash of `board + company (lowercased) + title (lowercased)`.
- Stale listing detection is not implemented in Stage 1. Users may occasionally receive alerts for roles that are already filled — this is documented as a known limitation.
- The default schedule is every 6 hours. Users who prefer to receive alerts only once per day can select daily digest, which batches all unnotified matches and delivers them at 08:00 WAT regardless of when the scraper ran.
- Each run logs: board name, listings fetched, new listings stored, errors, start and end timestamps, and status.

#### 3.5 Matching

Keyword-based matching against the concatenated title and description of each listing.

A listing matches a user's profile if:
1. At least one inclusion keyword appears in the listing text (if any inclusion keywords are set), AND
2. None of the exclusion keywords appear in the listing text.

Matching is case-insensitive. Partial word matches count (e.g. "python" matches "Python developer"). This is intentional — better to over-notify and let the user tighten keywords than to miss relevant listings.

#### 3.6 Notifications

**Telegram**
Each alert message contains: job title (bold), company name, location or "Remote", salary if available, source board, and a direct link to the listing. Messages are sent one per match for immediate frequency, or batched into a single message with a numbered list for daily digest.

**Email**
Email alerts are not implemented. The notification system uses Telegram exclusively.

#### 3.7 Dashboard

After login, users land on a dashboard showing:
- The 20 most recent matched listings (title, company, board, date found, link to original)
- Current alert status (active / paused) with a toggle
- A link to edit preferences
- A summary: total matches found this week

#### 3.8 Admin View

A route accessible only to users with `is_admin = TRUE`, not linked anywhere in the main UI. Shows:
- All registered users, their alert status, and last notification sent
- Most recent scraper run per board: timestamp, listings found, new listings, status, error message if any
- A "Run scraper now" button that triggers the GitHub Actions workflow via the repository dispatch API (requires a `GITHUB_DISPATCH_TOKEN` with `workflow` scope stored as an env var)

---

### Stage 2 — User Control and Visibility

**Goal:** Give users more agency over which boards are monitored and make the system's health visible without requiring admin access.

#### 3.9 Board Selection

Users can enable or disable individual boards from their preferences page. A board toggle takes effect on the next scraper run. The scraper reads each user's enabled board list and only matches that user against listings from boards they've enabled.

This does not change what the scraper fetches — it fetches all boards every run regardless — but the matching and notification steps filter by user board preference.

#### 3.10 User-Facing Scraper Status

A small status section on the dashboard (not a full admin panel) shows:
- Last successful run timestamp per board
- Whether the most recent run returned results or flagged an error

This lets non-technical users understand why they may not be receiving alerts without needing to contact the admin.

#### 3.11 Salary Filter

An optional salary range filter added to preferences. If set, listings with parseable salary data outside the stated range are excluded. Listings with no salary data are not excluded — salary information is inconsistently available across boards.

---

### Stage 3 — Intelligence and Expansion

**Goal:** Improve match quality and expand coverage to boards requiring browser automation.

#### 3.12 LLM-Assisted Match Scoring

Keyword matching produces false positives (e.g. a listing that mentions "python" once in a footnote) and false negatives (e.g. a copywriting role described in terms the user didn't think to keyword). Stage 3 introduces optional LLM scoring.

For each keyword match, the user's skills summary and the full listing description are submitted to the Claude API with a prompt requesting a fit score from 0 to 10 and a one-sentence rationale. Users can set a minimum score threshold in preferences. Matches below the threshold are stored but not notified.

This is opt-in per user, not default — keyword matching remains the default. The LLM scoring adds per-match latency (~1–2 seconds) and a small API cost.

#### 3.13 Wellfound

Added in Stage 3 due to its React SPA architecture requiring Playwright, which significantly increases scraper runtime and maintenance burden. The Wellfound scraper is treated as non-critical — failures are logged and the run continues without it.

#### 3.14 LinkedIn

LinkedIn scraping is evaluated in Stage 3 but may remain permanently out of scope depending on the outcome of that evaluation. The legal risk (ToS violation, prior enforcement history) and technical countermeasures (bot detection, rate limiting, CAPTCHA) make it the hardest surface to sustain reliably. If included, it would use Playwright with rate limiting and would carry an explicit maintenance disclaimer.

---

## 4. User Flows

### 4.1 Registration and Onboarding

```
Landing page
  └── "Sign up" → Registration form (name, email, password)
        └── Submit → Account created → Onboarding step 1 (Role)
              └── Next → Onboarding step 2 (Keywords)
                    └── Next → Onboarding step 3 (Notifications)
                          ├── If Telegram selected → Telegram connect flow
                          └── Finish → Dashboard (with "You're all set" confirmation)
```

### 4.2 Telegram Connect Flow

```
Onboarding step 3 / Settings page
  └── "Connect Telegram" button clicked
        └── App generates one-time token (32 bytes, 15 min TTL), stores against user
              └── Deep link displayed: t.me/<botname>?start=<token>
                    └── User opens link → Telegram opens bot → user taps Start
                          └── Bot receives /start <token>
                                └── Token valid? 
                                      ├── Yes → Store chat_id, mark connected, confirm in Telegram
                                      └── No / expired → "Link has expired. Return to the app to reconnect."
```

The UI polls the `/api/notifications/telegram-status` endpoint every 3 seconds for up to 2 minutes after the deep link is shown. When `telegram_connected` flips to `true`, the UI updates without requiring a page reload.

### 4.3 Alert Delivery (Immediate)

```
GitHub Actions cron fires (every 6 hours)
  └── Scraper fetches all boards concurrently
        └── Results deduplicated and written to listings table
              └── Matcher iterates: for each new listing × each active user
                    └── Match? → Write to user_matches
                          └── User frequency = 'immediate'?
                                ├── Yes → Dispatch notification now (Telegram)
                                └── No  → Leave notified_at NULL (digest job picks up later)
```

### 4.4 Daily Digest Delivery

```
GitHub Actions digest cron fires (08:00 UTC daily)
  └── Query user_matches WHERE notified_at IS NULL, grouped by user
        └── For each user with pending matches:
              └── Format all matches into one message
                    └── Dispatch → mark notified_at = now()
```

### 4.5 Preference Edit

Any field in the user's profile or notification settings can be changed from the Settings page at any time. Changes take effect on the next scraper run. There is no confirmation step for most changes.

### 4.6 Pause and Resume

A toggle on the dashboard and settings page. When paused, the matching engine skips the user entirely — no matches are written, no notifications sent. Listings that appeared while paused are not retroactively matched when the user resumes.

---

## 5. Constraints and Limitations

### 5.1 Stale Listings

Job listings are often not taken down when a role is filled. Job Radar has no way to detect this from the outside. Users should treat every alert as "this was posted, not necessarily still open." This is documented in the UI with a short note below the dashboard listing count.

### 5.2 Render Cold-Start

The Render free tier sleeps inactive services. First page load after a period of inactivity takes 20–40 seconds. The UI displays a loading state rather than appearing broken. This is acceptable at this scale and documented for users during onboarding.

### 5.3 Keyword Matching Limitations

Keyword matching cannot understand context. "Python" will match a listing for a Python developer and also a listing that mentions a Python snake in a zoology research context. Users should set exclusion keywords aggressively. Stage 3 LLM scoring addresses this for users who opt in.

### 5.4 GitHub Actions Minutes Budget

A private repository gets 2,000 free minutes/month. A scraper run that includes Playwright (Stage 3) takes roughly 5 minutes. Four runs per day × 30 days = 600 minutes. This is within budget. If the budget becomes a concern, the run frequency can be reduced or the repository made public (which requires ensuring no secrets are committed).

### 5.5 (Removed)

---

## 6. Out of Scope

- OAuth / social login (all stages)
- Mobile native app
- Application tracking — saving jobs, adding notes, tracking status
- Browser extension
- Multi-language UI
- Team or shared accounts
- API access or webhooks for external tools
- Paid tier or billing
- Any employer-facing features
