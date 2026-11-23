from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from sqlalchemy import select
from app.models import Resident
from app.services.core import fail

hasher = PasswordHasher()
DUMMY_HASH = hasher.hash('dummy-password-for-timing')

def authenticate(db, username, password):
    resident = db.scalar(select(Resident).where(Resident.username == username.lower()))
    try:
        hasher.verify(resident.password_hash if resident else DUMMY_HASH, password)
    except (VerificationError, InvalidHashError):
        fail('Invalid username or password.', 401)
    if not resident or not resident.is_active:
        fail('Invalid username or password.', 401)
    return resident

def signup(db, name, username, password):
    if db.scalar(select(Resident).where(Resident.username == username.lower())):
        fail('This username is already taken.', 409)
    resident = Resident(name=name, username=username.lower(), password_hash=hasher.hash(password))
    db.add(resident)
    db.flush()
    return resident
