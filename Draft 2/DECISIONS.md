# Implementation decisions

## Source and scope

All five supplied Markdown documents and all 12 mobile plus 3 desktop reference images were inspected before implementation. The repository contained no implementation or AGENTS.md. The application follows the specified Python 3.12/FastAPI/SQLAlchemy/Alembic/SQLite/Jinja2 stack. Vanilla JavaScript renders reusable functional components into the server-rendered document shell. All artwork is discrete, original local SVG; no mockup screenshot is used as a screen or background.

The Sites skill was consulted for local implementation/preview guidance. Part 1 explicitly requires a local-first classroom application; no hosted Site or external service was created.

## Seven entities and schema

Exactly seven domain tables: resident, chore, chore_rating, week, availability, assignment, delegation. Alembic creates its standard migration metadata table, `alembic_version`; it is infrastructure, not a domain entity. No workload history table exists.

The permitted authentication fields and active flags are used. **One justified additional column** is `assignment.rationale` (JSON): it freezes the score/rating count, availability weekday, historical average, planned points, adjusted burden, historical period, candidates and tie-break rule at generation. Reconstructing this later from mutable ratings/availability would produce false explanations. This addition does not change the fairness algorithm or introduce an entity.

Uniqueness and check constraints cover ratings, availability, weekly chores, week dates, status/timestamp consistency, point ranges and active delegations. Foreign keys are enabled on every SQLite connection. SQLite triggers enforce exact assignment due dates against chore/week, prevent changes to assigned week dates, and block changing the due weekday of a chore with assignment history. Retire and replace such a chore instead. Names/descriptions can change; historical point and rationale snapshots remain fixed.

The portable service layer uses ordinary SQLAlchemy queries. The initial SQLite calendar checks and cross-table triggers need dialect-specific equivalents before PostgreSQL deployment. PostgreSQL is a migration path, not a tested target in this delivery.

## Fairness and dates

- Weekday 1 means Monday; 7 means Sunday everywhere.
- Local scheduling calendar is Asia/Manila. UTC timestamps are stored as UTC-naive SQL DateTime values and serialized with a `Z`; UI displays them explicitly in Manila time.
- “Previous four completed weeks” means four **ended calendar weeks**, not only weeks whose chores are completed. For future target weeks, the window ends at the earlier of target Monday and the current local Monday. Current/future unfinished calendar weeks are excluded.
- Missing calendar weeks in the four-week window contribute zero points. The historical denominator includes only weeks whose Sunday is on/after the resident’s local joining date. The week of joining counts; weeks wholly before joining do not. Residents cannot receive chores due before joining.
- All-time cumulative includes all recorded assignments, including planned future weeks. The all-time average denominator uses **recorded scheduling weeks** since joining, including recorded weeks with zero work for that resident. It does not invent scheduling records since registration. No eligible weeks returns null and the UI labels it accordingly.
- Four-week statistics use the same ended-calendar window relative to the selected week; all-time statistics are not cut off by the selected week.
- Full float precision is retained internally; only display is rounded to two decimals.
- Scores use active residents’ current ratings. A single active rating suffices; zero ratings on any active chore blocks generation before creating a week or assignments.
- Greedy ordering is descending score then chore ID. Choice is historical average plus current actual-responsibility points, then fewest current responsible chores, then resident ID. Retry accounts for existing assignments and accepted transfers. It fills missing chores only.
- API generation permits the current or upcoming week; historical generation is reserved for the deterministic seed/service fixture. Completion and request resolution remain possible for past incomplete chores.

## Responsibility, transactions and reporting

Accepted delegation changes responsibility only through its delegation record; assignment.resident_id remains the original owner. Pending requests do not transfer points. Acceptance rechecks current availability and active status. Accepted requests cannot be cancelled, rejected, or redelegated. Rejected/cancelled history is preserved.

Completing while a request is pending automatically cancels that pending request in the same transaction. A late acceptance then fails. This prevents transferring an already-completed chore.

SQLite mutations acquire `BEGIN IMMEDIATE` before authorization/state reads and commit once; concurrent generation and acceptance/completion tests exercise this behavior. The partial unique index remains a final database guard against multiple live requests. PostgreSQL would require explicit row/advisory locking in place of this SQLite transaction strategy before multi-process production use.

Reporting uses a tested SQL outer join that resolves only accepted delegation to one responsible resident per assignment, then zero-fills active residents and calculates the three distinct metrics. This is suitable for a small single dorm; very large deployments should move aggregation into grouped SQL and add pagination.

## Identity and security

Passwords use Argon2id hashes with random salts. Username normalization is lowercase. Signup accepts name, username and 8–128-character password; password confirmation is a UI-only check. Extra payload fields are rejected. Session cookies are HttpOnly, SameSite=Strict and signed, with a one-day expiry. A per-session CSRF token is required for authenticated writes, and foreign Origin requests are rejected. Authentication bodies require JSON. Error responses omit credential values. The local server binds to loopback by default.

A random server-start secret is used if SECRET_KEY is not supplied, invalidating sessions on restart. A stable deployment must supply a strong shared secret. Signed-cookie logout removes the browser cookie; there is no server-side token revocation table. Public internet deployment would additionally require HTTPS, secure cookies, login rate limiting, recovery/account lifecycle policies and operational monitoring. These are not claimed as implemented production hosting features.

The login profile picker reveals safe display names/usernames as specified. It never authenticates by selection. Dashboard browsing uses an authenticated directory containing only IDs/names. Shared status excludes passwords, personal settings, availability records and private delegation reasons. Requests are filtered to the original assignee or target substitute. All writes resolve identity server-side.

## UI decisions

Desktop presentation starts at **1024 CSS pixels**. Below that threshold the same details-open boolean drives a mobile bottom sheet. The selected resident, week, details visibility and authenticated identity remain separate client state variables. No avatar/carousel/viewport fields are persisted in the database.

Original artwork is mapped deterministically by `(resident_id - 1) % 4`, providing four consistent character variants and a fallback for every new resident. The artwork intentionally uses a simpler original pixel grid than the detailed concept illustrations; no proprietary sprites or copied mockup art are bundled as application assets. Artwork source and provenance are in `scripts/create_assets.py` and `app/static/assets/LICENSE.md`.

Mobile swipes use the character region and a dominant horizontal-axis threshold. Vertical sheet dragging is restricted to its handle; content scroll remains native. Arrow and expand/collapse controls provide alternatives. Desktop uses clicks/arrows/focused keyboard browsing with paired non-modal panels. Closing via keyboard restores focus to the selected character. Reduced-motion preferences remove transitions.

Asynchronous view loads carry a sequence number. Only the latest request replaces the rendered avatar, identity and status together. Existing content remains visible during a resident switch with a loading notice; errors retain the prior coherent view. Forms preserve safe text on errors and clear password values. Critical actions use confirmation dialogs; chore retirement uses a browser-native confirmation.

Onboarding completion is derived from availability and rating records; there is no extra flag/table. All-unavailable schedules are valid. Rating all chores is recommended but optional. My Profile includes Resume setup; the own dashboard prompts for missing availability/ratings. Refreshing midway through onboarding can resume through those controls.

Rules are static, read-only placeholders labeled “Rules pending approval.” No actual hours, penalties or policies were invented.

## Limits

- Local single-server classroom application; no public hosting or PostgreSQL validation.
- Self-reported completion; no quality verification, audit of physical work, email, SMS, calendar or password recovery.
- Original SVG artwork follows the supplied palette, room staging and character silhouette direction, but is not a pixel-for-pixel replica of the mockups.
- Browser tests cover headless Chromium desktop and touch emulation; physical devices, Safari, Firefox and assistive-technology audits are not claimed.
- No time/XP/productivity scores, multi-dorm/room model, detailed timetable or admin role.

## Verification record

Automated pytest result: 41 passed on 2026-11-22. Isolated headless Chromium walkthrough: 12 scenario groups passed on 2026-11-22. Exact command lines, categories and limits are in TEST_RESULTS.md. Visual screenshots are saved under artifacts/. `AUDIT_RESULTS.md` records the requirements audit, changes made and remaining limits.
