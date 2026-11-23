# Dormie — AI project handoff

Use this file to give another AI a concise but complete picture of the Dormie application before asking it to propose or implement improvements. The numbered project specifications in this folder remain the source of truth when details here are incomplete. The current UI refinement phase is specified by `06 - UI Polish and Quality Assurance.md`.

## Project summary

Dormie is a responsive, local-first dormitory chore management web app presented as a pixel-art dorm simulation. Residents sign in, record recurring weekday availability and chore intensity ratings, review weekly assignments, complete chores, delegate work, and view personal or dorm-wide workload statistics. It uses one shared backend and database on desktop and mobile.

The product combines the cozy illustrated dorm environment, resident-character carousel and game-like welcome screen with actual authenticated workflows and database-backed records. Resident browsing is read-only: changing the displayed resident never changes the signed-in account.

## Technology and architecture

- Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2, Alembic, SQLite and Jinja2.
- Responsive frontend in vanilla JavaScript and CSS. No frontend build step or external asset requests.
- One server-rendered HTML shell; API-backed views are assembled from reusable UI functions in `app/static/app.js`.
- Original, local SVG artwork lives in `app/static/assets/`; source generator is `scripts/create_assets.py`.
- Default data store is `dormie.db`. `DATABASE_URL` can select another SQLite file.
- Seven domain tables: `resident`, `chore`, `chore_rating`, `week`, `availability`, `assignment`, and `delegation`.

## Main implemented features

- Welcome/login, registration, password authentication, session identity and setup resumption.
- Recurring Monday–Sunday availability and 1–5 chore intensity ratings.
- Shared chore catalog with create/edit/retire behavior and protection for chores with assignment history.
- Deterministic weekly assignment generation with candidate eligibility, workload fairness, historical burden, stable tie breaks, safe idempotency and an explanation snapshot for each assignment.
- Completion by the responsible resident; delegation request, cancellation, acceptance and rejection flows with eligibility rechecks and preserved history.
- Workload reports distinguishing originally assigned points, current responsibility and completed points, with period/resident/group selection and zero-filled residents.
- Static read-only dorm rules labeled pending approval.
- Desktop coverflow-style resident carousel, keyboard/arrows/click navigation and two contextual status panels around the selected character.
- Mobile resident swipe, arrow controls, bottom-sheet drag/expand/collapse, native content scrolling, compact navigation and full-body resident when collapsed.
- Loading, empty, error, confirmation and success states across the main workflows.

## Assignment and workload notes

The allocation logic is implemented in `app/services/core.py`. It follows the specifications’ deterministic greedy process; the method and inputs are frozen in `assignment.rationale` when generated. The exact score interpretation, history window and date conventions are recorded in `DECISIONS.md` and the relevant spec. Avoid changing fairness rules without comparing proposed changes to those requirements and updating their tests.

Assignment history preserves the original owner and point snapshot. Accepted delegation changes who is responsible, not who originally received the chore. Pending requests do not transfer responsibility. Completing a chore cancels a pending request atomically. The statistics query derives responsibility from accepted delegation records rather than maintaining a separate workload-history entity.

## Security and data constraints

- Passwords are Argon2id hashes; API responses do not expose password hashes.
- Session cookies are signed, HttpOnly and SameSite Strict. Authenticated writes use a CSRF token; cross-origin writes are rejected.
- Writes use the authenticated resident identity rather than trusting a client-supplied resident ID.
- Private delegation reasons are restricted to relevant participants.
- Relational uniqueness/check constraints and SQLite foreign-key enforcement are enabled. SQLite migration triggers guard cross-table due-date consistency and assignment history rules.
- The app targets one local server process. PostgreSQL equivalents, production deployment, rate limiting, password recovery and multi-process locking are not part of the validated implementation.

## Key files

| Path | Purpose |
|---|---|
| `01 - Project Overview & Architecture.md` … `05 - Seed Data, Testing & Delivery.md` | Product and technical requirements; authoritative specs |
| `06 - UI Polish and Quality Assurance.md` | Incremental visual, interaction, accessibility and QA requirements for the next phase |
| `Dormie - Codex Improvement Prompts.md` | Additional project-specific improvement prompts |
| `app/main.py` | FastAPI app, middleware, template and static mounting |
| `app/db.py` | SQLAlchemy engine/session setup |
| `app/models/__init__.py` | Domain schema and constraints |
| `app/api/routes.py` | HTTP routes and request validation |
| `app/services/auth.py` | Password hashing and auth helpers |
| `app/services/core.py` | Scheduling, fairness, delegation, completion and reporting |
| `app/static/app.js` | Client state, rendering, navigation and API interactions |
| `app/static/style.css` | Responsive visual system and interactions |
| `app/templates/index.html` | HTML shell |
| `alembic/versions/` | Database migrations and SQLite guards |
| `app/seed.py` | Non-destructive demonstration data |
| `tests/` | Domain, API, migration and concurrency coverage |
| `scripts/browser_check.py` | Isolated Chromium browser workflows and screenshot capture |
| `README.md` | Exact setup, run, demo-account and classroom walkthrough instructions |
| `DECISIONS.md` | Assumptions and implementation choices |
| `AUDIT_RESULTS.md` | Specification/reference audit findings and remaining limitations |
| `TEST_RESULTS.md` | Executed verification and limitations |
| `artifacts/` | Rendered desktop/mobile screenshots and browser results |

## Run the application

From this project directory, with Python 3.12 installed:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock.txt
python -m alembic upgrade head
python -m app.seed
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`. Demonstration accounts are `alex`, `bea`, `carlo`, and `dana`; each password is `Dormie2026!`. The fixed demonstration week is November 9–15, 2026. See `README.md` before resetting or reseeding data; seeding is deliberately non-destructive.

## Current verified status

Last recorded application validation (November 22, 2026):

- `pytest -q`: **41 passed**.
- `python scripts/browser_check.py`: **12 scenario groups passed** in headless Chromium, covering 1440 × 900 desktop, 390 × 844 mobile, resizing, touch gestures and end-to-end workflows.
- `alembic check`: no new upgrade operations detected.
- `node --check app/static/app.js`: passed.

### Workspace and migration diagnostic (November 22, 2026)

- Draft 2 now has an independent local Git repository at `/home/roi/Documents/Projects/Dormie-Draft2`, created from a copy. The existing DS187 repository/history and Draft 1 were left intact; no remote was configured, and the new repository has not been staged, committed or pushed. Its `.gitignore` excludes environment secrets (while allowing `.env.example`), virtual environments, Python caches, local database/backup files and generated coverage data. Review `git status --short` in the new repository before any future staging.
- A consistent SQLite online backup was created at `/tmp/dormie-pre-migration-backup.db`. The original database remains at revision `3c5d_integer_validation`; it was not upgraded.
- A separate copy at `/tmp/dormie-migration-test.db` was successfully migrated to `4d6e_mysql_guards` (the sole head). On that copy, all seven domain-table counts matched before/after (resident 5, chore 4, chore_rating 20, week 6, availability 35, assignment 24, delegation 2), `integrity_check` returned `ok`, and `foreign_key_check` returned no violations. `alembic check` reported no new operations on the migrated copy.
- The original DB upgrade remains pending owner approval. After approval, from the independent repo, set `DATABASE_URL` explicitly to the intended original DB before running `alembic upgrade head`; verify with `alembic current --verbose` and `alembic check`. Do not accidentally point the migration at a different working-directory-relative `dormie.db`.
- Migration explanation: migration `4d6e_mysql_guards` is a no-op for SQLite but still must be recorded as current; the prior check failed because the original DB revision lagged one revision behind the head.
- From `/home/roi/Documents/Projects/Dormie-Draft2`, the isolated copy reported current revision `4d6e_mysql_guards (head)` and `alembic check` passed. The regression suite from that independent checkout passed **42 tests** (one Starlette/httpx deprecation warning). Original `dormie.db` SHA-256 remained `6dba3955a38f3cca7330f957c4122bd058aef36cd1a760e946e5e5ece278804f`, still at `3c5d_integer_validation` with unchanged counts, confirming it was not modified.
- Final setup: `/home/roi/Documents/Projects/Dormie-Draft2/dormie.db` is now a persistent consistent copy of the original, migrated to `4d6e_mysql_guards` and verified with all seven original row counts, SQLite integrity, foreign-key check, `alembic current` and `alembic check`. The original database and `/tmp/dormie-pre-migration-backup.db` remain preserved. Independent repository initial commit message: `Establish Dormie development baseline`; no remote/push. See `TEST_RESULTS.md` for exact counts and checks.

Latest visual captures are in `artifacts/`, especially `desktop-open.png`, `mobile-open.png`, `welcome-desktop.png`, and `welcome-mobile.png`. Browser tests emulate touch; they do not constitute physical-device or cross-browser testing.

### UI polish phase handoff (November 2026)

The follow-up request introduced `06 - UI Polish and Quality Assurance.md`, which prioritizes asset and visual refinement, motion, rules presentation, accessibility and a broader browser/viewport QA matrix. In the latest review turn, that specification and `Dormie - Codex Improvement Prompts.md` were located and partially inspected. No UI-polish implementation, complete review of all requested references, or new test run was completed in that turn. The results above are the previous baseline and must be rerun before claiming current verification. Start by reading all requirements in Part 6, reviewing all numbered specs and references, and inspecting current artifacts/source; then complete its phases in order. Do not treat the phase as done or the historic test counts as new results.

## Known limitations and improvement opportunities

- Artwork is original and local, but simpler than the richer painterly/isometric reference images; it is not a pixel-perfect recreation.
- Only Chromium has been used for browser automation. Physical devices, Safari, Firefox and assistive-technology testing remain open.
- The Part 6 cross-browser, contrast, keyboard/screen-reader and detailed visual comparison work is not yet completed. Verify Firefox and WebKit availability before reporting results; unsupported/unavailable engines should be recorded as not run.
- Schema triggers and concurrency behavior target SQLite. PostgreSQL support is not validated.
- This is a single-dorm, resident-only, local classroom application. There is no admin role, multiple dorm/room model, notifications, password recovery, physical chore verification or approved rules content.
- Rules remain read-only placeholders until actual dorm policies are supplied.
- See `AUDIT_RESULTS.md`, `DECISIONS.md` and `TEST_RESULTS.md` before proposing work, so known constraints and completed requirements are not mistaken for gaps.

## Suggested prompt for another AI

> Continue improving the existing Dormie application; do not rebuild it. Read `AI_HANDOFF.md`, all six numbered specifications, `Dormie - Codex Improvement Prompts.md`, `DECISIONS.md`, `AUDIT_RESULTS.md`, and `TEST_RESULTS.md`, inspect every mobile/desktop reference image and the existing source before editing. Use Part 6 as the primary specification. Implement its phases in order: original local pixel-art assets; visual refinement; accessible animations/interactions; better rules presentation without inventing policies; accessibility; then desktop/mobile and available Chromium/Firefox/WebKit QA. Preserve the shared backend, schema, authentication/authorization, database-driven content, deterministic fairness algorithm, cloud deployment configuration and working workflows. Do not stop at a plan. After each phase run relevant regression checks, inspect actual rendered UI, capture before/after screenshots, fix defects, and update the handoff, decisions, audit and test records. Distinguish verified outcomes from historical results and clearly document unavailable browsers/devices and remaining limitations.

