# Part 3: Core Functionality, Algorithms & API Services

## 1. Workload Points & Fairness Metrics

### Collective Chore Intensity Formula
Residents rate each chore from 1 to 5. For chore $c$:

$$\text{chore\_score}(c) = \frac{\sum \text{active\_resident\_ratings\_for\_}c}{\text{number\_of\_active\_resident\_ratings\_for\_}c}$$

- Use the numeric arithmetic mean as workload points (e.g., ratings `5, 4, 5, 4` produce **4.5 points**).
- Retain full floating-point precision internally; display to **2 decimal places** in the UI.
- Report the count of ratings alongside the mean.
- If a chore has zero ratings, it is ineligible for automatic generation until at least one rating exists.

### Three Differentiated Workload Metrics
1. **Originally Assigned Workload:** Sum of `ASSIGNMENT.workload_points` for tasks where the resident is the original assignee (`ASSIGNMENT.resident_id`), regardless of delegation.
2. **Actual Responsibility Workload:** For each assignment, credit points to the **accepted substitute** (`DELEGATION.substitute_resident_id` where `status = 'accepted'`), if one exists; otherwise credit to the original assignee. Never count an assignment twice. **This is the primary metric used by the assignment algorithm and resident-facing workload comparison.**
3. **Completed Workload:** Credit `workload_points` only for assignments with `status = 'completed'`, attributed to the same responsible resident as defined in *Actual Responsibility Workload*. Do not confuse acceptance of a delegation with task completion.

### Continuity & Rating Updates
- Rating changes affect **future** assignments only; historical `ASSIGNMENT.workload_points` remain frozen.
- When a new resident joins, include their ratings and availability going forward without revising historic scores or weeks. Keep historical comparisons meaningful for newcomers by using eligible weeks (weeks since `joined_at`) in averages.

---

## 2. Deterministic Fair Assignment Algorithm

Implement a **deterministic, explainable greedy allocator** triggered when a resident clicks **Generate assignments** for a given upcoming week (no external task scheduler required). Note in UI/docs that this is a transparent workload-balancing heuristic, not a mathematically guaranteed globally optimal schedule.

### Step-by-Step Execution
1. **Resolve Week:** Create or retrieve the Monday–Sunday `WEEK` record (using `Asia/Manila` local calendar).
2. **Validate Chores:** List active chores with `frequency = 'weekly'` and a valid collective score. If any active chore has zero ratings, **block generation** with a specific error identifying the unrated chore(s).
3. **Derive Due Dates:** For each chore, calculate the exact `due_date` from `WEEK.start_date` and `CHORE.due_weekday`.
4. **Filter Availability:** Find active residents who explicitly marked that `weekday` as `is_available = True`. (Missing rows = unavailable).
5. **Calculate Historical & Current Burden:**
   - Calculate each resident's credited **actual responsibility** points over the **previous four completed weeks** (or fewer eligible weeks for newer residents), plus currently planned points for the target week.
   - Formula:
     $$\text{Adjusted Workload Burden} = \text{Historical Average per Eligible Week} + \text{Current-Week Points}$$
   - Treat the target week's existing assignments accurately if generation is retried for missing chores.
6. **Greedy Allocation & Tie-Breaking:**
   - Order chores to be assigned by **descending workload score** (tie-break by ascending `chore_id`).
   - Assign each chore to the eligible resident with the **lowest adjusted workload burden**.
   - **Tie-breaker:** Fewest current-week chores, then ascending `resident_id`. Never rely on random choices.
7. **Handle Unassigned Chores:** If no eligible resident is available for a chore on its due weekday, do **not** allocate it to an unavailable resident. Return a clear **unassigned warning** for that chore so users can update availability and retry.
8. **Transaction & Idempotency:** Persist results in a database transaction. Re-running generation/refresh must not duplicate or reshuffle existing assignments for that week; show existing assignments and offer safe generation for missing chores only.
9. **Explainability Rationale:** Return and display a short rationale for every assignment: chore score, availability check, historical burden used, and tie-break basis (if applicable).

---

## 3. Delegation & Completion Rules

### Task Completion
- Only the **currently responsible resident** (original assignee if no accepted delegation exists, or the accepted substitute) may mark an assignment as `completed`.
- Sets `status = 'completed'` and records UTC timestamp in `completed_at`.

### Delegation Lifecycle
- **Request:** Only the original assignee may request a delegation on an incomplete assignment, providing a text `reason` and selecting an eligible substitute (must be active, not the original assignee, and available on the chore's `due_weekday`).
- **Concurrency:** Only one `pending` or `accepted` delegation may exist per assignment at any time.
- **Pending State:** Responsibility remains with the original assignee while `status = 'pending'`. The original assignee may **Cancel** (`status = 'cancelled'`) a pending request.
- **Resolution:** The target substitute may **Accept** (`status = 'accepted'`) or **Reject** (`status = 'rejected'`).
  - Upon **Accept**, actual responsibility and fairness accounting transfer to the substitute (`ASSIGNMENT.resident_id` remains untouched). Accepted delegations are final until task completion (no re-delegation chains).
  - Upon **Reject** or **Cancel**, the record is preserved in history, and the original assignee may submit a new delegation request.

---

## 4. API & Service Layer Architecture

Keep business logic in a dedicated service layer (`app/services`) so it is independently testable, and expose it via FastAPI routes (`app/api`):

- **Auth Service/Endpoints:** Resident signup, login, logout, password hashing, session/token protection, and fetching current resident profile.
- **Chore & Rating Service/Endpoints:** List/create/update common chores (authenticated residents may manage common chores in MVP), submit/update own 1–5 chore rating, calculate aggregate score and rating count.
- **Availability Service/Endpoints:** Read and update own recurring Monday–Sunday availability toggles.
- **Weekly Assignment Service/Endpoints:** List/get weekly periods, fetch weekly assignments with rationale and responsible resident resolution, trigger idempotent weekly assignment generation, mark eligible chore completed.
- **Delegation Service/Endpoints:** Create delegation request, list incoming/outgoing/historical delegations, accept/reject (substitute only), cancel (original assignee only).
- **Statistics Service/Endpoints:** Fetch personal and group workload statistics (weekly, 4-week sum, all-time cumulative, per-eligible-week average across all 3 workload metrics) with week filters.
- **Resident browsing/read model:** Provide an authenticated active-resident directory (safe ID and display name) and read-only selected-resident status for a selected week, reusing the assignment and statistics services. Include shared chore responsibilities, completion counts, all three workload metrics, and the required ranges. Return only shared status data for another resident; do not expose credentials, private delegation reasons, personal availability/settings, or another resident's private requests. Account-level actions and private delegation alerts use the authenticated resident, never the viewed resident. Desktop and mobile use the same data; neither carousel selection nor opening a panel mutates database records.
- **Security & Validation:** Validate all inputs server-side (Pydantic), use parameterized ORM queries, and strictly prevent unauthorized users from altering another resident's ratings, availability, completions, or delegations.
