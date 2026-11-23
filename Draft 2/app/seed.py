"""Idempotent fixed classroom fixture. Never deletes or overwrites resident work."""
from datetime import date, datetime, timedelta
from sqlalchemy import select
from app.db import SessionLocal
from app.models import Resident, Chore, ChoreRating, Availability, Assignment, Delegation
from app.services.auth import hasher
from app.services.core import generate, request_delegation, resolve_delegation, complete

DEMO_WEEK = date(2026, 11, 9)

def seed(db):
    if db.scalar(select(Resident.resident_id).limit(1)):
        return False
    residents = []
    for name in ('Alex', 'Bea', 'Carlo', 'Dana'):
        r = Resident(name=name, username=name.lower(), password_hash=hasher.hash('Dormie2026!'), joined_at=datetime(2026, 10, 5))
        db.add(r)
        db.flush()
        residents.append(r)
    days = ({1, 3, 4, 6, 7}, {1, 2, 4, 5, 7}, {2, 3, 4, 6}, {1, 2, 5, 6, 7})
    for r, available in zip(residents, days):
        for day in range(1, 8):
            db.add(Availability(resident_id=r.resident_id, weekday=day, is_available=day in available))
    specs = [('Sweep floor', 1, [2, 2, 3, 1], 'Sweep the common room and hallways. Collect dust and return the broom.'),
             ('Wash dishes', 2, [3, 3, 2, 4], 'Wash shared dishes, rinse the sink and tidy the drying rack.'),
             ('Clean bathroom', 4, [5, 4, 5, 4], 'Clean the sink, scrub the toilet and wipe shared surfaces.'),
             ('Mop floor', 6, [3, 4, 3, 4], 'Mop shared floors and leave the mop clean and dry.')]
    for name, day, ratings, description in specs:
        c = Chore(name=name, due_weekday=day, description=description)
        db.add(c)
        db.flush()
        for r, rating in zip(residents, ratings):
            db.add(ChoreRating(resident_id=r.resident_id, chore_id=c.chore_id, intensity_rating=rating, rated_at=datetime(2026, 10, 5, 1)))
    db.flush()
    for offset in (4, 3, 2, 1):
        start = DEMO_WEEK - timedelta(weeks=offset)
        result = generate(db, start, as_of=start)
        for aid in result['created']:
            a = db.get(Assignment, aid)
            a.status = 'completed'
            a.completed_at = datetime.combine(a.due_date, datetime.min.time()) + timedelta(hours=9)
        db.flush()
    result = generate(db, DEMO_WEEK, as_of=DEMO_WEEK)
    tasks = [db.get(Assignment, aid) for aid in result['created']]
    # Seed an accepted transfer with the original owner retained, and a pending inbox.
    from app.services.core import eligible_substitutes
    for index, a in enumerate(tasks):
        substitutes = eligible_substitutes(db, a)
        if index < 2 and substitutes:
            d = request_delegation(db, a.assignment_id, a.resident_id, substitutes[0].resident_id, 'I have an unexpected study commitment. Could you help this week?')
            d.delegated_at = datetime(2026, 11, 9, 0, 30 + index)
            if index == 0:
                resolve_delegation(db, d.delegation_id, d.substitute_resident_id, 'accepted')
        if index == 3:
            complete(db, a.assignment_id, a.resident_id)
            a.completed_at = datetime(2026, 11, 9, 9)
    db.commit()
    return True

if __name__ == '__main__':
    with SessionLocal() as db:
        print('Seeded fixed demo: November 9–15, 2026.' if seed(db) else 'Database already populated; left unchanged.')
