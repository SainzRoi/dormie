# Part 6: UI Polish, Artwork & Quality Assurance

**Project:** Dormie  
**Type:** Incremental improvement specification for the existing application  
**Baseline:** `AI_HANDOFF.md` (recorded November 22, 2026) and latest Parts 1–5  
**Status:** Proposed work; not implemented or validated by this document.

## 1. Objective and boundaries

Improve the existing Dormie application until its appearance, interaction quality, accessibility, and cross-device reliability match the intended responsive pixel-art simulation experience. Do not rebuild working features. This is an addendum to the latest five project specifications, not a replacement.

Before editing, inspect the current repository, `AI_HANDOFF.md`, Parts 1–5, `README.md`, `DECISIONS.md`, `AUDIT_RESULTS.md`, `TEST_RESULTS.md`, `references/mobile/`, `references/desktop/`, and the latest screenshots in `artifacts/`. Verify actual file paths and existing implementations. The handoff reports 41 passing pytest tests, 12 passing Chromium browser scenario groups, a clean Alembic check, and passing JS syntax validation; these are historical results, not new test results. Re-run the baseline and report any differences.

Preserve:

- One shared responsive app (existing FastAPI/Jinja2/vanilla JS/CSS architecture unless the current repository has already adopted an approved revision).
- Seven domain entities; no new tables for visuals, gestures, rules, or XP.
- Authentication, session identity, CSRF, authorization and delegation privacy boundaries.
- Recurring Monday–Sunday weekday availability, 1–5 intensity ratings, deterministic allocation, four-week eligible historical average, workload snapshots and idempotent assignment generation as specified in Parts 2–3.
- Original assignee history; accepted delegation transfers actual responsibility, pending delegation does not, and completion is restricted to the responsible resident.
- Originally assigned, actual responsibility and completed points as separate database-derived metrics; two decimal places for display, no conversion into XP.
- Mobile swipe and bottom sheet; desktop coverflow and click-to-open side panels. Browsing is read-only, never authentication or account switching.
- Static read-only rules, no admin role, no penalties engine, no class-hour scheduling, photo verification, persistent game rewards, or other unapproved scope additions.
- `Asia/Manila` display dates and existing UTC timestamp conventions.

**Cloud dependency:** The owner separately requested moving Dormie online through Firebase/Google. Do not decide or implement the database migration in this workstream. If the cloud migration is already in progress, protect its changes, use the current supported storage configuration, and coordinate through a separate branch or agreed merge order. Do not provision paid resources, deploy public builds, expose credentials, or use production data for tests without approval. Re-run regression checks after any merge.

## 2. Improvement roadmap

| ID | Area | Priority | Deliverable | Depends on |
|---|---|---|---|---|
| P6-01 | Visual fidelity | High | Responsive visual audit and refreshed UI system | Baseline audit; P6-02 asset direction |
| P6-02 | Character/environment art | High | Coherent original asset set and integration | Approved visual direction |
| P6-03 | Animations/transitions | Medium | Accessible interaction motion | P6-01/P6-02 stable layout |
| P6-04 | Cross-browser/physical-device testing | Medium | Browser matrix, results, device checklist | Run baseline early; final runs after UI work |
| P6-05 | Actual dorm rules | Medium | Approved read-only policy content or explicit pending state | Owner-supplied rules |
| P6-06 | Accessibility | Medium | Keyboard, screen reader, contrast and gesture audit | Start in P6-01; final audit after motion |

Recommended sequence: baseline and visual audit → agree on asset direction → implement artwork and UI together → motion → final accessibility and browser testing. Rules content may proceed independently when supplied. Keep changes small and testable. Proposed screen dimensions, color tokens and motion durations below are defaults, not rigid design approvals; respect current specs where they differ.

## 3. P6-01 — Visual fidelity to reference mockups (High)

**Observed baseline:** Handoff reports a working UI whose original artwork is simpler than the references. Do not assume other visual defects without comparing actual rendered screenshots.

**Likely files:** `app/static/style.css`, `app/static/app.js`, `app/templates/index.html`, shared asset files, browser checks. Inspect before altering.

### Design direction

- Gender-neutral retro pixel-art dorm simulation, inspired by classic character browsing and room-building games; original visual identity, no copied proprietary artwork or game UI assets.
- Earthy cream, olive, muted forest green, walnut, sand and charcoal. Suggested tokens: background `#FAF2E5`, surface `#F0E2C9`, accent `#58783D`, ink `#493426`, dark `#343832`. Validate contrast before settling colors; avoid forcing exact palette values when accessibility requires adjustments.
- Crisp pixel-art silhouettes, warm room environments, subtle textured framing, readable UI fonts, consistent spacing, rounded cards, clear hierarchy. Text and controls stay live HTML/CSS, not baked into images. Avoid a conventional admin-dashboard appearance on the home screen.
- Use one reusable visual system across welcome/auth, setup, dashboard, catalog/ratings, availability, assignments, chore details, delegations, statistics and rules.

### Screen requirements

**Welcome:** Full-scene illustration, Dormie wordmark, centered START button, upper-right resident icon for sign-up/identification. No ordinary promotional sections, sidebar or marketing navigation. Keep existing session-aware first-time/returning behavior. Decorative sound UI only when functional; default off.

**Mobile dashboard:** Portrait, centered full-body avatar when sheet collapsed; horizontal swipe and arrows; compact status panel with visible handle and button. Expanded sheet shows details, reduces character area without losing navigation, scrolls independently and preserves selected resident/week. Use clear `You`/viewing label and return-to-my-status action.

**Desktop dashboard:** Centered resident coverflow; neighboring avatars angled, scaled and muted but still recognizable and clickable. Selected avatar remains large. Use top navigation, not a persistent dashboard sidebar. Click a resident to open both side panels around the selected character. Left: identity and workload overview; right: chores, completion and all relevant workload metrics. No desktop drag-up requirement. Arrow navigation keeps detail visibility; character click opens details; close control/Escape closes them. Avoid card and panel overlap at intermediate widths.

**Other views:** Use the same palette and reusable forms/buttons/tables/status chips. Show real data, no fabricated tasks or statistics. Maintain clear empty, loading, error, success and confirmation states. Preserve all existing actions and validation.

### Acceptance criteria

- [ ] Compare screenshots of welcome, closed/open dashboard (own and another resident), onboarding, assignments, ratings, delegation, statistics, and rules against references.
- [ ] Render at 1440 × 900 and 390 × 844; also check 1023/1024 px breakpoint and a narrow 320 px viewport, unless current approved responsive breakpoint differs.
- [ ] No unintended horizontal page overflow, hidden controls, cropped labels, or obstructed forms; intentional internal scrollers remain usable.
- [ ] Selected character stays visually central on desktop with open panels and fully visible on closed mobile sheet.
- [ ] All important text is selectable and all controls remain semantic and interactive; no flattened UI screenshots.
- [ ] Record before/after screenshots and trade-offs. Visual reproduction means coherent fidelity, not an unsupported pixel-perfect claim.

## 4. P6-02 — Original character and dorm artwork (High)

**Observed baseline:** Artwork lives at `app/static/assets/`; handoff identifies `scripts/create_assets.py` as the source generator. Existing artwork is locally stored and original.

### Requirements

- Audit current assets, what generates them, sizes, licensing and existing avatar mapping. Preserve or revise the generator rather than hand-editing its outputs without documenting the source of truth.
- Create a consistent pixel grid, palette, light direction, perspective, proportions and outline rules. Keep the style gender-neutral and represent varied skin tones, hair and clothing respectfully. No stereotyped roles based on identity.
- Provide distinctive full-body avatars for demo residents Alex, Bea, Carlo and Dana, plus a reproducible fallback for new residents using existing public identity data. Do not create avatar persistence fields or customization mechanics unless separately approved.
- Produce separable illustrations: mobile portrait welcome scene, desktop landscape stage, dashboard dorm interior, avatar sprites with transparency, floor/ground highlight and optional decorative scenery. Use crop-safe compositions; ensure controls and selected characters stay legible.
- Furnish rooms with beds, desks, shared seating, shelving and cleaning supplies. Include enough room detail without reducing UI readability.
- Use SVG or optimized PNG/other appropriate local assets. For raster pixel artwork, use integer scaling or `image-rendering: pixelated` where suitable; avoid blurry resizing. For SVG, preserve consistent pixel-style edges. Specify intrinsic sizes/aspect ratios to avoid layout shifts.
- Store only original or properly licensed assets in the repo. Maintain `ART_ASSETS.md` with source/generator, license, dimensions, intended usage and fallback. Do not include reference screenshots as production UI backgrounds containing controls or text; separate decorative backgrounds are acceptable.
- Avoid runtime third-party image requests and paid art/AI services without approval. If richer artwork requires a human or image generation outside the repository, identify the missing asset and its exact dimensions rather than claiming the asset exists.

### Acceptance criteria

- [ ] Demo avatars are distinct, consistent and identifiable in closed and open responsive states.
- [ ] New resident fallback is stable and does not depend on an additional table or external service.
- [ ] Welcome imagery and dashboard stage respect safe areas across viewport orientations.
- [ ] Images load locally without missing paths; unnecessary downloads and layout shift minimized.
- [ ] Asset provenance and regeneration steps documented; all UI remains independently interactive.
- [ ] Before/after visuals demonstrate improved artwork, or explicit remaining differences are listed.

## 5. P6-03 — Animations and transitions (Medium)

**Likely files:** `app/static/style.css`, `app/static/app.js`, browser tests.

| Interaction | Suggested behavior | Default duration |
|---|---|---|
| Resident browsing | Neighbor avatars slide/scale into position; active resident highlight changes | 180–260 ms |
| Desktop status panels | Slide/fade from each side; keep center resident in view | 200–260 ms |
| Mobile status sheet | Drag follows pointer; snap to collapsed/expanded position on release | 180–260 ms after release |
| Navigation/dialogs | Brief fade or translate; no blocking animation | 120–180 ms |
| Feedback | Subtle button press and status transition after server confirms | 100–160 ms |

Durations are tuning defaults. Prefer CSS transforms/opacity rather than expensive layout animation; use pointer events for drag and handle `pointercancel`, short drags and resize. Use intent detection so horizontal gestures do not interfere with vertical panel scrolling. Do not intercept gestures over inputs or scrollable content unnecessarily. Keep equivalent controls for keyboard and touch.

- Maintain selected resident, week and details-open state during resizing. Do not show stale resident information during rapid switching; cancel outdated requests or ignore stale results via request state. Keep visible and accessible labels synchronized.
- Respect `prefers-reduced-motion: reduce`: disable decorative loops, perspective transitions, parallax and unnecessary movement; preserve functional state changes immediately or with minimal fades. No flashing or audio autoplay.
- Never delay an API action or mark a chore completed until the server confirms. Prevent duplicate writes from rapid clicks; allow recovery on failure.

### Acceptance criteria

- [ ] Rapid repeated browsing selects the correct final profile with no stale statistics or focus loss.
- [ ] Mobile sheet drag/cancel/snap and internal scrolling work; desktop click/close/Escape require no drag.
- [ ] Keyboard and pointer alternatives work with animations disabled.
- [ ] Reduced-motion mode produces the same final states and no continuous decorative motion.
- [ ] No animation-induced duplicate submissions or unauthorized controls. Record observations instead of claiming measured FPS without profiling.

## 6. P6-04 — Cross-browser and physical-device QA (Medium)

**Observed baseline:** Chromium automated tests only; touch was emulated. Physical-device, Safari and Firefox testing remain unverified. Do not equate WebKit automation with real Safari.

### Automated browser matrix

| Engine | Viewports | Checks |
|---|---|---|
| Chromium | 1440×900, 390×844, 320px width, breakpoint boundaries | Full flows, resizing, emulated touch, reduced motion |
| Firefox | Desktop and mobile-sized viewport | Full critical flows, layout, scroll, keyboard |
| WebKit | Desktop and mobile-sized viewport | Full critical flows, pointer/touch where supported, layout |

Use existing automation (`scripts/browser_check.py`) and extend with Playwright or an equivalent already in the repo. Install additional browser binaries only if allowed and report missing dependencies. Use isolated test databases and deterministic fixtures; do not seed or reset real data or use publicly exposed demo credentials.

### Manual device/browser matrix

- Real Android phone / Chrome: touch swiping, expanded sheet scrolling, orientation, keyboard and login.
- Real iPhone / Safari: touch, viewport safe areas, browser bars, virtual keyboard, scrolling, rotation.
- Desktop Chrome/Edge, Firefox and Safari when available: keyboard, mouse, resize, browser zoom, session behavior.
- Test interrupted network/slow responses on a safe staging deployment (if available) or controlled local conditions. Verify recovery without duplicate assignments or delegation writes.

Use the current campus/groupmate-accessible deployment only if approved and isolated from real resident records. Provide a checklist for groupmates to run on their own devices; record device model, OS/browser version, viewport, reproduction steps, expected/actual outcome, screenshot if permitted, and pass/fail/blocked/not run.

### Critical scenarios

1. Welcome → sign-up/login; interrupted setup resumes; logout and expired session behavior.
2. Rating validation, visible collective mean/count, unconfigured chore warning, recurring availability saved without weekly re-entry.
3. Generate assignments once and retry safely; due days, unassigned warning and rationale remain correct.
4. Browse other residents read-only, switch selected week, resize with open/closed details, verify authenticated identity remains unchanged.
5. Complete a responsible assignment; delegation request, accept/reject/cancel, no substitute, prohibited cross-account actions and duplicate request guard.
6. All three workload metrics, zero-point residents and filters; rules expand/collapse.
7. Slow/error/empty states, scroll and long names, reduced motion, keyboard and touch alternatives.

### Acceptance criteria

- [ ] Execute existing tests and supported browser checks; add regression cases for the new UI.
- [ ] Run `pytest -q`, `node --check app/static/app.js`, and existing browser check where applicable. Use `alembic check` when relevant and supported by the current data configuration; document why any command differs or is skipped.
- [ ] Report outcomes per actual engine, viewport and test scenario. Separate automation, emulation and physical devices; unperformed tests remain not run/blocked.
- [ ] Resolve reproducible high-severity defects before sign-off or document blockers and impact.

## 7. P6-05 — Actual dorm rules and regulations (Medium)

**Observed baseline:** Read-only static placeholders pending approval. No actual policy text has been supplied with this addendum.

### Content workflow

1. Locate existing static rules source. Request authoritative policy text from the dorm or owner if absent. Do not assume the dorm's rules or create official-looking fines, visitor restrictions, quiet hours or punishments.
2. Preserve approved wording, categories, conditions and dates. Identify source/owner, approval date/effective date and version when available. If unclear, ask for clarification; do not silently fill gaps.
3. Render expandable sections with descriptive headings and readable text: cleanliness/chores, shared spaces, waste, quiet hours, visitors, safety and conduct where present in the approved source. These are suggested organizing categories only.
4. If source policy is missing, keep the pending-approval label and clearly marked examples (or an explicit no-approved-policy empty state); do not present examples as enforceable rules.
5. Keep the page read-only for residents; no policy editing admin module, sanction system, acknowledgments tracking or new database entity. Sanitize content, use safe rendering and avoid publishing private contact details without permission.

### Acceptance criteria

- [ ] Actual wording matches supplied approved source, or the screen remains visibly marked pending approval.
- [ ] Rules are available from desktop top nav and mobile menu, with accessible expansion controls and readable text.
- [ ] No policy enforcement or invented regulatory facts; document the outstanding approval dependency.

## 8. P6-06 — Accessibility audit and remediation (Medium)

Target WCAG 2.2 AA as a design/test benchmark, not a certification claim. Audit existing implementation, including welcome, forms, carousel, dialogs, status panels, tables, statistics and policy accordion. Accessibility requirements apply during visual/motion work, not only at the end.

### Requirements

- Semantic HTML (`button`, `nav`, headings, forms, labels, tables); accessible names for icon-only controls; appropriate `aria-expanded`, `aria-controls`, live announcements for meaningful state/error changes; no misuse of ARIA to recreate native controls.
- Full keyboard access: predictable Tab order, visible focus not hidden by sheets, Enter/Space activation, Escape closes applicable panels/dialogs, focus returns to trigger where appropriate. Arrow/A/D shortcuts only when carousel context is active and never while typing or editing controls. No keyboard traps; modal focus handling only for true modal views.
- Carousel offers clear previous/next controls and resident position/name/current viewing state. Do not auto-advance residents. Mobile sheet includes expand/collapse controls so drag is not mandatory; alternatives for horizontal swipe and drag.
- Contrast target: normal text 4.5:1, large text 3:1, essential non-text controls and state boundaries 3:1 where WCAG applies. Do not rely solely on color to signal status; use labels, shapes or icons with text.
- Prefer touch targets around 44×44 CSS px for primary controls, keeping minimum target size/spacing requirements in mind. Provide usable spacing, zoom to 200%, reflow at 320 CSS px without lost information (allow appropriate data-table scroll), and no essential image-only text.
- Decorative art gets empty alt text or equivalent hidden semantics; meaningful images and charts get useful labels or data alternatives. Character names and chart/table values stay available to assistive technologies.
- Forms include explicit labels, useful errors, error association, safe input retention, password visibility controls where appropriate and password manager support. Do not force memorization puzzles or inaccessible login steps.
- Respect reduced motion and avoid auto-playing sound. Avoid exposing private data through hidden DOM or accessibility labels.

### Verification

- Run an automated accessibility scanner (e.g., axe-core in the existing browser harness) if available; supplement with manual checks. Automated tools do not prove WCAG compliance.
- Keyboard-only walkthrough of all critical actions, screen reader checks on actual supported combinations (e.g., NVDA/Firefox, VoiceOver/Safari, TalkBack/Chrome) where equipment exists, contrast measurement and zoom/reflow checks.
- For charts, confirm equivalent real-value tables/labels. Review errors/loading/status announcements for clarity and reasonable frequency.

### Acceptance criteria

- [ ] No known critical keyboard/accessibility blockers in tested core workflows; report remaining findings by severity and screen.
- [ ] Carousel and bottom sheet operate without gesture-only interactions.
- [ ] Focus remains visible and logically ordered; errors and success are understandable without color or motion.
- [ ] Contrast and reduced motion checked; manual and automated evidence clearly distinguished. Untested assistive technology combinations remain explicitly unverified.

## 9. Implementation and regression gates

1. Review current source and run baseline. Identify exact issues with screenshot/evidence, affected files, severity and checkable acceptance conditions. Do not confuse historical test counts with current results.
2. Select one phase or an explicitly approved combination. Record decisions, preserve current work, avoid unrelated formatting/refactor changes.
3. Implement targeted changes, add regression tests, inspect actual screenshots and interaction states at both reference viewports and near breakpoint. Test authorization when UI exposes a new action or display.
4. Run baseline and new checks; resolve regressions or record failures. Do not change business logic solely to fit visual references.
5. Update handoff and delivery docs after verified changes. Save before/after screenshots in `artifacts/ui-polish/` or the repository's established artifact directory; avoid screenshots with real private data.

## 10. Required outputs

- Modified source/assets and any new tests; `ART_ASSETS.md` with provenance and generation instructions.
- `UI_POLISH_REPORT.md`: each P6 item, changed paths, before/after evidence, design decisions, unresolved differences, and status (done/partial/blocked/not started).
- `QA_MATRIX.md`: automated/manual results including browser/version, viewport/device, command, scenario, impact and limitations.
- Updated `TEST_RESULTS.md`, `DECISIONS.md`, and `AI_HANDOFF.md` as applicable; README updates for new commands or asset regeneration.
- Reproducible screenshot and test capture instructions. Do not overwrite Parts 1–5 or approved cloud migration work without explicit justification and approval.

### Final definition of done

- All approved improvement items have evidence against their acceptance criteria; dependencies are explicitly marked.
- Core functionality remains intact; no data corruption, unauthorized access, rating/workload drift or responsive interaction regressions in tested scenarios.
- Visuals are coherent across mobile and desktop; responsive states retain their specific interaction patterns.
- Real policy content is not claimed without approved material; unperformed physical device, browser and assistive technology tests are not claimed as passes.
- No production deployment, paid service, or unrelated database replacement is performed as part of this addendum without approval.
