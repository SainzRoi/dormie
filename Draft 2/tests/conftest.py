from datetime import date, datetime
import pytest
import os
import subprocess
import sys
import uuid
from sqlalchemy import text
from sqlalchemy.engine import make_url
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from app.db import make_engine, get_db
from app.models import Base, Resident, Chore, ChoreRating, Availability
from app.main import app
from app.services.auth import hasher

@pytest.fixture
def factory(tmp_path):
    mysql_url = os.getenv('MYSQL_TEST_URL')
    admin = None
    if mysql_url:
        url = make_url(mysql_url)
        if url.get_backend_name() != 'mysql':
            raise ValueError('MYSQL_TEST_URL must be a MySQL URL')
        database = 'dormie_test_' + uuid.uuid4().hex
        admin = make_engine(url.set(database=None).render_as_string(hide_password=False))
        with admin.begin() as connection:
            connection.execute(text(f'CREATE DATABASE `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_bin'))
        test_url = url.set(database=database).render_as_string(hide_password=False)
        engine = make_engine(test_url)
    else:
        engine = make_engine(f'sqlite:///{tmp_path}/test.db')
    try:
        if mysql_url:
            subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'],
                env={**os.environ, 'DATABASE_URL': test_url}, check=True, capture_output=True)
        else:
            Base.metadata.create_all(engine)
        factory = sessionmaker(engine, expire_on_commit=False)
        yield factory
    finally:
        engine.dispose()
        if admin is not None:
            with admin.begin() as connection:
                connection.execute(text(f'DROP DATABASE `{database}`'))
            admin.dispose()

@pytest.fixture
def db(factory):
    with factory() as session:
        yield session

@pytest.fixture
def populated(db):
    password_hash = hasher.hash('Dormie2026!')
    for name in ['Alex','Bea','Carlo','Dana']:
        db.add(Resident(name=name, username=name.lower(), password_hash=password_hash, joined_at=datetime(2026,10,5)))
    db.flush()
    for cid,(name,day,ratings) in enumerate([('Sweep floor',1,[2,2,3,1]),('Wash dishes',2,[3,3,2,4]),('Clean bathroom',4,[5,4,5,4]),('Mop floor',6,[3,4,3,4])],1):
        db.add(Chore(chore_id=cid,name=name,due_weekday=day))
        db.flush()
        for rid,rating in enumerate(ratings,1):
            db.add(ChoreRating(resident_id=rid,chore_id=cid,intensity_rating=rating))
    for rid in range(1,5):
        for day in range(1,8):
            db.add(Availability(resident_id=rid,weekday=day,is_available=True))
    db.commit()
    return db

@pytest.fixture
def client(factory):
    def override():
        with factory() as session:
            yield session
    app.dependency_overrides[get_db] = override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()

@pytest.fixture
def login(client,populated):
    def do(username='alex'):
        assert client.post('/api/auth/login',json={'username':username,'password':'Dormie2026!'}).status_code == 200
        data=client.get('/api/me').json()
        client.headers['X-CSRF-Token']=data['csrf']
        return data
    do()
    return do
