# Dormie — Codex improvement prompts

Place `06 - UI Polish and Quality Assurance.md` in the existing Dormie repository beside Parts 1–5. Keep the current source, existing handoff, audit/test results and visual references. These prompts are designed for incremental improvements, not a fresh implementation. Choose the master prompt or run one task prompt at a time; do not run both approaches concurrently on the same working tree.

## Master prompt — review then implement the selected improvement phases

```text
Act as a senior frontend engineer, UI/UX designer, accessibility specialist and QA engineer reviewing the existing Dormie project. This is an incremental improvement task, not a rebuild.

Read AI_HANDOFF.md, the latest five numbered specifications, 06 - UI Polish and Quality Assurance.md, DECISIONS.md, AUDIT_RESULTS.md, TEST_RESULTS.md and README.md. Inspect the source files, mobile/desktop references and current rendered screenshots. Verify actual paths and repository status rather than assuming the handoff is current. Respect existing uncommitted changes and any approved cloud migration work.

Begin by running the existing available regression tests and comparing current rendered pages against their reference images. Supply a concise prioritized plan for P6-01 through P6-06 with concrete issues, affected paths, expected outcomes, dependencies and acceptance checks. Distinguish verified gaps from planned enhancements. Identify missing artwork, policy sources, browser engines or physical devices before promising delivery. Wait for my selection before implementation, as required by the existing handoff.

After I select phases, implement the full selected work incrementally. Prioritize visual fidelity and original character/environment assets; then transitions, cross-browser checks and accessibility. Do not block unrelated work on missing approved dorm policies. Use the acceptance criteria in Part 6.

Preserve the current FastAPI/Jinja2/vanilla JS/CSS architecture unless the repository already has an approved revision; preserve seven entity roles, security boundaries, the deterministic allocation algorithm, historical workload snapshots, recurring weekday availability, delegation lifecycle, database-derived statistics and responsive workflows. Browsing another resident never changes session identity or permits mutation. Do not introduce XP scoring, class timetable ingestion, photo verification, new admin features or unapproved data models.

Match the game-inspired aesthetic without using entire UI screenshots as functional screens. Improve original local artwork and component consistency. Keep mobile swipe and draggable status panel and desktop coverflow with click-to-open left and right panels. Provide non-gesture controls, keyboard navigation and reduced-motion support.

Inspect rendered before/after screenshots at 1440x900 and 390x844, plus narrow and breakpoint viewports. Run existing and added tests, including supported cross-browser and accessibility checks. Clearly distinguish Chromium, Firefox, WebKit emulation, real Safari and real devices. Do not claim tests as passed unless executed. Keep rules pending approval unless approved content is supplied.

Deliver targeted code/assets, regression tests, ART_ASSETS.md, UI_POLISH_REPORT.md, QA_MATRIX.md and updated TEST_RESULTS.md, DECISIONS.md, AI_HANDOFF.md and README.md as applicable. Record all unresolved limitations. Do not deploy, create paid resources, expose secrets, change cloud architecture or use live resident data without my approval. Stop for scope decisions, not for routine implementation steps once a phase is approved.
```

## Prompt 1 — P6-01: Visual fidelity

```text
Implement P6-01 from 06 - UI Polish and Quality Assurance.md for the existing Dormie application. This prompt authorizes P6-01 only. First review AI_HANDOFF.md, Part 4, other relevant specifications, current UI code, references and actual rendered screenshots. Run a baseline regression check and report a concise evidence-based comparison. Then improve the existing responsive interface, not a separate mockup.

Match the gender-neutral pixel-art dorm simulation aesthetic: cream/olive/walnut palette, crisp room artwork, readable live HTML text, consistent cards and clear states. Improve the welcome screen, mobile collapsed/expanded dashboard, desktop closed/open coverflow dashboard, onboarding, ratings, availability, weekly assignments, chore details, delegations, statistics and rules. Prioritize the welcome and dashboard as visual anchors. Use semantic reusable components and retain functional controls. Do not embed whole reference screenshots as the UI.

Keep desktop character click opening two contextual side panels with the resident centered, and mobile swipe/drag with accessible alternatives. Keep selected resident/week state across resize. Preserve all account boundaries and database-backed metrics. Coordinate with P6-02 if assets are incomplete; do not invent a new avatar system.

Validate at 1440x900, 390x844, 320px and the documented breakpoint. Capture before/after screenshots, add regression checks, run available tests and document exact changed files, design trade-offs and remaining visual gaps in UI_POLISH_REPORT.md. Do not change business logic, database or deployment configuration.
```

## Prompt 2 — P6-02: Original character and dorm artwork

```text
Implement P6-02 from 06 - UI Polish and Quality Assurance.md. This prompt authorizes the character and environment artwork phase. Inspect the existing asset directory, generator, avatar mapping, reference images, current welcome and responsive carousel screens. Reuse existing assets when suitable and improve them where needed.

Create a coherent gender-neutral original pixel-art asset family with consistent pixel grid, proportions, light direction and muted earthy palette. Make Alex, Bea, Carlo and Dana visually distinct, with a stable fallback for new residents using the existing public identity mapping. Improve the isometric dorm environments with separate portrait and landscape compositions, transparent full-body character sprites and suitable center-stage highlighting. Keep functional UI elements and text separate from illustrations. Maintain image sharpness, legibility and safe cropping across responsive states.

Use only original or appropriately licensed local assets. Maintain the existing source generator or record its replacement, and create ART_ASSETS.md with provenance, file dimensions, usage, fallback and regeneration instructions. Do not add tables, character customization persistence, external runtime assets or unapproved paid generation services. If an asset requires outside art creation, document exact requirements and do not misrepresent a placeholder as finished.

Integrate assets into the existing app, verify at 1440x900 and 390x844 with closed/open status states, capture screenshots, run relevant regressions and update UI_POLISH_REPORT.md. Preserve all functional workflows and current session identity behavior.
```

## Prompt 3 — P6-03: Motion and transitions

```text
Implement P6-03 from 06 - UI Polish and Quality Assurance.md after the visual layout and assets have stabilized. This prompt authorizes motion improvements only. Review the existing gesture/carousel logic and styles, then add short, consistent CSS transitions for horizontal resident browsing, desktop side panels and mobile bottom-sheet snapping. Keep the selected character centered on desktop and maintain full-body view in collapsed mobile state.

Use pointer intent handling, appropriate cancellation, reliable scroll/drag separation, safe state transitions and non-gesture controls. Preserve selected resident/week/open state across resizing. Prevent stale asynchronous profile data, duplicate API writes and input interference during rapid browsing. Respect prefers-reduced-motion: reduce, with equivalent immediate state changes and no decorative motion. No autoplay audio or mandatory animations.

Add regression cases for rapid navigation, canceled drags, open/close, resize, internal scrolling and keyboard/gesture alternatives. Verify the same behavior and data with motion disabled. Run available tests, capture actual evidence and record tuning choices, limitations and results in UI_POLISH_REPORT.md and TEST_RESULTS.md. Do not change assignment or authentication logic.
```

## Prompt 4 — P6-04: Cross-browser and device testing

```text
Implement P6-04 from 06 - UI Polish and Quality Assurance.md. Review TEST_RESULTS.md and scripts/browser_check.py, verify the recorded baseline, extend the existing browser harness to supported Chromium, Firefox and WebKit engines, and run isolated deterministic tests. Use a test database and do not mutate production data. If browser binaries, devices or permissions are unavailable, record those checks as blocked/not run.

Cover desktop 1440x900, mobile 390x844, narrow 320px, breakpoint resizing, touch emulation and reduced motion as supported. Verify authentication/setup resumption, ratings, availability, idempotent generation, read-only resident browsing, delegation outcomes, authorized completion, statistics, rules, errors, scrolling and keyboard controls. Check Safari/Firefox-specific layout or event issues where reproducible and fix in-scope defects without broad refactors.

Provide QA_MATRIX.md with engine/version, viewport, actual outcome, screenshot/evidence, command, defect and fix. Clearly distinguish browser automation from real devices; WebKit automation is not a real Safari result. Provide a manual checklist for groupmates using physical Android/Chrome, iPhone/Safari and available desktop browsers, including orientation, zoom, virtual keyboard and touch. Do not claim physical-device results without executing them. Run existing/new regressions and update TEST_RESULTS.md and AI_HANDOFF.md. Do not deploy publicly or create paid services without approval.
```

## Prompt 5 — P6-05: Dorm policy content

```text
Implement P6-05 from 06 - UI Polish and Quality Assurance.md. Inspect the existing static read-only Rules & Regulations page. I will provide the authoritative approved dorm policy text or its source; if it is absent, retain a visible pending-approval state and tell me exactly what content is needed. Do not invent quiet hours, visitor rules, restrictions, fines, disciplinary consequences or other official policies.

When approved content is available, reproduce its substance and wording accurately, organize it into accessible expandable categories where appropriate, and show source/effective date/version when provided. Keep reading easy at desktop and mobile widths. Preserve the original no-admin, no-policy-enforcement and seven-entity architecture. Render safely and avoid publishing personal information without permission.

Verify nav access, keyboard accordion behavior, mobile readability and pending/approved labels. Add a regression test where practical. Document the policy source, changed files, evidence and outstanding approvals in UI_POLISH_REPORT.md. Do not mark the content approved unless the source establishes that status.
```

## Prompt 6 — P6-06: Accessibility testing and remediation

```text
Implement P6-06 from 06 - UI Polish and Quality Assurance.md. Audit the existing rendered Dormie UI against WCAG 2.2 AA as a practical target, not a certification claim. Review current accessibility support before adding fixes. Run an automated scanner such as axe-core within the existing browser harness if available, then perform manual keyboard, focus, contrast, zoom/reflow and reduced-motion checks; run screen-reader checks on actual supported combinations only when available.

Prioritize welcome/auth, onboarding, resident carousel, mobile bottom sheet, desktop side panels, forms, dialogs, chores, delegations, charts/tables and rules accordion. Use semantic controls, labels, meaningful names, visible focus, appropriate dialogs and state announcements, non-gesture equivalents, readable contrast, status cues beyond color, usable targets and textual chart alternatives. Do not intercept global navigation keys during text editing; preserve native scroll and ensure focus is not obscured or trapped. Do not expose private data through accessibility labels or hidden UI.

Fix reproducible high-impact issues in the existing code; preserve design, responsive states, API security and workload behavior. Add accessibility regression checks, inspect at desktop/mobile widths, 320px reflow and 200% zoom, and record evidence in QA_MATRIX.md and UI_POLISH_REPORT.md. Report automated checks separately from human/assistive technology checks, with blocked checks and remaining limitations. Run regressions and update TEST_RESULTS.md. Do not claim full conformance from an automated scan alone.
```

## Final audit prompt — after selected phases and any approved deployment merge

```text
Audit the completed Dormie improvement phases against Part 6 and the latest Parts 1–5. Inspect the actual repository diff, report artifacts and rendered before/after screenshots. Re-run current available tests and browser checks on isolated data. Verify mobile swipe/bottom-sheet states, desktop click-to-open side panels, accessibility alternatives, authorization, delegation and workload accounting remain correct. Confirm no unapproved database or cloud changes, copied proprietary assets, fabricated official rules or untested pass claims exist.

Fix reproducible in-scope regressions. Update UI_POLISH_REPORT.md, QA_MATRIX.md, TEST_RESULTS.md, DECISIONS.md, README.md and AI_HANDOFF.md as applicable. Report status and evidence for every P6 item, including known limitations, missing approved policies, physical-device/browser gaps and any unresolved blockers. Distinguish what is implemented, actually tested, not run, blocked and still proposed. Do not deploy, provision paid services or change unrelated scope without approval.
```
