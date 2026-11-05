import secrets
from datetime import date
from typing import Annotated, Literal
from app.security import hasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy import select
from app.database import get_db
from app.models import Resident, Chore, ChoreRating, Availability, Week, Assignment, Delegation, utcnow
from app.services import chores as svc

router = APIRouter(prefix='/api')
# Equal-cost failure for unknown usernames.
DUMMY_HASH = hasher.hash(secrets.token_hex(24))
Text100 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]

class Input(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Credentials(Input):
    username: Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, pattern=r'^[a-z0-9_]{3,50}$')]
    password: str = Field(min_length=8, max_length=128)

class Signup(Credentials):
    name: Text100

class ChoreInput(Input):
    name: Text100
    description: str = Field(default='', max_length=2000)
    frequency: Literal['weekly'] = 'weekly'
    due_weekday: int = Field(ge=1, le=7, strict=True)
    is_active: bool = True

class RatingInput(Input):
    intensity_rating: int = Field(ge=1, le=5, strict=True)

class AvailabilityInput(Input):
    days: list[bool] = Field(min_length=7, max_length=7)

class WeekInput(Input):
    start_date: date

class DelegationInput(Input):
    substitute_resident_id: int
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]

class ResponseInput(Input):
    status: Literal['accepted', 'rejected', 'cancelled']

def public_resident(r):
    return dict(resident_id=r.resident_id, name=r.name, username=r.username)

def transaction(request: Request, db=Depends(get_db)):
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        expected = request.session.get('csrf')
        supplied = request.headers.get('X-CSRF-Token', '')
        if not expected or not secrets.compare_digest(expected, supplied):
            raise HTTPException(403, 'Invalid CSRF token. Refresh the page and try again.')
        svc.write_lock(db)
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise

def current(request: Request, db=Depends(transaction)):
    rid = request.session.get('resident_id')
    r = db.get(Resident, rid) if rid else None
    if not r or not r.is_active:
        raise HTTPException(401, 'Sign in to continue.')
    return r

@router.get('/session')
def session(request: Request, db=Depends(transaction)):
    if 'csrf' not in request.session:
        request.session['csrf'] = secrets.token_urlsafe(32)
    rid = request.session.get('resident_id')
    r = db.get(Resident, rid) if rid else None
    return {'csrf': request.session['csrf'], 'resident': public_resident(r) if r and r.is_active else None}

@router.post('/register', status_code=201)
def register(data: Signup, request: Request, db=Depends(transaction)):
    if db.scalar(select(Resident).where(Resident.username == data.username)):
        raise HTTPException(409, 'Username already exists.')
    r = Resident(name=data.name, username=data.username, password_hash=hasher.hash(data.password))
    db.add(r)
    db.flush()
    request.session.clear()
    request.session.update(resident_id=r.resident_id, csrf=secrets.token_urlsafe(32))
    return public_resident(r)

@router.post('/login')
def login(data: Credentials, request: Request, db=Depends(transaction)):
    r = db.scalar(select(Resident).where(Resident.username == data.username))
    try:
        hasher.verify(r.password_hash if r else DUMMY_HASH, data.password)
    except (VerificationError, InvalidHashError):
        raise HTTPException(401, 'Incorrect username or password.')
    if not r or not r.is_active:
        raise HTTPException(401, 'Incorrect username or password.')
    request.session.clear()
    request.session.update(resident_id=r.resident_id, csrf=secrets.token_urlsafe(32))
    return public_resident(r)

@router.post('/logout')
def logout(request: Request, db=Depends(transaction)):
    request.session.clear()
    return {'message': 'Signed out.'}

@router.get('/me')
def me(r=Depends(current)):
    return public_resident(r)

@router.get('/chores')
def catalog(r=Depends(current), db=Depends(transaction)):
    collective = svc.scores(db)
    mine = {x.chore_id: x.intensity_rating for x in db.scalars(select(ChoreRating).where(ChoreRating.resident_id == r.resident_id))}
    return [dict(chore_id=c.chore_id, name=c.name, description=c.description, frequency=c.frequency, due_weekday=c.due_weekday, is_active=c.is_active, mean=collective.get(c.chore_id, (None, 0))[0], count=collective.get(c.chore_id, (None, 0))[1], my_rating=mine.get(c.chore_id)) for c in db.scalars(select(Chore).order_by(Chore.chore_id))]

@router.post('/chores', status_code=201)
def add_chore(data: ChoreInput, r=Depends(current), db=Depends(transaction)):
    c = Chore(**data.model_dump())
    db.add(c)
    db.flush()
    return {'chore_id': c.chore_id, 'message': 'Chore created. Rate it before generating assignments.'}

@router.put('/chores/{cid}')
def edit_chore(cid: int, data: ChoreInput, r=Depends(current), db=Depends(transaction)):
    c = svc.require(db, Chore, cid)
    if data.due_weekday != c.due_weekday and db.scalar(select(Assignment).where(Assignment.chore_id == cid)):
        raise HTTPException(409, 'This chore has assignment history. Retire it and create a new chore to change its weekday.')
    for key, value in data.model_dump().items():
        setattr(c, key, value)
    return {'message': 'Chore updated.'}

@router.put('/chores/{cid}/rating')
def rate(cid: int, data: RatingInput, r=Depends(current), db=Depends(transaction)):
    svc.require(db, Chore, cid)
    rating = db.scalar(select(ChoreRating).where(ChoreRating.chore_id == cid, ChoreRating.resident_id == r.resident_id))
    if not rating:
        rating = ChoreRating(chore_id=cid, resident_id=r.resident_id)
        db.add(rating)
    rating.intensity_rating, rating.rated_at = data.intensity_rating, utcnow()
    return {'message': 'Rating saved. Existing assignment scores remain unchanged.'}

@router.get('/availability')
def availability(r=Depends(current), db=Depends(transaction)):
    rows = {a.weekday: a.is_available for a in db.scalars(select(Availability).where(Availability.resident_id == r.resident_id))}
    return {'days': [rows.get(i, False) for i in range(1, 8)], 'configured_days': len(rows)}

@router.put('/availability')
def set_availability(data: AvailabilityInput, r=Depends(current), db=Depends(transaction)):
    for day, available in enumerate(data.days, 1):
        a = db.scalar(select(Availability).where(Availability.resident_id == r.resident_id, Availability.weekday == day))
        if not a:
            a = Availability(resident_id=r.resident_id, weekday=day)
            db.add(a)
        a.is_available = available
    return {'message': 'Recurring availability saved for future generation.'}

@router.get('/weeks')
def weeks(r=Depends(current), db=Depends(transaction)):
    return [{'start_date': w.start_date, 'end_date': w.end_date, 'week_id': w.week_id} for w in db.scalars(select(Week).order_by(Week.start_date.desc()))]

@router.get('/assignments')
def assignments(start_date: date, r=Depends(current), db=Depends(transaction)):
    svc.validate_week(start_date)
    rows = svc.assignment_rows(db, start_date)
    assigned = {a['chore_id'] for a in rows}
    score = svc.scores(db)
    warnings = [f'{c.name}: unassigned' + (' — needs at least one active-resident rating.' if c.chore_id not in score else ' — generate missing chores after checking availability.') for c in db.scalars(select(Chore).where(Chore.is_active.is_(True))) if c.chore_id not in assigned]
    return {'assignments': rows, 'warnings': warnings}

@router.post('/assignments/generate')
def generate(data: WeekInput, r=Depends(current), db=Depends(transaction)):
    return svc.generate(db, data.start_date)

@router.post('/assignments/{aid}/complete')
def complete(aid: int, r=Depends(current), db=Depends(transaction)):
    return svc.complete(db, aid, r.resident_id)

@router.post('/assignments/{aid}/delegations', status_code=201)
def delegate(aid: int, data: DelegationInput, r=Depends(current), db=Depends(transaction)):
    return svc.request_delegation(db, aid, r.resident_id, data.substitute_resident_id, data.reason)

@router.get('/delegations')
def delegations(r=Depends(current), db=Depends(transaction)):
    rows = []
    for d in db.scalars(select(Delegation).order_by(Delegation.delegation_id.desc())):
        a = db.get(Assignment, d.assignment_id)
        if r.resident_id not in (a.resident_id, d.substitute_resident_id):
            continue
        rows.append(dict(delegation_id=d.delegation_id, assignment_id=a.assignment_id, chore=db.get(Chore, a.chore_id).name, original=db.get(Resident, a.resident_id).name, original_id=a.resident_id, substitute=db.get(Resident, d.substitute_resident_id).name, substitute_id=d.substitute_resident_id, due_date=a.due_date, reason=d.reason, status=d.status, delegated_at=d.delegated_at))
    return rows

@router.post('/delegations/{did}/respond')
def respond(did: int, data: ResponseInput, r=Depends(current), db=Depends(transaction)):
    return svc.respond(db, did, r.resident_id, data.status)

@router.get('/statistics')
def statistics(start_date: date, r=Depends(current), db=Depends(transaction)):
    return svc.statistics(db, start_date)
