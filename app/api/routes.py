import secrets
from datetime import date
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, StrictBool
from sqlalchemy import select, text, func
from app.db import get_db
from app.models import Resident, Chore, ChoreRating, Availability, Week, Assignment, Delegation, utcnow
from app.services import core, auth

router = APIRouter(prefix='/api')
DB = Annotated[object, Depends(get_db)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Username = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r'^[a-zA-Z0-9_]{3,40}$')]

class Input(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Credentials(Input):
    username: Username
    password: str = Field(min_length=8, max_length=128)

class Signup(Credentials):
    name: Name

class Profile(Input):
    name: Name

class ChoreInput(Input):
    name: Name
    description: str = Field(default='', max_length=2000)
    due_weekday: int = Field(ge=1, le=7, strict=True)
    frequency: Literal['weekly'] = 'weekly'
    is_active: bool = True

class RatingInput(Input):
    intensity_rating: int = Field(ge=1, le=5, strict=True)

class AvailabilityInput(Input):
    days: list[StrictBool] = Field(min_length=7, max_length=7)

class GenerationInput(Input):
    start_date: date

class DelegationInput(Input):
    substitute_resident_id: int
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]

class ResolutionInput(Input):
    status: Literal['accepted', 'rejected', 'cancelled']

def write_lock(db):
    # Serialize writes before domain reads; released by commit/rollback.
    if db.bind.dialect.name == 'sqlite' and not db.in_transaction():
        db.execute(text('BEGIN IMMEDIATE'))
    elif db.bind.dialect.name == 'mysql':
        db.execute(text('SELECT id FROM app_write_lock WHERE id = 1 FOR UPDATE')).one()

def current(request: Request, db: DB):
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        expected = request.session.get('csrf')
        if not expected or not secrets.compare_digest(request.headers.get('X-CSRF-Token', ''), expected):
            core.fail('Session security token missing. Reload and try again.', 403)
        write_lock(db)
    resident = db.get(Resident, request.session.get('resident_id', -1))
    if not resident or not resident.is_active:
        core.fail('Please log in to continue.', 401)
    return resident

User = Annotated[Resident, Depends(current)]

def me_data(db, r):
    availability = db.scalars(select(Availability).where(Availability.resident_id == r.resident_id)).all()
    rated = db.scalar(select(func.count()).select_from(ChoreRating).join(Chore).where(ChoreRating.resident_id == r.resident_id, Chore.is_active.is_(True)))
    total = db.scalar(select(func.count()).select_from(Chore).where(Chore.is_active.is_(True)))
    return {'resident_id': r.resident_id, 'name': r.name, 'username': r.username, 'joined_at': r.joined_at.isoformat() + 'Z',
            'availability_saved': len(availability) == 7, 'rated_count': rated, 'chore_count': total}

def establish(request, r):
    request.session.clear()
    request.session.update(resident_id=r.resident_id, csrf=secrets.token_urlsafe(32))

@router.get('/auth/residents')
def public_residents(db: DB):
    # Login identifiers are public; selection alone never authenticates a resident.
    return [{'resident_id': x.resident_id, 'name': x.name, 'username': x.username} for x in core.active_residents(db)]

@router.post('/auth/signup')
def signup(data: Signup, request: Request, db: DB):
    write_lock(db)
    r = auth.signup(db, data.name, data.username, data.password)
    db.commit()
    establish(request, r)
    return me_data(db, r)

@router.post('/auth/login')
def login(data: Credentials, request: Request, db: DB):
    r = auth.authenticate(db, data.username, data.password)
    establish(request, r)
    return me_data(db, r)

@router.post('/auth/logout')
def logout(request: Request, r: User):
    request.session.clear()
    return {'message': 'Logged out.'}

@router.get('/me')
def me(request: Request, db: DB, r: User):
    return {**me_data(db, r), 'csrf': request.session['csrf'], 'today': core.today(), 'current_week': core.monday(core.today())}

@router.patch('/me')
def profile(data: Profile, db: DB, r: User):
    r.name = data.name
    db.commit()
    return me_data(db, r)

@router.get('/residents')
def directory(db: DB, r: User):
    return [{'resident_id': x.resident_id, 'name': x.name} for x in core.active_residents(db)]

@router.get('/availability')
def get_availability(db: DB, r: User):
    saved = {a.weekday: a.is_available for a in db.scalars(select(Availability).where(Availability.resident_id == r.resident_id))}
    return {'days': [saved.get(d, False) for d in range(1, 8)]}

@router.put('/availability')
def availability(data: AvailabilityInput, db: DB, r: User):
    for day, value in enumerate(data.days, 1):
        a = db.scalar(select(Availability).where(Availability.resident_id == r.resident_id, Availability.weekday == day))
        if a:
            a.is_available = value
        else:
            db.add(Availability(resident_id=r.resident_id, weekday=day, is_available=value))
    db.commit()
    return {'days': data.days}

@router.get('/chores')
def chores(db: DB, r: User):
    means = core.scores(db)
    own = {x.chore_id: x.intensity_rating for x in db.scalars(select(ChoreRating).where(ChoreRating.resident_id == r.resident_id))}
    return [{'chore_id': c.chore_id, 'name': c.name, 'description': c.description, 'due_weekday': c.due_weekday, 'frequency': c.frequency, 'is_active': c.is_active,
             'mean': means.get(c.chore_id, (None, 0))[0], 'rating_count': means.get(c.chore_id, (None, 0))[1], 'my_rating': own.get(c.chore_id)}
            for c in db.scalars(select(Chore).order_by(Chore.chore_id))]

@router.post('/chores')
def create_chore(data: ChoreInput, db: DB, r: User):
    c = Chore(**data.model_dump())
    db.add(c)
    db.commit()
    return {'chore_id': c.chore_id}

@router.put('/chores/{cid}')
def update_chore(cid: int, data: ChoreInput, db: DB, r: User):
    c = core.require(db, Chore, cid)
    if c.due_weekday != data.due_weekday and db.scalar(select(Assignment.assignment_id).where(Assignment.chore_id == cid).limit(1)):
        core.fail('This chore has assignment history. Retire it and create a new chore to change its due weekday.', 409)
    for key, value in data.model_dump().items():
        setattr(c, key, value)
    db.commit()
    return {'chore_id': cid}

@router.put('/chores/{cid}/rating')
def rate(cid: int, data: RatingInput, db: DB, r: User):
    chore = core.require(db, Chore, cid)
    if not chore.is_active:
        core.fail('Retired chores cannot receive new or updated ratings.', 409)
    row = db.scalar(select(ChoreRating).where(ChoreRating.resident_id == r.resident_id, ChoreRating.chore_id == cid))
    if not row:
        row = ChoreRating(resident_id=r.resident_id, chore_id=cid)
        db.add(row)
    row.intensity_rating, row.rated_at = data.intensity_rating, utcnow()
    db.commit()
    return {'intensity_rating': row.intensity_rating}

@router.get('/weeks')
def weeks(db: DB, r: User):
    return [{'week_id': w.week_id, 'start_date': w.start_date, 'end_date': w.end_date} for w in db.scalars(select(Week).order_by(Week.start_date.desc()))]

@router.post('/weeks/generate')
def generate(data: GenerationInput, db: DB, r: User):
    if data.start_date < core.monday(core.today()):
        core.fail('Generate the current or an upcoming week. Past weeks are read-only for generation.', 422)
    result = core.generate(db, data.start_date)
    db.commit()
    return result

@router.get('/assignments')
def assignments(start: date, db: DB, r: User):
    core.validate_week(start)
    return [core.assignment_data(db, a) for a in db.scalars(select(Assignment).join(Week).where(Week.start_date == start).order_by(Assignment.due_date, Assignment.assignment_id))]

@router.get('/assignments/{aid}')
def assignment(aid: int, db: DB, r: User):
    return core.assignment_data(db, core.require(db, Assignment, aid))

@router.post('/assignments/{aid}/complete')
def complete(aid: int, db: DB, r: User):
    a = core.complete(db, aid, r.resident_id)
    db.commit()
    return core.assignment_data(db, a)

@router.get('/assignments/{aid}/substitutes')
def substitutes(aid: int, db: DB, r: User):
    a = core.require(db, Assignment, aid)
    if a.resident_id != r.resident_id:
        core.fail('Only the original assignee may review substitutes.', 403)
    week = core.require(db, Week, a.week_id)
    points = {x['resident_id']: x['weekly']['actual'] for x in core.stats(db, week.start_date)}
    return [{'resident_id': x.resident_id, 'name': x.name, 'points': points[x.resident_id]} for x in core.eligible_substitutes(db, a)]

@router.post('/assignments/{aid}/delegations')
def delegate(aid: int, data: DelegationInput, db: DB, r: User):
    d = core.request_delegation(db, aid, r.resident_id, data.substitute_resident_id, data.reason)
    db.commit()
    return {'delegation_id': d.delegation_id, 'status': d.status}

@router.get('/delegations')
def delegations(db: DB, r: User):
    rows = db.execute(select(Delegation, Assignment).join(Assignment).where((Delegation.substitute_resident_id == r.resident_id) | (Assignment.resident_id == r.resident_id)).order_by(Delegation.delegation_id.desc())).all()
    return [{'delegation_id': d.delegation_id, 'assignment_id': a.assignment_id, 'name': core.require(db, Chore, a.chore_id).name,
             'original_name': core.require(db, Resident, a.resident_id).name, 'substitute_name': core.require(db, Resident, d.substitute_resident_id).name,
             'resident_id': a.resident_id, 'substitute_resident_id': d.substitute_resident_id, 'reason': d.reason, 'status': d.status,
             'due_date': a.due_date, 'workload_points': a.workload_points, 'delegated_at': d.delegated_at.isoformat()+'Z'} for d, a in rows]

@router.patch('/delegations/{did}')
def resolve(did: int, data: ResolutionInput, db: DB, r: User):
    d = core.resolve_delegation(db, did, r.resident_id, data.status)
    db.commit()
    return {'status': d.status}

@router.get('/statistics')
def statistics(start: date, db: DB, r: User):
    return core.stats(db, start)

@router.get('/residents/{rid}/status')
def resident_status(rid: int, start: date, db: DB, r: User):
    viewed = core.require(db, Resident, rid)
    if not viewed.is_active:
        core.fail('Resident is inactive.', 404)
    result = next(x for x in core.stats(db, start) if x['resident_id'] == rid)
    tasks = assignments(start, db, r)
    return {**result, 'joined_at': viewed.joined_at.isoformat()+'Z', 'assignments': [a for a in tasks if a['responsible_id'] == rid or a['resident_id'] == rid]}
