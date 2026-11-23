from datetime import date, timedelta
from sqlalchemy import select, func
from app.models import *
from app.services import core

def test_auth_signup_login_logout(client):
    assert client.get('/api/me').status_code==401
    assert client.post('/api/auth/signup',json={'name':'New','username':'new','password':'short'}).status_code==422
    response=client.post('/api/auth/signup',json={'name':'New Resident','username':'new','password':'Password123'})
    assert response.status_code==200
    me=client.get('/api/me').json()
    assert 'password_hash' not in me
    assert me['availability_saved'] is False
    assert client.post('/api/auth/signup',json={'name':'Same','username':'NEW','password':'Password123'}).status_code==409
    assert client.post('/api/auth/logout',headers={'X-CSRF-Token':me['csrf']}).status_code==200
    assert client.get('/api/me').status_code==401
    assert client.post('/api/auth/login',json={'username':'new','password':'WrongPassword'}).status_code==401
    assert client.post('/api/auth/login',json={'username':'new','password':'Password123'}).status_code==200

def test_rating_validation_upsert_security(client,login,populated):
    for value in [0,6,2.5,True]:
        assert client.put('/api/chores/3/rating',json={'intensity_rating':value}).status_code==422
    for value in [1,5,4]:
        assert client.put('/api/chores/3/rating',json={'intensity_rating':value}).status_code==200
    assert client.put('/api/chores/3/rating',json={'intensity_rating':3,'resident_id':2}).status_code==422
    populated.expire_all()
    ratings=populated.scalars(select(ChoreRating).where(ChoreRating.chore_id==3)).all()
    assert len(ratings)==4
    assert next(r for r in ratings if r.resident_id==2).intensity_rating==4
    assert client.get('/api/chores').json()[2]['mean']==4.25

def test_availability_owned_and_explicit(client,login,populated):
    assert client.put('/api/availability',json={'days':[False]*7}).status_code==200
    assert client.get('/api/availability').json()['days']==[False]*7
    assert client.put('/api/availability',json={'days':[True]}).status_code==422
    assert client.put('/api/availability',json={'days':[True]*7,'resident_id':2}).status_code==422
    login('bea')
    assert client.get('/api/availability').json()['days']==[True]*7

def test_csrf_and_origin(client,login):
    token=client.headers.pop('X-CSRF-Token')
    assert client.put('/api/availability',json={'days':[False]*7}).status_code==403
    client.headers['X-CSRF-Token']=token
    assert client.put('/api/availability',json={'days':[False]*7},headers={'Origin':'https://evil.invalid'}).status_code==403

def test_generate_api_and_completion_authorization(client,login,populated):
    start=core.monday(core.today())+timedelta(weeks=1)
    response=client.post('/api/weeks/generate',json={'start_date':start.isoformat()})
    assert response.status_code==200,response.text
    tasks=client.get('/api/assignments',params={'start':str(start)}).json()
    assert len(tasks)==4
    a=next(a for a in tasks if a['resident_id']!=1)
    assert client.post(f"/api/assignments/{a['assignment_id']}/complete").status_code==403
    assert client.post('/api/weeks/generate',json={'start_date':str(start)}).json()['created']==[]
    assert client.post('/api/weeks/generate',json={'start_date':'2020-01-06'}).status_code==422

def test_directory_status_privacy_and_delegation_inbox(client,login,populated):
    start=core.monday(core.today())
    client.post('/api/weeks/generate',json={'start_date':str(start)})
    tasks=client.get('/api/assignments',params={'start':str(start)}).json()
    a=next(a for a in tasks if a['resident_id']==1)
    aid=a['assignment_id']
    d=client.post(f'/api/assignments/{aid}/delegations',json={'substitute_resident_id':2,'reason':'PRIVATE REASON'})
    assert d.status_code==200,d.text
    did=d.json()['delegation_id']
    assert client.patch(f'/api/delegations/{did}',json={'status':'accepted'}).status_code==403
    login('carlo')
    assert client.get('/api/delegations').json()==[]
    assert 'PRIVATE REASON' not in client.get('/api/residents/1/status',params={'start':str(start)}).text
    assert 'password' not in client.get('/api/residents').text
    assert client.get(f'/api/assignments/{aid}/substitutes').status_code==403
    assert client.get('/api/me').json()['name']=='Carlo'
    login('bea')
    assert client.patch(f'/api/delegations/{did}',json={'status':'accepted'}).status_code==200
    assert client.post(f'/api/assignments/{aid}/complete').status_code==200
    updated=client.get(f'/api/assignments/{aid}').json()
    assert updated['resident_id']==1 and updated['responsible_id']==2

def test_chore_crud_and_weekday_history_policy(client,login):
    response=client.post('/api/chores',json={'name':'Tidy shelf','due_weekday':3})
    assert response.status_code==200
    cid=response.json()['chore_id']
    assert client.put(f'/api/chores/{cid}',json={'name':'Tidy shelves','due_weekday':5}).status_code==200
    assert client.post('/api/chores',json={'name':'Invalid','due_weekday':2,'frequency':'daily'}).status_code==422
    assert client.post('/api/weeks/generate',json={'start_date':str(core.monday(core.today()))}).status_code==422
    assert client.put(f'/api/chores/{cid}/rating',json={'intensity_rating':3}).status_code==200
    client.post('/api/weeks/generate',json={'start_date':str(core.monday(core.today()))})
    assert client.put(f'/api/chores/{cid}',json={'name':'Tidy shelves','due_weekday':6}).status_code==409
    assert client.put(f'/api/chores/{cid}',json={'name':'Tidy shelves','due_weekday':5,'is_active':False}).status_code==200

def test_inactive_login_blocked(client,populated):
    populated.get(Resident,1).is_active=False;populated.commit()
    assert client.post('/api/auth/login',json={'username':'alex','password':'Dormie2026!'}).status_code==401

def test_rendered_page_and_assets(client):
    assert client.get('/').status_code==200
    assert 'Dormie' in client.get('/').text
    assert client.get('/static/app.js').status_code==200
    assert client.get('/static/assets/resident-0.svg').status_code==200


def test_retired_chore_rejects_rating_updates(client,login,populated):
    chore=populated.get(Chore,1)
    chore.is_active=False
    populated.commit()
    response=client.put('/api/chores/1/rating',json={'intensity_rating':5})
    assert response.status_code==409
    assert 'Retired chores' in response.json()['detail']
