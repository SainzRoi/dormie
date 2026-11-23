"""Shared domain services. Call mutating services inside one write transaction."""
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from sqlalchemy import select, func, case, and_
from app.models import Resident, Chore, ChoreRating, Availability, Week, Assignment, Delegation, utcnow

MANILA = ZoneInfo('Asia/Manila')
METRICS = ('original', 'actual', 'completed')

def fail(message, status=400):
    raise HTTPException(status, message)

def require(db, model, key):
    obj = db.get(model, key)
    if obj is None:
        fail('Record not found.', 404)
    return obj

def today():
    return datetime.now(MANILA).date()

def monday(day):
    return day - timedelta(days=day.weekday())

def validate_week(start):
    if start.weekday() != 0:
        fail('Choose a Monday; each week ends on the following Sunday.', 422)
    return start + timedelta(days=6)

def joined_day(r):
    return r.joined_at.replace(tzinfo=timezone.utc).astimezone(MANILA).date()

def active_residents(db):
    return db.scalars(select(Resident).where(Resident.is_active.is_(True)).order_by(Resident.resident_id)).all()

def scores(db):
    return {cid: (float(total) / count, count) for cid, total, count in db.execute(select(ChoreRating.chore_id, func.sum(ChoreRating.intensity_rating), func.count()).join(Resident).where(Resident.is_active.is_(True)).group_by(ChoreRating.chore_id))}

def reporting_rows(db):
    """One SQL row per assignment. Accepted-only outer join prevents double counting."""
    responsible = func.coalesce(Delegation.substitute_resident_id, Assignment.resident_id)
    return db.execute(select(Assignment, Week, responsible.label('responsible')).join(Week).outerjoin(Delegation, and_(Delegation.assignment_id == Assignment.assignment_id, Delegation.status == 'accepted'))).all()

def totals(rows, rid, starts=None):
    result = dict.fromkeys(METRICS, 0.0)
    for a, w, responsible in rows:
        if starts is not None and w.start_date not in starts:
            continue
        if a.resident_id == rid:
            result['original'] += a.workload_points
        if responsible == rid:
            result['actual'] += a.workload_points
            if a.status == 'completed':
                result['completed'] += a.workload_points
    return result

def history_starts(start, as_of=None):
    # A completed week means a calendar period that has ended, not completed tasks.
    boundary = min(start, monday(as_of or today()))
    return [boundary - timedelta(weeks=n) for n in range(1, 5)]

def stats(db, start):
    validate_week(start)
    rows = reporting_rows(db)
    weeks = db.scalars(select(Week)).all()
    previous = history_starts(start)
    output = []
    for r in active_residents(db):
        eligible = {w.start_date for w in weeks if w.end_date >= joined_day(r)}
        cumulative = totals(rows, r.resident_id)
        # Average over recorded scheduling weeks, including zero-workload weeks.
        averages = {key: value / len(eligible) if eligible else None for key, value in totals(rows, r.resident_id, eligible).items()}
        weekly = totals(rows, r.resident_id, {start})
        own = [a for a, w, responsible in rows if w.start_date == start and responsible == r.resident_id]
        output.append({'resident_id': r.resident_id, 'name': r.name, 'weekly': weekly,
                       'four_week': totals(rows, r.resident_id, set(previous)), 'cumulative': cumulative,
                       'average': averages, 'eligible_weeks': len(eligible),
                       'count': len(own), 'completed_count': sum(a.status == 'completed' for a in own)})
    return output

def generate(db, start, as_of=None):
    end = validate_week(start)
    chores = db.scalars(select(Chore).where(Chore.is_active.is_(True))).all()
    means = scores(db)
    unrated = [c.name for c in chores if c.chore_id not in means]
    if unrated:
        fail('Generation blocked. Rate these unrated chores first: ' + ', '.join(unrated), 422)
    week = db.scalar(select(Week).where(Week.start_date == start))
    if not week:
        week = Week(start_date=start, end_date=end)
        db.add(week)
        db.flush()
    residents = active_residents(db)
    rows = reporting_rows(db)
    historical = {}
    planned = {}
    counts = {}
    previous = history_starts(start, as_of)
    for r in residents:
        eligible = {s for s in previous if s + timedelta(days=6) >= joined_day(r)}
        historical[r.resident_id] = totals(rows, r.resident_id, eligible)['actual'] / len(eligible) if eligible else 0.0
        planned[r.resident_id] = totals(rows, r.resident_id, {start})['actual']
        counts[r.resident_id] = sum(w.start_date == start and responsible == r.resident_id for a, w, responsible in rows)
    availability = {(a.resident_id, a.weekday) for a in db.scalars(select(Availability).where(Availability.is_available.is_(True)))}
    existing = {a.chore_id for a, w, responsible in rows if w.start_date == start}
    warnings, created = [], []
    for c in sorted(chores, key=lambda c: (-means[c.chore_id][0], c.chore_id)):
        if c.chore_id in existing:
            continue
        due = start + timedelta(days=c.due_weekday - 1)
        eligible = [r for r in residents if (r.resident_id, c.due_weekday) in availability and joined_day(r) <= due]
        if not eligible:
            warnings.append(f'{c.name}: no eligible resident on {due:%A}; remains unassigned.')
            continue
        key = lambda r: (historical[r.resident_id] + planned[r.resident_id], counts[r.resident_id], r.resident_id)
        winner = min(eligible, key=key)
        rid = winner.resident_id
        candidates = [{'resident_id': r.resident_id, 'burden': key(r)[0], 'current_chores': counts[r.resident_id]} for r in sorted(eligible, key=key)]
        rationale = {'score': means[c.chore_id][0], 'rating_count': means[c.chore_id][1], 'available_weekday': c.due_weekday,
                     'historical_average': historical[rid], 'planned_before': planned[rid], 'adjusted_burden': key(winner)[0],
                     'history_weeks': [s.isoformat() for s in previous], 'candidates': candidates,
                     'basis': 'Lowest historical average + planned points; ties use fewest current-week chores, then ascending resident ID.'}
        a = Assignment(resident_id=rid, chore_id=c.chore_id, week_id=week.week_id, due_date=due, workload_points=means[c.chore_id][0], rationale=rationale)
        db.add(a)
        db.flush()
        created.append(a.assignment_id)
        planned[rid] += a.workload_points
        counts[rid] += 1
    return {'created': created, 'existing_count': len(existing), 'warnings': warnings, 'week_id': week.week_id}

def live_delegation(db, aid):
    return db.scalar(select(Delegation).where(Delegation.assignment_id == aid, Delegation.status.in_(['pending', 'accepted'])))

def responsible_id(db, a):
    d = live_delegation(db, a.assignment_id)
    return d.substitute_resident_id if d and d.status == 'accepted' else a.resident_id

def eligible_substitutes(db, a):
    available = select(Availability.resident_id).where(Availability.weekday == a.due_date.isoweekday(), Availability.is_available.is_(True))
    return db.scalars(select(Resident).where(Resident.is_active.is_(True), Resident.resident_id != a.resident_id, Resident.resident_id.in_(available)).order_by(Resident.resident_id)).all()

def request_delegation(db, aid, actor, substitute, reason):
    a = require(db, Assignment, aid)
    if a.resident_id != actor:
        fail('Only the original assignee can request a substitute.', 403)
    if a.status == 'completed' or live_delegation(db, aid):
        fail('This assignment is completed or already has an active request.', 409)
    if substitute not in [r.resident_id for r in eligible_substitutes(db, a)]:
        fail('Substitute must be another active resident available on the due weekday.', 422)
    d = Delegation(assignment_id=aid, substitute_resident_id=substitute, reason=reason)
    db.add(d)
    db.flush()
    return d

def resolve_delegation(db, did, actor, action):
    d = require(db, Delegation, did)
    a = require(db, Assignment, d.assignment_id)
    expected = a.resident_id if action == 'cancelled' else d.substitute_resident_id
    if actor != expected:
        fail('You cannot respond to this request.', 403)
    if d.status != 'pending' or a.status == 'completed':
        fail('This request is no longer pending. Refresh to see its current state.', 409)
    if action == 'accepted' and actor not in [r.resident_id for r in eligible_substitutes(db, a)]:
        fail('You are no longer eligible on the due weekday. Update availability or reject.', 409)
    d.status = action
    db.flush()
    return d

def complete(db, aid, actor):
    a = require(db, Assignment, aid)
    if responsible_id(db, a) != actor:
        fail('Only the currently responsible resident may complete this chore.', 403)
    if a.status == 'completed':
        fail('This chore is already completed.', 409)
    d = live_delegation(db, aid)
    if d and d.status == 'pending':
        d.status = 'cancelled'
    a.status, a.completed_at = 'completed', utcnow()
    db.flush()
    return a

def assignment_data(db, a):
    c = require(db, Chore, a.chore_id)
    responsible = responsible_id(db, a)
    d = live_delegation(db, a.assignment_id)
    return {'assignment_id': a.assignment_id, 'chore_id': c.chore_id, 'name': c.name, 'description': c.description,
            'resident_id': a.resident_id, 'original_name': require(db, Resident, a.resident_id).name,
            'responsible_id': responsible, 'responsible_name': require(db, Resident, responsible).name,
            'due_date': a.due_date, 'workload_points': a.workload_points, 'status': a.status,
            'completed_at': a.completed_at.isoformat() + 'Z' if a.completed_at else None,
            'rationale': a.rationale, 'delegation_status': d.status if d else None}
