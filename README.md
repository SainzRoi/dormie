# DormTogether · DS 187

A local-first dormitory chore assignment and monitoring application implementing [the project specification](DS187_Codex_Project_Spec.md). FastAPI, SQLAlchemy 2, Alembic, SQLite, a Jinja-served application shell, and lightweight browser JavaScript. No external services or frontend build are needed to run it.

New to the project? Read [the simple program guide](PROGRAM_GUIDE.md) for the everyday workflow, code map, and assignment example.

To share the app online, follow [the GitHub + Vercel deployment guide](DEPLOYMENT.md). Hosted use requires PostgreSQL; local use keeps SQLite.

## Setup and run

Requires **Python 3.12+** and internet access for the initial dependency installation. Run from this project directory on Linux/macOS:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -c "import secrets; from pathlib import Path; p=Path('.env'); p.write_text(p.read_text().replace('replace-with-a-random-secret-at-least-32-characters', secrets.token_hex(32)))"
set -a
source .env
set +a
python -m alembic upgrade head
python -m app.seed
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. API documentation is at `/docs`; a liveness endpoint is at `/health`. The database is `dorm.db` in the project directory. The `.env` file is loaded by the shell commands above, not automatically by the application. Repeat the activation and `source` commands in a new terminal. A missing session secret generates an ephemeral development key, so restarting then signs residents out.

This machine’s default Python may be 3.10. A cached Codex Python 3.12 was found at `/home/roi/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12`; it can replace `python3.12` in the first command on this machine. That path is not required on other machines.

For HTTPS hosting, set `COOKIE_SECURE=true`. This version is intended for a local classroom demonstration, not public internet deployment.

## Demo accounts and dates

| Resident | Username | Password |
|---|---|---|
| Alex | `alex` | `DormDemo2026!` |
| Bea | `bea` | `DormDemo2026!` |
| Carlo | `carlo` | `DormDemo2026!` |
| Dana | `dana` | `DormDemo2026!` |

The idempotent seed creates four chores, the specified ratings with means **2.00, 3.00, 4.50, and 3.50**, recurring availability, four completed historical weeks beginning October 12, 2026, and pending assignments for **November 9–15, 2026**. Seed dates and allocation history are fixed independently of the computer clock. Repeating the command preserves existing edits and assignments.

An optional separate command demonstrates one accepted delegation without completing the chore:

```bash
python -m app.seed --delegation
```

It preserves the original assignee and is idempotent. Run the main seed first. Use a fresh database for an untouched classroom fixture; do not delete a database containing work you want to keep.

## Classroom walkthrough

1. Sign in as `alex`. Change “Week beginning” to **2026-11-09**. Review the overview, onboarding checklist, and points.
2. Open **Chores & ratings**. Show the bathroom’s **4.50** collective score and four ratings. Edit a rating, then show that existing assignments retain their frozen points.
3. Open **My availability**. Save seven recurring weekday choices. Explain that these persist across weeks and missing days are unavailable.
4. In **Weekly assignments**, expand an assignment rationale to explain availability, historical average, planned points, and tie-breaks.
5. Select a current or future Monday and click **Generate missing assignments**. Click again to demonstrate idempotency. An unrated active chore blocks generation; a chore with no eligible residents stays unassigned with a warning.
6. For a pending chore, sign in as its original assignee, select an available substitute, and enter a reason. Sign out and sign in as that substitute. Accept in **Delegations**. Show the original assignee remains recorded. Reject or cancel another pending request to demonstrate preserved history.
7. Mark the accepted chore completed as the substitute. The original assignee cannot do so after transfer.
8. Open **Workload statistics**. Compare original, actual, and completed weekly totals, all-time cumulative totals, eligible-week averages, and the four-week chart. All residents appear, including those with zero points.

If demonstrating after November 2026, the seeded week remains viewable and its pending chores/delegations remain actionable. Generate new chores only for the current or future weeks.

## Tests

After installing dependencies:

```bash
python -m pytest -q
```

The integration tests apply Alembic migrations to a separate temporary SQLite database for each test. They cover authentication, CSRF, ownership, validation, generation, delegation, reporting views, migration constraints, and concurrent generation. They never use `dorm.db`.

The framework-independent database/service suite can also be run alone:

```bash
python -m unittest tests.test_domain -v
```

Optional UI behavior tests (Node.js 18+):

```bash
npm install
npm test
```

These use JSDOM and fixture API responses to test page rendering, escaping, recurring-availability and rating submissions, and authentication UI. They do not replace real-browser or HTTP integration testing. Node is not required to run the application.

**Verification in the implementation environment:** 29 real SQLite service/model/seed tests passed under Python 3.12 using locally cached dependencies. See [VERIFICATION.md](VERIFICATION.md) for the exact commands, UI test result, and blocked checks. FastAPI/Alembic installation was blocked by network/DNS restrictions, so full HTTP tests, actual migration execution, and application launch have not been verified here. Do not interpret the service tests as passing the entire acceptance checklist.

## Behavior and architecture

- Seven domain tables: resident, chore, chore_rating, week, availability, assignment, delegation. Alembic also maintains its infrastructure version table. `weekly_workload` is a SQL view, not a history table.
- Only weekly chores; weekdays are 1=Monday to 7=Sunday. All timestamps originate in UTC and display in Asia/Manila.
- Residents may manage shared chores. Retiring preserves history. A chore with assignment history cannot have its weekday changed; retire it and create a replacement.
- Generation snapshots the average of active residents’ ratings. Unrated active chores block the entire generation action.
- Chores sort by descending score, then ID. Candidates must be active, joined by the due date, and explicitly available. The chosen candidate minimizes **historical average + current-week responsibility points**, then target-week chore count, then resident ID.
- History uses the previous four calendar weeks that have ended before both today and the selected target week. Zero-work weeks count; weeks before joining do not. “Ended” describes the calendar week, not whether every task was completed.
- Current/future-week generation fills missing chores without reshuffling. Writes reserve the SQLite write lock before reading decision state; uniqueness constraints provide a second guard against duplicates.
- A pending delegation does not transfer responsibility. Acceptance transfers points without changing the original assignee or marking completion. Accepted delegations cannot be chained. Completing the original task cancels any still-pending request.
- Weekly reporting is selected-week specific. Cumulative reporting is all recorded weeks, including planned assignments. Average denominator spans the first recorded week or joining week (whichever is later) through the later of the selected week and latest recorded week, including zero-work weeks.

```text
app/models/         Seven SQLAlchemy models and constraints
app/services/       Allocation, reporting, completion, delegation rules
app/api/            Validated REST endpoints and authorization
app/templates/      Accessible application shell
app/static/         Responsive styles and browser behavior
app/seed.py         Fixed demo data and optional delegation
alembic/            Initial schema migration, view and SQLite triggers
tests/              Service, HTTP integration and UI behavior tests
```

Session cookies are signed, HttpOnly, SameSite=Strict, and expire after eight hours. All mutations, including login, require a CSRF token from `GET /api/session`, supplied as `X-CSRF-Token`. Passwords are Argon2id hashes. Request models reject unexpected fields; resident IDs for ratings and availability always come from the authenticated session.

For implementation choices and limitations, see [DECISIONS.md](DECISIONS.md). Framework references: [SQLAlchemy SQLite constraints and partial indexes](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html), [Starlette session middleware](https://www.starlette.io/middleware/).
