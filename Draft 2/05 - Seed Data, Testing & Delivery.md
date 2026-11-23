# Part 5: Seed Data, Testing & Delivery Plan

## 1. Deterministic Seed & Demo Data

Provide a deterministic seed command and documented login credentials for four sample residents: **Alex, Bea, Carlo, and Dana**.

### Seed Chores & Ratings
Seed four weekly chores with the exact ratings below:

| Chore | Due Weekday | Ratings (Alex, Bea, Carlo, Dana) | Collective Mean |
| :--- | :--- | :---: | :---: |
| **Sweep floor** | Monday (`1`) | 2, 2, 3, 1 | **2.00** |
| **Wash dishes** | Tuesday (`2`) | 3, 3, 2, 4 | **3.00** |
| **Clean bathroom** | Thursday (`4`) | 5, 4, 5, 4 | **4.50** |
| **Mop floor** | Saturday (`6`) | 3, 4, 3, 4 | **3.50** |

### Seed Availability, Weeks & Delegations
- **Recurring Availability:** Seed distinct repeating weekday availabilities for Alex, Bea, Carlo, and Dana, ensuring enough eligible residents exist on Monday, Tuesday, Thursday, and Saturday.
- **Fixed Demo Dates:** Provide a fixed demo Monday–Sunday week—e.g., **November 9–15, 2026**—plus optional earlier completed weeks to demonstrate historical workload balancing over a 4-week window. **Never make example dates depend on the current system clock.**
- **Delegation Demo:** Seed a realistic delegation scenario (or provide an idempotent demo command) so presenters can immediately demonstrate original assignee vs. accepted substitute and the resulting shifts in workload statistics.

---

## 2. Required Automated Tests (`pytest`)

Write automated API/service integration tests using a temporary test database covering at minimum:

1. **Ratings Validation:** Valid `1..5` ratings, rejection of out-of-range ratings (`<1` or `>5`), and enforcement of one active rating per `(resident_id, chore_id)` pair.
2. **Scoring Math:** Correct arithmetic mean calculation (including decimal results like `4.5`), rating count reporting, and blocking generation when a chore has `0` ratings.
3. **Week & Due Date Math:** Monday `start_date` and Sunday `end_date` validation (6 days apart) and accurate `due_date` derivation per `due_weekday`.
4. **Recurring Availability:** Stored without a `week_id`, unique by `(resident_id, weekday)`, and missing weekday records treated strictly as unavailable.
5. **Availability Filtering:** Assignment generator excludes unavailable residents and returns an explicit unassigned warning if zero residents are available on a chore's due weekday.
6. **Deterministic Allocation:** Fair greedy allocation ordering chores by descending score, selecting the lowest adjusted burden, and deterministic tie-breaking, accurately reflecting historical workload.
7. **Idempotent Generation:** Re-running generation for the same week does not duplicate chores or overwrite/reshuffle existing assignments.
8. **Snapshot Immutability:** Updating a chore's rating does not retroactively alter `workload_points` on already-generated assignments.
9. **Delegation Mechanics:** Delegation preserves `ASSIGNMENT.resident_id`; a `pending` request keeps responsibility with the original assignee; an `accepted` request transfers responsibility to the substitute.
10. **Delegation Guards:** Rejects invalid substitutes (self-delegation, inactive, or unavailable on due weekday), rejects delegating already-completed assignments, and blocks duplicate active (`pending`/`accepted`) requests on the same assignment.
11. **Completion Authorization:** Marking a task `completed` is permitted **only** for the currently responsible resident (original assignee or accepted substitute).
12. **Statistics & Metrics:** Accurate weekly, 4-week, all-time cumulative, and per-eligible-week average point totals; includes zero-workload residents; credits delegated tasks without double counting; properly separates *Originally Assigned*, *Actual Responsibility*, and *Completed* metrics.
13. **Authorization & Security:** Unauthorized residents cannot alter another person's ratings, availability, completions, or delegation responses.

### Responsive Dashboard UI Acceptance Tests

Add browser-level tests (e.g., Playwright if available locally) or a documented repeatable manual browser checklist, in addition to the required pytest service tests. Verify:

1. Desktop at 1440 × 900: login as Alex; centered avatar, top navigation and closed panels. Click Bea; left and right panels open around Bea; data matches the selected week.
2. Arrow/keyboard browse with panels closed, then while open; both panels update together, viewed resident and week remain consistent, and session still belongs to Alex. Close/Escape retains the selection. Reopen via character click.
3. Mobile at 390 × 844: swipe left/right or tap arrows; drag status sheet up/down and use expand/collapse alternative. Ensure vertical scrolling and horizontal browsing do not interfere.
4. Resize between modes while details are open and closed; preserve selected resident, week and visibility. Check no overlap, clipping, or inaccessible controls at intermediate widths.
5. Browsing others is read-only in both modes; no private delegation reasons or settings leak, and server rejects attempted cross-resident mutations. Account switching requires authentication.
6. Loading, errors, zero chores, one resident, and rapid resident/week changes render correct data; stale responses never replace a new selection. Keyboard and reduced-motion controls work.

Include the desktop/mobile walkthrough in README and document results separately from automated service test results. Do not claim browser tests passed without executing them.

---

## 3. Implementation Order

1. Inspect the repository. If empty, initialize the project with the FastAPI + SQLAlchemy + Alembic + Jinja2 stack.
2. Implement ORM models, Alembic migrations, and database constraints for all seven entities.
3. Add authentication, deterministic seed data, and basic resident/chore CRUD.
4. Add chore ratings, recurring availability, and collective scoring queries.
5. Implement deterministic week generation and historical workload accounting.
6. Implement delegation and completion workflows with strict authorization checks.
7. Add statistics queries/views and dashboard visualizations.
8. Build and polish responsive frontend pages and status badges, including mobile draggable status sheet and desktop click-to-open two-panel carousel with top navigation (Part 4 D01–D05).
9. Implement and run the `pytest` suite; fix all failures.
10. Write `README.md`, `DECISIONS.md`, and the final classroom demo walkthrough.

---

## 4. Acceptance Criteria (Definition of Done)

- [ ] Application launches locally using documented commands in `README.md`.
- [ ] Database migrations create the seven related physical tables with keys and constraints.
- [ ] Seed command populates demonstrable residents (Alex, Bea, Carlo, Dana), chores, ratings, and availability.
- [ ] Users rate chores; system shows mean intensity and rating count.
- [ ] Users save recurring weekday availability without weekly re-entry.
- [ ] Monday–Sunday weeks and assignment due dates are validated and accurate.
- [ ] Weekly chore generation respects availability, workload history, and idempotency.
- [ ] Residents view all assignments and mark only their eligible tasks completed.
- [ ] Delegation request, acceptance, rejection, cancellation, and history work; original assignee remains recorded in `ASSIGNMENT.resident_id`.
- [ ] Dashboard and statistics page accurately report weekly, cumulative, average, assigned, actual-responsibility, and completed workload metrics.
- [ ] UI works cleanly on desktop and mobile with readable error states.
- [ ] Desktop carousel supports character click, previous/next and keyboard navigation; opens/closes two contextual side panels around the centered character with no required vertical drag.
- [ ] Mobile carousel supports swipe and arrow navigation; the compact bottom sheet expands/collapses with drag or toggle.
- [ ] Both modes preserve account authorization and display consistent database-derived resident status; responsive transitions and read-only browsing pass the UI acceptance checks above.
- [ ] Automated tests run and pass (`pytest`); `README.md` gives the exact test command and a live-demo walkthrough.
- [ ] `DECISIONS.md` records any reasonable assumptions and known MVP limitations.
