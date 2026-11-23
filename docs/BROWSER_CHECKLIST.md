# Repeatable manual browser checklist

Start with a fresh seeded demonstration database following README. Use Alex / Dormie2026!, and November 9, 2026 in the week picker unless testing current-week generation. Perform mutations only in a disposable demonstration database.

## Desktop — 1440 × 900

- [ ] Welcome art, START, and Resident login work; password is required even after selecting a profile.
- [ ] Login centers Alex with both panels closed and compact top navigation.
- [ ] Arrow and focused Left/Right keyboard controls browse without opening panels. Repeat keyboard presses still work.
- [ ] Click Bea: paired panels show Bea, character stays visible, and account remains Alex.
- [ ] No completion/delegation controls or private reasons appear in another resident’s shared status.
- [ ] Browse while open: both panels update together and keep the selected week.
- [ ] Close/Escape keeps selection; focus returns to selected character; Enter reopens it.
- [ ] Return to my status selects Alex without changing the session.

## Mobile — 390 × 844

- [ ] Full-body character and compact sheet are visible after login.
- [ ] Swipe left/right on character and tap arrows; identity/status change together.
- [ ] Drag handle up to expand and down to collapse; expansion state survives browsing.
- [ ] Expand/Collapse buttons provide the same actions without dragging.
- [ ] Expanded body scrolls without moving the sheet or changing resident.
- [ ] Portrait, arrows, menu and account controls remain reachable while expanded.
- [ ] Resize to 768, 900, 1024, 1440 pixels with panels open and closed: selection, week and visibility persist with no horizontal overflow.

## Workflows

- [ ] Register → recurring availability → ratings → setup confirmation → zero-workload home.
- [ ] All-unavailable schedule saves with a clear explanation; interrupted setup resumes from Profile.
- [ ] Invalid login, duplicate username, mismatched password, invalid input and network failure display readable recoverable errors.
- [ ] Save a rating; collective mean/count update. Historical assignment score/explanation stay frozen.
- [ ] Add/edit/retire a chore; retiring preserves history. Due-day changes after assignments are blocked with useful guidance.
- [ ] Generate a current/upcoming Monday. Repeat generation: no duplicates or reshuffling.
- [ ] Unrated active chore blocks generation by name. No eligible resident produces an unassigned warning and allows retry after availability changes.
- [ ] Complete only as responsible resident; confirmation and persisted timestamp update workload.
- [ ] Request substitute; pending retains original responsibility. Accept transfers responsibility only; reject/cancel retain history and allow a new request. No chains after acceptance.
- [ ] Switch accounts through logout/login; browsing alone never switches accounts.
- [ ] Check selected-week, previous-four-week, cumulative, average totals for all three metrics. Confirm zero-point residents appear and group totals count each assignment once.
- [ ] Rules accordions are read-only and explicitly pending approval.

## Edge states and accessibility

- [ ] Single active resident: arrows disabled; one centered sprite.
- [ ] No active chores/no assignments: useful empty states and no fabricated totals.
- [ ] Rapid resident/week changes never render a prior response under a new identity.
- [ ] Loading disables submit buttons; success appears only after server success; failed submission keeps non-password text.
- [ ] All controls work by keyboard with visible focus; dialog Escape and focus restoration work.
- [ ] Reduced-motion preference removes transitions.
- [ ] No uncaught browser JavaScript errors or horizontal clipping.

Executed automated browser scenarios and limitations are recorded separately in TEST_RESULTS.md. Unchecked boxes here are a reusable checklist, not a claim of failure or success.
