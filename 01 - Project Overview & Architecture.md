# Part 1: Project Overview & Architecture

> **Source Instructions:** Build a complete, runnable, local-first web application from this specification. Do not stop at scaffolding, mockups, or an ERD. Implement the database, migrations, backend, frontend, tests, sample data, and setup documentation. Document any unstated implementation choices in `DECISIONS.md`.

## 1. Project Goal and Scope

Create a database-driven system for **residents of one shared dormitory** to distribute and monitor recurring household chores fairly. The system's main objective is **fair and explainable allocation**, not productivity measurement. Different residents perform chores at different speeds, so **do not use estimated time/duration for workload scoring**.

### Core Capabilities
The application must let residents:
1. Create/access their resident profiles.
2. View the common chore catalog and **rate the perceived intensity** of each chore on an integer scale from **1 to 5**.
3. Enter their **recurring weekday availability** once, based on their semester schedule, and update it when circumstances change (**do not require new availability submissions every week**).
4. View chore assignments within a fixed **Monday–Sunday** week.
5. See why a chore was assigned, using availability and workload history.
6. Mark tasks as completed.
7. Request a delegation when unexpectedly unavailable, with another eligible resident accepting or rejecting the request.
8. View **weekly, cumulative, and average workload points** for themselves and the group.
9. Browse shared resident status through a pixel-art character carousel without changing the authenticated account. On mobile, swipe or tap arrows and drag the status sheet up/down. On desktop, browse with click/arrow/keyboard controls and click a character to open two side-by-side status panels around that character (see Part 4).

### Out of Scope for MVP (Strict Exclusions)
Only dormitory residents use the application. Do **not** invent or implement the following features:
- Multiple dormitories or room management modules.
- Dormitory manager or administrator roles.
- Class timetable ingestion or class-hour conflict detection (`CLASS_SCHEDULE` entity).
- Separate temporary unavailability tables/entities.
- Estimated duration or time-based workload scoring (`estimated_minutes`).
- Automatic external notifications, email, SMS, or calendar integrations.
- Objective verification of the quality of completed chores.
- A permanent physical `WORKLOAD_HISTORY` table.
- Complex optimization or machine-learning assignment models.

---

## 2. Technology Stack & Delivery

Use this stack unless an existing repository already has a suitable working stack:

- **Backend:** Python 3.12+, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic.
- **Database:** SQLite for easy local classroom demonstration, with conventional relational schema and foreign keys enabled. Keep database access portable enough to switch to PostgreSQL later.
- **Frontend:** One responsive web UI using server-rendered templates plus lightweight JavaScript and CSS, or an existing repository frontend framework if present. No external paid services. Use a shared data/service layer and viewport-specific presentation: mobile bottom sheet; desktop coverflow-inspired resident carousel, compact top navigation, and click-to-open left/right status panels. No separate desktop application or desktop-specific database is required.
- **Tests:** `pytest`, including API/integration tests with a temporary test database.
- **Timezone:** `Asia/Manila` for scheduling and displayed timestamps; store UTC timestamps consistently and convert on display.

### Recommended Repository Structure
If starting from an empty repository, create a clean directory structure:
- `app/models`
- `app/services`
- `app/api`
- `app/templates`
- `app/static`
- `alembic`
- `tests`
- `requirements.txt` or `pyproject.toml` (with pinned or bounded dependencies)
- `README.md` (with exact setup, migration, seed, test, and run commands)
- `.env.example` (if configuration is used)
- `DECISIONS.md` (for implementation assumptions and known limitations)
