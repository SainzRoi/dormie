# Dormie implementation audit

Audit date: 2026-11-22. This review covers the five supplied specifications, all reference images in `references/mobile/` and `references/desktop/`, the application source, relational schema/migrations, API and service behavior, and the desktop/mobile browser workflows.

## Findings and corrections

| Area | Audit result | Correction / verification |
|---|---|---|
| Architecture and delivery (spec 01) | Required FastAPI, SQLAlchemy, Alembic, SQLite, server templates and one shared responsive client are present. Local install/run instructions, decisions, test records, demo data/accounts and classroom walkthrough are provided. | No separate mobile backend or application. Verified through migrations and isolated-server browser run. |
| Relational design (spec 02) | Seven domain tables are used. Foreign keys, unique and check constraints, active delegation guard, date consistency triggers and immutable assignment snapshots align with the documented model. No workload-history entity was added. | Migration upgrade/downgrade and re-upgrade are in the automated suite; SQLite foreign-key enforcement and cross-table date rules are tested. See portability limitation below. |
| Business rules (spec 03) | Deterministic assignment ordering/tie-break, rating-based intensity, availability filtering, prior completed-week burden, unassigned warnings and explanation snapshots are covered. Original owner, current responsible resident and completed points remain distinct under delegation. | Tests cover deterministic retries, zero ratings, missing/unavailable candidates, historical windows, idempotence, concurrent generation, delegation lifecycle and completion races. Added rejection of rating writes to retired chores; this was a real API-only gap found during audit. |
| Workflow and UI (spec 04) | Registration/login, onboarding, weekday availability, chore ratings, generation, completion, delegation, personal/group summaries, rules, account switching, and error/success/empty states are implemented. Browsing the resident carousel changes the viewed profile, never the authenticated identity. | Browser suite exercises all major paths, including mobile gesture interactions and desktop keyboard/panels. Rules remain read-only pending dorm approval, as documented. |
| Seed, testing and delivery (spec 05) | Demonstration data and accounts are reproducible; test and demo instructions are documented. | Final pytest run: **41 passed**. Browser walkthrough: **12 scenario groups passed**. See `TEST_RESULTS.md`. |
| Visual references | The palette, game-style welcome, compact navigation, illustrated room, consistent resident sprites, desktop coverflow and paired panels, and mobile character/bottom-sheet presentation are present. | Mobile swipe and sheet drag are separated by gesture region/axis; arrow and accessible expand/collapse controls are also present. Screenshots are captured at 1440 × 900 and 390 × 844, plus the responsive breakpoint set. |

## Audit fixes

- API rating writes now check that the chore remains active and return HTTP 409 for retired chores. The UI already prevented this action; the API now enforces the same lifecycle rule. `test_retired_chore_rejects_rating_updates` protects it.
- Improved mobile navigation and dashboard-caption text sizing for legibility at the reference viewport.
- Added a dedicated 390 × 844 welcome-screen capture to the browser verification artifacts.

## Remaining limitations

- The supplied references depict richer, painterly/isometric pixel scenes than the original local SVG assets. The implementation follows their earthy palette, dorm staging, silhouettes and game presentation, but the art is an original, simpler interpretation rather than a pixel-for-pixel match.
- Browser verification used headless Chromium and emulated touch input; physical phones/tablets, Safari, Firefox and assistive-technology testing were not available in this run.
- SQLite-specific triggers and transaction locking are tested. PostgreSQL equivalents and multi-process locking have not been implemented or validated.
- The app is a local, single-server classroom demo. Public deployment still needs operational hardening described in `DECISIONS.md`; this is not represented as production hosting.
- Rules are intentionally labeled pending approval because no actual dorm policy was supplied. Completion is self-reported and has no physical-work verification.

## Artifacts

Rendered views are under `artifacts/`: `welcome-desktop.png`, `welcome-mobile.png`, `desktop-closed.png`, `desktop-open.png`, `mobile-closed.png`, `mobile-open.png`, and `statistics-desktop.png`. Browser scenario results are in `artifacts/browser-results.json`; exact commands and test details are in `TEST_RESULTS.md`.

## Independent repository and database setup (2026-11-22)

Draft 2 is now prepared as an independent local repository at `/home/roi/Documents/Projects/Dormie-Draft2`. Draft 1 and the DS187 Git history were preserved. The reviewed initial commit is `Establish Dormie development baseline`; no remote was configured or push performed. The project `.gitignore` excludes secrets/environment files (except `.env.example`), local databases/backups, virtual environments, Python caches and coverage output.

The independent repository has its own persistent `dormie.db`, copied consistently from the original database and migrated to `4d6e_mysql_guards`. All seven domain tables and row counts were preserved (5, 4, 20, 6, 35, 24, 2); integrity and foreign-key checks pass, and Alembic check is clean. The original Draft 2 database and the pre-migration backup remain unchanged. Regression suite: 42 passed, one non-failing Starlette/httpx deprecation warning. The original database was not upgraded.
