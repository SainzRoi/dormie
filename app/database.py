import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

class Base(DeclarativeBase):
    pass

def make_engine(url):
    url = make_url(url)
    if url.drivername in ('postgres', 'postgresql'):
        url = url.set(drivername='postgresql+psycopg')
    options = {}
    if url.get_backend_name() == 'sqlite':
        options['connect_args'] = {"check_same_thread": False, "timeout": 30}
    elif url.get_backend_name() == 'postgresql':
        # Let the hosted database pool connections across serverless instances.
        options['poolclass'] = NullPool
        options['connect_args'] = {'prepare_threshold': None, 'connect_timeout': 15}
    engine = create_engine(url, **options)
    if url.get_backend_name() == 'sqlite':
        @event.listens_for(engine, "connect")
        def configure(dbapi, _):
            dbapi.execute("PRAGMA foreign_keys=ON")
    return engine

database_url = os.getenv("DATABASE_URL", "sqlite:///./dorm.db")
if os.getenv('VERCEL') and make_url(database_url).get_backend_name() not in ('postgres', 'postgresql'):
    raise RuntimeError('Set DATABASE_URL to a hosted PostgreSQL database before deploying to Vercel.')
engine = make_engine(database_url)
SessionLocal = sessionmaker(engine, expire_on_commit=False)

def get_db():
    with SessionLocal() as db:
        yield db
