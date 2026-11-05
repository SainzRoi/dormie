"""Fixed, repeatable classroom fixture. Run after alembic upgrade head."""
import argparse
from datetime import date, datetime, timedelta, timezone
from sqlalchemy import select
from app.database import SessionLocal
from app.models import Resident, Chore, ChoreRating, Availability, Assignment, Delegation
from app.security import hasher
from app.services.chores import generate, complete, request_delegation, respond, eligible, write_lock

DEMO_WEEK = date(2026, 11, 9)
DEMO_PASSWORD = 'DormDemo2026!'

def seed(db):
    names = ['Alex', 'Bea', 'Carlo', 'Dana']
    residents = []
    for name in names:
        r = db.scalar(select(Resident).where(Resident.username == name.lower()))
        if not r:
            r = Resident(name=name, username=name.lower(), password_hash=hasher.hash(DEMO_PASSWORD), joined_at=datetime(2026, 10, 1, tzinfo=timezone.utc))
            db.add(r)
            db.flush()
        residents.append(r)
    available = [{1, 2, 4}, {2, 4, 6}, {1, 4, 6}, {1, 2, 6, 7}]
    for r, days in zip(residents, available):
        for day in range(1, 8):
            if not db.scalar(select(Availability).where(Availability.resident_id == r.resident_id, Availability.weekday == day)):
                db.add(Availability(resident_id=r.resident_id, weekday=day, is_available=day in days))
    fixtures = [('Sweep floor', 1, [2,2,3,1]), ('Wash dishes', 2, [3,3,2,4]), ('Clean bathroom', 4, [5,4,5,4]), ('Mop floor', 6, [3,4,3,4])]
    for name, day, ratings in fixtures:
        c = db.scalar(select(Chore).where(Chore.name == name))
        if not c:
            c = Chore(name=name, description=f'{name} in the shared dormitory spaces.', due_weekday=day)
            db.add(c)
            db.flush()
        for r, rating in zip(residents, ratings):
            if not db.scalar(select(ChoreRating).where(ChoreRating.chore_id == c.chore_id, ChoreRating.resident_id == r.resident_id)):
                db.add(ChoreRating(resident_id=r.resident_id, chore_id=c.chore_id, intensity_rating=rating))
    db.flush()
    # Historical data is fixed, including completion timestamps.
    for i in (4, 3, 2, 1):
        start = DEMO_WEEK - timedelta(weeks=i)
        result = generate(db, start, allow_past=True, as_of=DEMO_WEEK)
        for row in result['assignments']:
            a = db.get(Assignment, row['assignment_id'])
            if a.status != 'completed':
                a.status = 'completed'
                a.completed_at = datetime.combine(a.due_date, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=10)
        db.flush()
    generate(db, DEMO_WEEK, allow_past=True, as_of=DEMO_WEEK)

def demo_delegation(db):
    from app.models import Week
    week = db.scalar(select(Week).where(Week.start_date == DEMO_WEEK))
    if not week:
        raise RuntimeError('Run python -m app.seed first.')
    assignments = list(db.scalars(select(Assignment).where(Assignment.week_id == week.week_id).order_by(Assignment.assignment_id)))
    if any(db.scalar(select(Delegation).where(Delegation.assignment_id == a.assignment_id, Delegation.reason == 'Classroom demo: unexpected study group.')) for a in assignments):
        return
    for a in assignments:
        if a.status == 'completed' or db.scalar(select(Delegation).where(Delegation.assignment_id == a.assignment_id, Delegation.status.in_(['pending', 'accepted']))):
            continue
        for r in db.scalars(select(Resident).order_by(Resident.resident_id)):
            if r.resident_id != a.resident_id and eligible(db, r.resident_id, a.due_date):
                result = request_delegation(db, a.assignment_id, a.resident_id, r.resident_id, 'Classroom demo: unexpected study group.')
                respond(db, result['delegation_id'], r.resident_id, 'accepted')
                return
    raise RuntimeError('No eligible incomplete demo assignment remains.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--delegation', action='store_true', help='Add one accepted demo delegation after seeding.')
    args = parser.parse_args()
    with SessionLocal() as db:
        write_lock(db)
        if args.delegation:
            demo_delegation(db)
        else:
            seed(db)
        db.commit()
    print('Demo ready: November 9–15, 2026. Users: alex, bea, carlo, dana. Password: DormDemo2026!')
