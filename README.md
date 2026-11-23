# Dormie

A local-first dormitory chore manager with a pixel-art common room, resident carousel, deterministic workload balancing, and one shared backend for desktop and mobile.

## Install and run

Requires **Python 3.12+ and MySQL 8.0.16+** (MySQL 8.4 recommended). No Node build is needed.

First, open MySQL as an administrator (`mysql -u root -p`) and create the database and local application user. Replace the example password:

```sql
CREATE DATABASE dormie CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
CREATE USER 'dormie'@'localhost' IDENTIFIED BY 'replace-me';
GRANT ALL PRIVILEGES ON dormie.* TO 'dormie'@'localhost';
```

Then run from this project directory:

```bash
# Skip creating the virtual environment if .venv already exists.
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock.txt
export DATABASE_URL='mysql+pymysql://dormie:replace-me@127.0.0.1:3306/dormie?charset=utf8mb4'
python -m alembic upgrade head
python -m app.seed
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Use your actual password in the URL; URL-encode special characters in the username/password. Set `DATABASE_URL` in each terminal that runs the application or migrations. `.env.example` is a reference; `.env` files are **not automatically loaded**. Without `DATABASE_URL`, the app retains its SQLite fallback (`dormie.db`). Existing SQLite data is not copied to MySQL; the seed creates a fresh demo and preserves an already populated database.

Open **http://127.0.0.1:8000**; API documentation is at **http://127.0.0.1:8000/docs**. Stop with Ctrl+C. On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1` and set the URL with `$env:DATABASE_URL = 'mysql+pymysql://...'`.

To inspect the MySQL database in MySQL Workbench, connect to `127.0.0.1:3306` as `dormie`, then refresh Schemas. Or use:

```bash
mysql -h 127.0.0.1 -u dormie -p dormie
```

```sql
SHOW TABLES;
SHOW CREATE TABLE assignment;
DESCRIBE resident;
SELECT resident_id, name, username FROM resident;
```

Always create the MySQL schema through Alembic, not `Base.metadata.create_all()`: migrations install the generated-column unique index, date/history triggers, and `app_write_lock` infrastructure table. This row serializes application writes transactionally, including generation and delegation/completion races. MySQL uses InnoDB, strict SQL mode, and READ COMMITTED isolation. Keep MySQL's strict SQL mode enabled. MySQL coerces fractional inputs stored in INT columns; the API rejects non-integer ratings/weekdays before storage (the SQLite-only raw fractional-value test is skipped on MySQL). Seven domain tables remain, plus Alembic version tracking and the write-lock table.

Set `SECRET_KEY` to a random secret for stable sessions across restarts. Without it, restarting signs everyone out. Set `COOKIE_SECURE=1` only behind HTTPS.

SQLite remains available for local tests or an isolated demo:

```bash
export DATABASE_URL=sqlite:///./classroom-demo.db
python -m alembic upgrade head
python -m app.seed
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Demonstration accounts

| Resident | Username | Password |
| --- | --- | --- |
| Alex | `alex` | `Dormie2026!` |
| Bea | `bea` | `Dormie2026!` |
| Carlo | `carlo` | `Dormie2026!` |
| Dana | `dana` | `Dormie2026!` |

The seed uses the fixed **November 9–15, 2026** demonstration week and four earlier completed weeks (October 12–November 8). Seeded ratings are exactly those specified in Part 5: Sweep floor 2.00, Wash dishes 3.00, Clean bathroom 4.50, Mop floor 3.50.

The UI defaults to the actual current Monday in Asia/Manila. **Choose November 9, 2026 in the week picker to inspect the fixed demo.** It is deliberately not presented as the current week. The seed command is non-destructive and does nothing if any resident already exists.

For a fresh, isolated classroom dataset, choose a new database filename instead of deleting existing work:

```bash
export DATABASE_URL=sqlite:///./classroom-demo.db
python -m alembic upgrade head
python -m app.seed
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Choose an unused filename; seeding preserves an already populated database.

## Classroom demonstration (10–15 minutes)

1. **Welcome and identity.** Open the title screen. Select Resident login, choose Alex, and authenticate. Selecting a login profile only prefills the username; a password is still required.
2. **Desktop resident browsing.** At 1440 × 900, choose November 9, 2026. Alex is centered and both panels start closed. Use arrows or focus the stage and use Left/Right. Click Bea to open Resident Info and Current Status around the character. The account button still says Alex. Browse with panels open, press Escape, and reopen a character.
3. **Mobile controls.** Resize to 390 × 844. The selected resident, week, and details state remain the same. Collapse the sheet to see the full-body character. Swipe the character horizontally or tap arrows. Drag the sheet handle up/down, or use Expand details/Collapse. Scroll the expanded sheet body independently. Return to my status selects Alex without logging in again.
4. **Ratings and availability.** Open Chores & Ratings. Inspect all four exact means and four ratings per chore. Change one of Alex’s ratings and save; the collective mean changes, but historical assignment points remain frozen. Open My Availability, change a weekday, and save. Explain that these booleans repeat every week and existing assignments are preserved.
5. **Explain an assignment.** Open Assignments, select the fixed demo week, and open Clean bathroom → Details → Why this assignment? The stored explanation includes score, rating count, available weekday, historical average, prior planned points, candidate burdens, and tie-break order.
6. **Accepted transfer and completion.** In the untouched seed, Carlo originally received Clean bathroom (4.50 pts), and Alex is its accepted substitute. Original assignment stays Carlo’s; actual responsibility belongs to Alex. Complete it as Alex and confirm. Completed workload becomes 4.50 for Alex from this chore. Reopening shows the Manila completion timestamp.
7. **Pending request.** The seed has Dana’s Mop floor request pending for Alex. Open Delegations as Alex and accept or reject it. A pending request does not transfer responsibility; acceptance does, and is not task completion. Sign in as Dana separately to demonstrate cancellation on a fresh dataset.
8. **Request lifecycle.** Sign in as Bea. On the demo week, Wash dishes is pending with no active request. Open its details and Request substitute; choose an eligible resident and supply a reason. Show Incoming/Outgoing/History from each account. After rejection or cancellation, create a new request. After acceptance, no further delegation is allowed.
9. **Generation.** Select the current or an upcoming Monday in Assignments. Generate and confirm; review assignments and explanations. Generate again to show zero new assignments and unchanged owners. Add an unrated chore to demonstrate the blocking error, rate it, and retry. To demonstrate an unassigned warning, all residents must explicitly be unavailable on that chore’s due weekday; generation never invents availability.
10. **Statistics and policies.** Explore all three metrics, four period options, and resident/group filters. Show the accessible data table and zero-point residents. Open Dorm Rules → Quiet hours and show that policies are pending approval.
11. **New resident.** Log out, register a new account, save recurring weekdays, review ratings, and finish setup. No fictitious points are awarded. Resume setup is available under My Profile.

## Tests

Run the service/API/migration/concurrency suite:

```bash
source .venv/bin/activate
python -m pytest -q
```

To run the same service, API, and concurrency tests on MySQL, set a test account URL. The account must be allowed to create and drop databases. Each test creates its own randomly named `dormie_test_*` database and removes only that database afterward; the existing application database is untouched. The SQLite migration regression test still runs separately.

```bash
export MYSQL_TEST_URL='mysql+pymysql://test_user:password@127.0.0.1:3306/?charset=utf8mb4'
python -m pytest -q
unset MYSQL_TEST_URL
```

Run the browser suite (optional development dependency):

```bash
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python scripts/browser_check.py
```

If Google Chrome or Chromium is installed, the script uses it automatically. Set `CHROME_PATH` to select another compatible executable. Otherwise it uses Playwright’s installed Chromium. The script launches its own server on a free loopback port, migrates and seeds a temporary database, executes workflows, saves screenshots/results to `artifacts/`, and stops its server. **It does not alter `dormie.db`.**

See [TEST_RESULTS.md](TEST_RESULTS.md) for executed results and [docs/BROWSER_CHECKLIST.md](docs/BROWSER_CHECKLIST.md) for repeatable manual checks. Browser verification uses Chromium emulation; physical touchscreen devices and other browser engines require separate validation.

## Project map

- `app/models/`: seven SQLAlchemy domain models and relational constraints.
- `alembic/versions/`: explicit schema migration and SQLite cross-table due-date guards.
- `app/services/`: authentication, scoring, allocator, responsibility resolution, delegation/completion, reporting queries.
- `app/api/`: Pydantic inputs and protected API routes.
- `app/templates/index.html`: Jinja2 document shell.
- `app/static/`: responsive CSS, vanilla JavaScript, separate original SVG artwork.
- `app/seed.py`: deterministic, non-destructive classroom data.
- `tests/`: temporary-database service/API, migration and concurrency tests.
- `scripts/create_assets.py`: reproducible original pixel artwork source.
- `scripts/browser_check.py`: isolated browser walkthrough and screenshots.
- `DECISIONS.md`: calendar, fairness, persistence, security and scope decisions.

## Main API surface

Authentication: `POST /api/auth/signup`, `/api/auth/login`, `/api/auth/logout`; `GET /api/me`; `PATCH /api/me`. Public `GET /api/auth/residents` exposes only login identifiers and names. Other endpoints require authentication.

Shared data: `GET /api/residents`; `GET /api/residents/{id}/status?start=YYYY-MM-DD`; `GET /api/chores`; `POST /api/chores`; `PUT /api/chores/{id}`; `PUT /api/chores/{id}/rating`.

Scheduling: `GET/PUT /api/availability`; `GET /api/weeks`; `POST /api/weeks/generate`; `GET /api/assignments?start=YYYY-MM-DD`; `GET /api/assignments/{id}`; `POST /api/assignments/{id}/complete`.

Delegation: `GET /api/assignments/{id}/substitutes`; `POST /api/assignments/{id}/delegations`; `GET /api/delegations`; `PATCH /api/delegations/{id}`. Statistics: `GET /api/statistics?start=YYYY-MM-DD`.

For authenticated writes, copy the CSRF token returned by `GET /api/me` into the `X-CSRF-Token` header and retain the session cookie. Request bodies use JSON. Ratings and availability endpoints always address the authenticated resident; they accept no arbitrary resident ID.

## Scope

One dormitory, resident-only access, weekly chores, weekday availability, self-reported completion, and static unapproved rules. No admin roles, room database, timetables, durations, XP, photo verification, notifications table, or workload-history table. See [DECISIONS.md](DECISIONS.md) for remaining limitations.

MySQL implementation references: [SQLAlchemy MySQL dialect](https://docs.sqlalchemy.org/en/20/dialects/mysql.html), [generated columns](https://dev.mysql.com/doc/refman/8.4/en/create-table-generated-columns.html), and [unique indexes](https://dev.mysql.com/doc/refman/8.4/en/create-index.html).
