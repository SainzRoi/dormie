import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import make_url

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./dormie.db')

def make_engine(url):
    backend = make_url(url).get_backend_name()
    options = {'pool_pre_ping': True}
    if backend == 'mysql':
        options.update(isolation_level='READ COMMITTED', pool_recycle=1800)
    engine = create_engine(url, connect_args={'check_same_thread': False, 'timeout': 20} if backend == 'sqlite' else {}, **options)
    if url.startswith('sqlite'):
        @event.listens_for(engine, 'connect')
        def sqlite_setup(conn, _):
            conn.execute('PRAGMA foreign_keys=ON')
            conn.execute('PRAGMA busy_timeout=20000')
    return engine

engine = make_engine(DATABASE_URL)
SessionLocal = sessionmaker(engine, expire_on_commit=False)

def get_db():
    with SessionLocal() as db:
        yield db
