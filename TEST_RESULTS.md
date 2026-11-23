# Dormie test and verification results

Executed against Python 3.12.16, SQLite, and headless Chromium, November 22, 2026.

## Automated service/API/migration suite

Command:

```bash
.venv/bin/pytest -q
```

**Latest independent-repository run: 42 passed.** Coverage includes:

- Seven domain tables, SQLite foreign-key enforcement, unique/check constraints, Monday/Sunday validation and migration upgrade/downgrade.
- Ratings, active-resident means, zero-rating generation blocks and integer-only values.
- Missing availability, unavailable residents and unassigned warnings.
- Deterministic sorting/tie breaks, historical burden, retries, snapshot/explanation immutability and safe idempotency.
- Original versus actual responsibility versus completed points; zero-filled group results and eligible-week averages.
- Delegation authorization, substitute eligibility, pending/accepted/rejected/cancelled transitions, no chains and completion race handling.
- Session login/signup/logout, CSRF and cross-origin guards, owner-only mutations, private reason filtering and validation.
- Retired chores reject new rating writes through the API as well as the interface.
- A two-thread generation race and completion-versus-acceptance race.
- Fresh Alembic install, seven-table seed, cross-table date triggers, idempotent seeding and downgrade/re-upgrade.

One non-failing Starlette deprecation warning recommends `httpx2` for its test client; the existing integration suite is passing with current `httpx`.

## Browser workflows

Command:

```bash
.venv/bin/python scripts/browser_check.py
```

**Result: 12 scenario groups passed.** The script runs a disposable database and its own local server. It verifies desktop at 1440 × 900; breakpoint/resizing at 1024, 900, 768 and 390 widths; mobile at 390 × 844 with actual touch events; session identity during browsing; both status panels; keyboard, arrows and Escape; assignment completion; rating and availability updates; statistics and rules; chore creation; unrated generation failure and recovery; idempotent generation; delegation request/cancel/reject/accept; new-resident onboarding and account switching; recoverable network errors; rapid resident navigation; reduced motion; one-resident/empty-catalog states; and absence of uncaught browser JavaScript errors.

Screenshots are in `artifacts/`: `welcome-desktop.png`, `welcome-mobile.png`, `desktop-closed.png`, `desktop-open.png`, `mobile-closed.png`, `mobile-open.png`, and `statistics-desktop.png`. The script records its last result in `artifacts/browser-results.json` and server log in `artifacts/browser-server.log`.

## Limits

The browser run used one headless Chromium installation and touch emulation, not a physical phone or tablet. Safari, Firefox, assistive technology and PostgreSQL were not tested. The app is configured for a single local server process. See DECISIONS.md for deployment and security boundaries.

## Independent working database setup

Created `/home/roi/Documents/Projects/Dormie-Draft2/dormie.db` from the preserved Draft 2 database using SQLite's online backup API. Applied `3c5d_integer_validation -> 4d6e_mysql_guards` to this independent working copy. `alembic current --verbose` reports `4d6e_mysql_guards (head)` and `alembic check` reports no new upgrade operations. The seven domain table row counts remain resident 5, chore 4, chore_rating 20, week 6, availability 35, assignment 24, delegation 2; SQLite integrity is `ok`, and `foreign_key_check` is empty. The original Draft 2 database and `/tmp/dormie-pre-migration-backup.db` were preserved; the original remains at `3c5d_integer_validation`.

The new local repository `/home/roi/Documents/Projects/Dormie-Draft2` was committed after staged-source review with message `Establish Dormie development baseline`. No remote was configured or push performed. Database and local environment files remain ignored.
