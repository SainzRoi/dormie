"""HTTP integration tests; migrate a fresh database for every test."""
from datetime import date, datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select, text, inspect
from sqlalchemy.orm import Session
from app.main import app
from app.database import get_db, make_engine
from app.models import Resident, Chore, Assignment, Availability, ChoreRating
from app.services.chores import monday, MANILA, weekly_totals

@pytest.fixture
def setup(tmp_path):
    engine=make_engine('sqlite:///'+str(tmp_path/'integration.db'))
    config=Config('alembic.ini')
    with engine.begin() as connection:
        config.attributes['connection']=connection
        command.upgrade(config,'head')
    def database():
        with Session(engine, expire_on_commit=False) as db:
            yield db
    app.dependency_overrides[get_db]=database
    with TestClient(app) as client:
        yield client, engine
    app.dependency_overrides.clear()
    engine.dispose()

def mutate(client, path, body=None, method='POST'):
    token=client.get('/api/session').json()['csrf']
    return client.request(method,path,json=body,headers={'X-CSRF-Token':token})

def register(client,name='alex'):
    response=mutate(client,'/api/register',{'name':name.title(),'username':name,'password':'TestPassword123!'})
    assert response.status_code==201,response.text
    return response.json()['resident_id']

def login(client,name):
    assert mutate(client,'/api/login',{'username':name,'password':'TestPassword123!'}).status_code==200

def prepare(client):
    for name in ['alex','bea']:
        register(client,name)
        assert mutate(client,'/api/availability',{'days':[True]*7},'PUT').status_code==200
    login(client,'alex')
    cid=mutate(client,'/api/chores',{'name':'Bathroom','due_weekday':4}).json()['chore_id']
    assert mutate(client,f'/api/chores/{cid}/rating',{'intensity_rating':5},'PUT').status_code==200
    week=monday(datetime.now(MANILA).date())+timedelta(weeks=1)
    response=mutate(client,'/api/assignments/generate',{'start_date':str(week)})
    assert response.status_code==200,response.text
    return cid,week,response.json()['assignments'][0]

def test_auth_csrf_and_password_hash(setup):
    c,engine=setup
    assert c.get('/api/me').status_code==401
    assert c.post('/api/register',json={'username':'alex','name':'Alex','password':'12345678'}).status_code==403
    rid=register(c)
    assert c.get('/api/me').json()['resident_id']==rid
    with Session(engine) as db:
        assert db.get(Resident,rid).password_hash.startswith('$argon2id$')
    assert 'httponly' in c.get('/api/session').headers['set-cookie'].lower()
    assert mutate(c,'/api/logout').status_code==200
    assert c.get('/api/me').status_code==401
    assert mutate(c,'/api/login',{'username':'alex','password':'WrongPass123'}).status_code==401
    login(c,'alex')

def test_registration_duplicate_and_input_validation(setup):
    c,_=setup
    register(c)
    assert mutate(c,'/api/register',{'username':'alex','name':'Other','password':'TestPassword123!'}).status_code==409
    assert mutate(c,'/api/chores',{'name':'','due_weekday':8}).status_code==422
    assert mutate(c,'/api/chores',{'name':'Daily','due_weekday':1,'frequency':'daily'}).status_code==422

def test_ratings_availability_ownership_and_validation(setup):
    c,engine=setup
    alex=register(c)
    cid=mutate(c,'/api/chores',{'name':'Sweep','due_weekday':1}).json()['chore_id']
    for value in [0,6,2.5,True]:
        assert mutate(c,f'/api/chores/{cid}/rating',{'intensity_rating':value},'PUT').status_code==422
    assert mutate(c,f'/api/chores/{cid}/rating',{'intensity_rating':5},'PUT').status_code==200
    assert mutate(c,f'/api/chores/{cid}/rating',{'intensity_rating':4},'PUT').status_code==200
    bea=register(c,'bea')
    assert mutate(c,f'/api/chores/{cid}/rating',{'intensity_rating':1,'resident_id':alex},'PUT').status_code==422
    assert mutate(c,'/api/availability',{'days':[False]*7,'resident_id':alex},'PUT').status_code==422
    assert mutate(c,'/api/availability',{'days':[True]},'PUT').status_code==422
    assert mutate(c,'/api/availability',{'days':[True]*7},'PUT').status_code==200
    with Session(engine) as db:
        rows=list(db.scalars(select(ChoreRating)))
        assert len(rows)==1 and rows[0].resident_id==alex and rows[0].intensity_rating==4
        assert all(a.resident_id==bea for a in db.scalars(select(Availability)))

def test_generation_validation_unrated_and_idempotent(setup):
    c,engine=setup
    register(c)
    week=monday(datetime.now(MANILA).date())+timedelta(weeks=1)
    assert mutate(c,'/api/assignments/generate',{'start_date':str(week+timedelta(days=1))}).status_code==422
    cid=mutate(c,'/api/chores',{'name':'Unrated','due_weekday':1}).json()['chore_id']
    response=mutate(c,'/api/assignments/generate',{'start_date':str(week)})
    assert response.status_code==409 and 'Unrated' in response.json()['detail']
    mutate(c,f'/api/chores/{cid}/rating',{'intensity_rating':3},'PUT')
    result=mutate(c,'/api/assignments/generate',{'start_date':str(week)}).json()
    assert result['warnings'] and not result['assignments']
    mutate(c,'/api/availability',{'days':[True]*7},'PUT')
    first=mutate(c,'/api/assignments/generate',{'start_date':str(week)}).json()['assignments']
    mutate(c,f'/api/chores/{cid}/rating',{'intensity_rating':5},'PUT')
    assert mutate(c,'/api/assignments/generate',{'start_date':str(week)}).json()['assignments']==first

def test_full_delegation_completion_and_reporting(setup):
    c,engine=setup
    cid,week,a=prepare(c)
    aid=a['assignment_id']
    requested=mutate(c,f'/api/assignments/{aid}/delegations',{'substitute_resident_id':2,'reason':'Study group'})
    assert requested.status_code==201,requested.text
    did=requested.json()['delegation_id']
    assert mutate(c,f'/api/assignments/{aid}/delegations',{'substitute_resident_id':2,'reason':'Again'}).status_code==409
    assert mutate(c,f'/api/delegations/{did}/respond',{'status':'accepted'}).status_code==403
    login(c,'bea')
    assert c.get('/api/delegations').json()[0]['status']=='pending'
    assert mutate(c,f'/api/assignments/{aid}/complete').status_code==403
    assert mutate(c,f'/api/delegations/{did}/respond',{'status':'accepted'}).status_code==200
    assert mutate(c,f'/api/assignments/{aid}/complete').status_code==200
    stats=c.get('/api/statistics',params={'start_date':str(week)}).json()['residents']
    assert stats[0]['original']==5 and stats[0]['actual']==0
    assert stats[1]['actual']==5 and stats[1]['completed']==5
    with Session(engine) as db:
        assert db.get(Assignment,aid).resident_id==1
        view=db.execute(text('SELECT * FROM weekly_workload ORDER BY resident_id')).mappings().all()
        assert view[0]['originally_assigned']==5 and view[0]['actual_responsibility']==0
        assert view[1]['actual_responsibility']==5 and view[1]['completed']==5
    login(c,'alex')
    assert mutate(c,f'/api/assignments/{aid}/complete').status_code==403

def test_database_migration_constraints_and_chore_history(setup):
    c,engine=setup
    cid,week,a=prepare(c)
    assert len([t for t in inspect(engine).get_table_names() if t!='alembic_version'])==7
    assert 'weekly_workload' in inspect(engine).get_view_names()
    assert mutate(c,f'/api/chores/{cid}',{'name':'Bathroom','due_weekday':2},'PUT').status_code==409
    assert mutate(c,f'/api/chores/{cid}',{'name':'Bathroom','due_weekday':4,'is_active':False},'PUT').status_code==200
    from sqlalchemy.exc import IntegrityError
    with engine.begin() as conn:
        with pytest.raises(IntegrityError):conn.execute(text("UPDATE assignment SET due_date='2026-01-01'"))
    assert c.get('/').status_code==200
    assert c.get('/static/app.js').status_code==200
    assert "frame-ancestors 'none'" in c.get('/').headers['content-security-policy']

def test_simultaneous_generations_do_not_duplicate(setup):
    c,engine=setup
    _,week,_=prepare(c)
    cookies=dict(c.cookies)
    csrf=c.get('/api/session').json()['csrf']
    def run(_):
        with TestClient(app) as client:
            client.cookies.update(cookies)
            return client.post('/api/assignments/generate',json={'start_date':str(week)},headers={'X-CSRF-Token':csrf}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(run,range(2)))==[200,200]
    with Session(engine) as db:
        assert len(list(db.scalars(select(Assignment))))==1

def test_rejected_cancelled_history_and_acceptance_revalidation(setup):
    c,engine=setup
    _,_,a=prepare(c)
    aid=a['assignment_id']
    def request():
        response=mutate(c,f'/api/assignments/{aid}/delegations',{'substitute_resident_id':2,'reason':'Unexpected commitment'})
        assert response.status_code==201,response.text
        return response.json()['delegation_id']
    first=request()
    login(c,'bea')
    assert mutate(c,f'/api/delegations/{first}/respond',{'status':'rejected'}).status_code==200
    login(c,'alex')
    second=request()
    assert mutate(c,f'/api/delegations/{second}/respond',{'status':'cancelled'}).status_code==200
    third=request()
    login(c,'bea')
    mutate(c,'/api/availability',{'days':[False]*7},'PUT')
    assert mutate(c,f'/api/delegations/{third}/respond',{'status':'accepted'}).status_code==409
    assert [d['status'] for d in c.get('/api/delegations').json()]==['pending','cancelled','rejected']
