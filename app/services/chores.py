from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from app.services.errors import DomainError
from sqlalchemy import select, func, text
from app.models import Resident, Chore, ChoreRating, Week, Availability, Assignment, Delegation, utcnow

MANILA = ZoneInfo('Asia/Manila')

def local_date(value):
    return value.replace(tzinfo=timezone.utc).astimezone(MANILA).date()

def monday(day):
    return day - timedelta(days=day.weekday())

def validate_week(start):
    if start.weekday() != 0:
        raise DomainError(422, 'Week start must be a Monday (Asia/Manila).')
    return start + timedelta(days=6)

def require(db, model, key):
    obj = db.get(model, key)
    if obj is None:
        raise DomainError(404, f'{model.__name__} not found.')
    return obj

def write_lock(db):
    # Obtain the SQLite write reservation before reading mutable business state.
    # Routes call this before any other database operation, including authentication.
    if db.bind.dialect.name == 'sqlite':
        db.execute(text('BEGIN IMMEDIATE'))
    elif db.bind.dialect.name == 'postgresql':
        # Match SQLite's serialized writes across all deployed app instances.
        # The lock is released automatically on commit or rollback.
        db.execute(text('SELECT pg_advisory_xact_lock(1872026)'))

def scores(db):
    rows = db.execute(select(ChoreRating.chore_id, func.avg(ChoreRating.intensity_rating), func.count()).join(Resident).where(Resident.is_active.is_(True)).group_by(ChoreRating.chore_id))
    return {cid: (float(avg), count) for cid, avg, count in rows}

def responsible(db, assignment):
    accepted = db.scalar(select(Delegation).where(Delegation.assignment_id == assignment.assignment_id, Delegation.status == 'accepted'))
    return accepted.substitute_resident_id if accepted else assignment.resident_id

def eligible(db, resident_id, due_date):
    """A resident can take a chore only if active, already joined, and available."""
    resident = db.get(Resident, resident_id)
    if resident is None or not resident.is_active:
        return False
    if local_date(resident.joined_at) > due_date:
        return False

    available = db.scalar(
        select(Availability.is_available).where(
            Availability.resident_id == resident_id,
            Availability.weekday == due_date.isoweekday(),
        )
    )
    return bool(available)


def assignment_rows(db, start):
    """Build the weekly schedule displayed by the browser."""
    week = db.scalar(select(Week).where(Week.start_date == start))
    if not week:
        return []

    assignments = db.scalars(
        select(Assignment)
        .where(Assignment.week_id == week.week_id)
        .order_by(Assignment.due_date, Assignment.assignment_id)
    )
    residents = list(db.scalars(select(Resident).order_by(Resident.resident_id)))
    rows = []
    for assignment in assignments:
        responsible_id = responsible(db, assignment)
        chore = db.get(Chore, assignment.chore_id)
        original_resident = db.get(Resident, assignment.resident_id)
        current_resident = db.get(Resident, responsible_id)

        substitutes = []
        for resident in residents:
            if resident.resident_id == assignment.resident_id:
                continue
            if eligible(db, resident.resident_id, assignment.due_date):
                substitutes.append({
                    'resident_id': resident.resident_id,
                    'name': resident.name,
                })

        rows.append({
            'assignment_id': assignment.assignment_id,
            'chore_id': assignment.chore_id,
            'chore': chore.name,
            'resident_id': assignment.resident_id,
            'original': original_resident.name,
            'responsible_id': responsible_id,
            'responsible': current_resident.name,
            'due_date': assignment.due_date,
            'workload_points': assignment.workload_points,
            'status': assignment.status,
            'completed_at': assignment.completed_at,
            'rationale': assignment.rationale,
            'eligible_substitutes': substitutes,
        })
    return rows


def weekly_totals(db, start):
    result = {r.resident_id: dict(resident_id=r.resident_id, name=r.name, original=0.0, actual=0.0, completed=0.0) for r in db.scalars(select(Resident).order_by(Resident.resident_id))}
    week = db.scalar(select(Week).where(Week.start_date == start))
    if week:
        for a in db.scalars(select(Assignment).where(Assignment.week_id == week.week_id)):
            result[a.resident_id]['original'] += a.workload_points
            credited = result[responsible(db, a)]
            credited['actual'] += a.workload_points
            if a.status == 'completed':
                credited['completed'] += a.workload_points
    return result

def history(db, target, resident, as_of=None):
    # Previous four calendar weeks, ended both before target and before today.
    cutoff = min(target, monday(as_of or datetime.now(MANILA).date()))
    weeks = [cutoff - timedelta(weeks=i) for i in range(1, 5)]
    weeks = [w for w in weeks if w + timedelta(days=6) >= local_date(resident.joined_at)]
    total = sum(weekly_totals(db, w)[resident.resident_id]['actual'] for w in weeks)
    return total, total / len(weeks) if weeks else 0.0

def generate(db, start, allow_past=False, as_of=None):
    """Assign missing chores, giving harder chores to the least-loaded residents."""
    week_end = validate_week(start)
    if not allow_past and start < monday(datetime.now(MANILA).date()):
        raise DomainError(422, 'Generate the current or an upcoming week; historical weeks are read-only for generation.')
    # 1. Check that every active chore has a difficulty rating.
    chores = list(db.scalars(select(Chore).where(Chore.is_active.is_(True))))
    chore_scores = scores(db)
    unrated = [chore.name for chore in chores if chore.chore_id not in chore_scores]
    if unrated:
        raise DomainError(409, 'Generation blocked: no active-resident ratings for ' + ', '.join(unrated))
    # 2. Find or create the week, preserving its existing assignments.
    week = db.scalar(select(Week).where(Week.start_date == start))
    if not week:
        week = Week(start_date=start, end_date=week_end)
        db.add(week)
        db.flush()
    existing = list(db.scalars(select(Assignment).where(Assignment.week_id == week.week_id)))
    assigned_chore_ids = {assignment.chore_id for assignment in existing}
    # 3. Start with each resident's recent average and this week's work.
    residents = list(db.scalars(select(Resident).where(Resident.is_active.is_(True))))
    historical_averages = {resident.resident_id: history(db, start, resident, as_of)[1] for resident in residents}
    planned_points = {resident.resident_id: 0.0 for resident in residents}
    chore_counts = {resident.resident_id: 0 for resident in residents}
    for assignment in existing:
        resident_id = responsible(db, assignment)
        planned_points[resident_id] = planned_points.get(resident_id, 0) + assignment.workload_points
        chore_counts[resident_id] = chore_counts.get(resident_id, 0) + 1
    # 4. Assign the hardest chores first. Skip days when nobody is available.
    warnings = []
    for chore in sorted(chores, key=lambda chore: (-chore_scores[chore.chore_id][0], chore.chore_id)):
        if chore.chore_id in assigned_chore_ids:
            continue
        due_date = start + timedelta(days=chore.due_weekday - 1)
        candidates = [resident.resident_id for resident in residents if eligible(db, resident.resident_id, due_date)]
        if not candidates:
            warnings.append(f'{chore.name}: no active resident available on {due_date:%A}. Update recurring availability and generate missing chores.')
            continue
        def assignment_priority(resident_id):
            # Compare workload first, then chore count, then ID for a stable tie-break.
            return (
                historical_averages[resident_id] + planned_points[resident_id],
                chore_counts[resident_id],
                resident_id,
            )

        resident_id = min(candidates, key=assignment_priority)
        chore_points = chore_scores[chore.chore_id][0]
        rationale = (
            f'Score {chore_points:.2f}; explicitly available {due_date:%A}. '
            f'Historical average {historical_averages[resident_id]:.2f} '
            f'+ planned {planned_points[resident_id]:.2f} '
            f'= burden {historical_averages[resident_id]+planned_points[resident_id]:.2f}. '
            f'Lowest burden among {len(candidates)} eligible residents; '
            f'ties use fewest target-week chores ({chore_counts[resident_id]}), '
            f'then resident ID ({resident_id}).'
        )
        assignment = Assignment(
            resident_id=resident_id,
            chore_id=chore.chore_id,
            week_id=week.week_id,
            due_date=due_date,
            workload_points=chore_points,
            rationale=rationale,
        )
        db.add(assignment)
        planned_points[resident_id] += chore_points
        chore_counts[resident_id] += 1
    db.flush()
    return dict(assignments=assignment_rows(db, start), warnings=warnings)

def complete(db, aid, actor):
    a = require(db, Assignment, aid)
    if responsible(db, a) != actor:
        raise DomainError(403, 'Only the current responsible resident may complete this chore.')
    if a.status != 'completed':
        a.status, a.completed_at = 'completed', utcnow()
        for d in db.scalars(select(Delegation).where(Delegation.assignment_id == aid, Delegation.status == 'pending')):
            d.status = 'cancelled'
    db.flush()
    return {'message': 'Chore completed.'}

def request_delegation(db, aid, actor, substitute, reason):
    a = require(db, Assignment, aid)
    if a.resident_id != actor:
        raise DomainError(403, 'Only the original assignee may request delegation.')
    if a.status == 'completed':
        raise DomainError(409, 'Completed chores cannot be delegated.')
    if db.scalar(select(Delegation).where(Delegation.assignment_id == aid, Delegation.status.in_(['pending', 'accepted']))):
        raise DomainError(409, 'A pending or accepted delegation already exists. Accepted delegations are final.')
    if substitute == actor or not eligible(db, substitute, a.due_date):
        raise DomainError(422, 'Choose another active resident available on the due weekday.')
    d = Delegation(assignment_id=aid, substitute_resident_id=substitute, reason=reason.strip())
    db.add(d)
    db.flush()
    return {'delegation_id': d.delegation_id, 'message': 'Delegation requested; responsibility stays with you until acceptance.'}

def respond(db, did, actor, action):
    d = require(db, Delegation, did)
    a = require(db, Assignment, d.assignment_id)
    if d.status != 'pending':
        raise DomainError(409, 'Only pending requests can be changed.')
    owner = a.resident_id if action == 'cancelled' else d.substitute_resident_id
    if actor != owner:
        raise DomainError(403, 'This response is not yours to make.')
    if action == 'accepted' and (a.status == 'completed' or not eligible(db, actor, a.due_date)):
        raise DomainError(409, 'Assignment completed or substitute is no longer eligible.')
    d.status = action
    db.flush()
    return {'message': f'Delegation {action}.'}

def statistics(db, start):
    validate_week(start)
    weekly = weekly_totals(db, start)
    residents = list(db.scalars(select(Resident).order_by(Resident.resident_id)))
    # All-time cumulative includes every recorded week, including planned work.
    weeks = list(db.scalars(select(Week).order_by(Week.start_date)))
    totals = {r.resident_id: dict(original=0.0, actual=0.0, completed=0.0) for r in residents}
    for w in weeks:
        for rid, vals in weekly_totals(db, w.start_date).items():
            for metric in totals[rid]:
                totals[rid][metric] += vals[metric]
    rows = []
    first = weeks[0].start_date if weeks else start
    average_end = max(start, weeks[-1].start_date) if weeks else start
    for r in residents:
        begin = max(first, monday(local_date(r.joined_at)))
        n = max(0, (average_end-begin).days // 7 + 1)
        four_sum, hist_avg = history(db, start, r)
        rows.append({**weekly[r.resident_id], 'cumulative': totals[r.resident_id], 'average': totals[r.resident_id]['actual'] / n if n else 0, 'eligible_weeks': n, 'four_week_sum': four_sum, 'historical_average': hist_avg})
    chart = [{'week': start-timedelta(weeks=i), 'residents': list(weekly_totals(db, start-timedelta(weeks=i)).values())} for i in reversed(range(4))]
    return {'week': start, 'average_through': average_end, 'residents': rows, 'chart': chart}
