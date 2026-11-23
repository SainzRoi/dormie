from datetime import date, datetime, timedelta
import pytest
from fastapi import HTTPException
from sqlalchemy import select, delete, inspect, text
from sqlalchemy.exc import IntegrityError, OperationalError
from app.models import *
from app.services import core

START=date(2026,11,9)

def run(db,start=START):
    return core.generate(db,start,as_of=start)

def test_exact_seven_entities_and_constraints(db):
    infrastructure = {'alembic_version', 'app_write_lock'} if db.bind.dialect.name == 'mysql' else set()
    assert set(inspect(db.bind).get_table_names()) - infrastructure == {'resident','chore','chore_rating','week','availability','assignment','delegation'}
    assert 'week_id' not in Availability.__table__.columns
    if db.bind.dialect.name == 'sqlite':
        assert db.scalar(text('PRAGMA foreign_keys')) == 1
    else:
        assert db.scalar(text('SELECT @@foreign_key_checks')) == 1

@pytest.mark.parametrize('value',[0,6,-1,2.5])
def test_rating_database_check(populated,value):
    if populated.bind.dialect.name == 'mysql' and value == 2.5:
        pytest.skip('MySQL coerces fractional values on INT storage; API strict-int tests cover rejection')
    populated.scalar(select(ChoreRating).where(ChoreRating.resident_id==1,ChoreRating.chore_id==1)).intensity_rating=value
    with pytest.raises((IntegrityError, OperationalError)) as error: populated.flush()
    if populated.bind.dialect.name == 'mysql':
        assert error.value.orig.args[0] == 3819

def test_mean_active_residents_and_count(populated):
    assert core.scores(populated)=={1:(2.0,4),2:(3.0,4),3:(4.5,4),4:(3.5,4)}
    populated.get(Resident,4).is_active=False
    populated.flush()
    assert core.scores(populated)[3] == (14/3,3)

def test_unrated_blocks_entire_transaction(populated):
    populated.add(Chore(name='New chore',due_weekday=7))
    populated.flush()
    with pytest.raises(HTTPException,match='New chore'):run(populated)
    assert populated.scalar(select(Week)) is None
    assert populated.scalar(select(Assignment)) is None

@pytest.mark.parametrize('start,end',[(date(2026,11,10),date(2026,11,16)),(START,date(2026,11,14))])
def test_week_database_calendar_check(db,start,end):
    db.add(Week(start_date=start,end_date=end))
    with pytest.raises((IntegrityError, OperationalError)) as error:db.flush()
    if db.bind.dialect.name == 'mysql':
        assert error.value.orig.args[0] == 3819

def test_week_validation_and_due_dates(populated):
    with pytest.raises(HTTPException):run(populated,START+timedelta(days=1))
    run(populated)
    w=populated.scalar(select(Week))
    assert (w.end_date-w.start_date).days==6
    for a in populated.scalars(select(Assignment)):
        assert a.due_date.isoweekday()==populated.get(Chore,a.chore_id).due_weekday
        assert w.start_date<=a.due_date<=w.end_date

def test_missing_availability_and_unassigned(populated):
    populated.execute(delete(Availability).where(Availability.weekday==4))
    for row in populated.scalars(select(Availability).where(Availability.weekday==1)):
        row.is_available=row.resident_id==4
    result=run(populated)
    assert 'Clean bathroom' in result['warnings'][0]
    assert len(result['created'])==3
    sweep=populated.scalar(select(Assignment).where(Assignment.chore_id==1))
    assert sweep.resident_id==4

def test_availability_unique(populated):
    populated.add(Availability(resident_id=1,weekday=1,is_available=True))
    with pytest.raises(IntegrityError):populated.flush()

def test_deterministic_greedy_order_and_idempotency(populated):
    first=run(populated)
    rows=populated.scalars(select(Assignment).order_by(Assignment.assignment_id)).all()
    assert [(a.chore_id,a.resident_id) for a in rows]==[(3,1),(4,2),(2,3),(1,4)]
    second=run(populated)
    assert second['created']==[] and second['existing_count']==4
    assert first['created']==[a.assignment_id for a in populated.scalars(select(Assignment))]

def test_historical_average_and_newcomer(populated):
    old=Week(start_date=START-timedelta(weeks=1),end_date=START-timedelta(days=1))
    populated.add(old);populated.flush()
    populated.add(Assignment(resident_id=1,chore_id=3,week_id=old.week_id,due_date=old.start_date+timedelta(days=3),workload_points=4.5,rationale={}))
    populated.get(Resident,4).joined_at=datetime(2026,11,9)
    populated.flush();run(populated)
    bathroom=populated.scalar(select(Assignment).where(Assignment.week_id!=old.week_id,Assignment.chore_id==3))
    assert bathroom.resident_id==2
    # Four calendar weeks including absent/zero weeks, not just weeks with rows.
    assert bathroom.rationale['candidates'][-1]['burden']==4.5/4
    assert core.stats(populated,START)[3]['eligible_weeks']==1

def test_tie_break_fewest_current_chores(populated):
    # Alex burden 4 from one existing task; Bea same burden from two tasks.
    w=Week(start_date=START,end_date=START+timedelta(days=6));populated.add(w);populated.flush()
    for cid,rid,points in [(1,1,4),(2,2,2),(4,2,2)]:
        c=populated.get(Chore,cid)
        populated.add(Assignment(resident_id=rid,chore_id=cid,week_id=w.week_id,due_date=START+timedelta(days=c.due_weekday-1),workload_points=points,rationale={}))
    for rid in (3,4):populated.get(Resident,rid).is_active=False
    populated.flush();run(populated)
    assert populated.scalar(select(Assignment).where(Assignment.chore_id==3)).resident_id==1

def test_retry_missing_chores_accounts_for_existing(populated):
    populated.execute(delete(Availability).where(Availability.weekday==4))
    run(populated)
    saved=[(a.assignment_id,a.resident_id) for a in populated.scalars(select(Assignment))]
    populated.add(Availability(resident_id=1,weekday=4,is_available=True));populated.flush()
    result=run(populated)
    assert len(result['created'])==1
    assert all(populated.get(Assignment,aid).resident_id==rid for aid,rid in saved)
    assert populated.get(Assignment,result['created'][0]).rationale['planned_before']>0

def test_snapshot_and_explanation_immutable(populated):
    run(populated);a=populated.scalar(select(Assignment).where(Assignment.chore_id==3))
    old=a.rationale.copy()
    for r in populated.scalars(select(ChoreRating).where(ChoreRating.chore_id==3)):r.intensity_rating=1
    populated.flush();run(populated)
    assert a.workload_points==4.5 and a.rationale==old

def test_delegation_transfer_and_three_metrics(populated):
    run(populated);a=populated.scalar(select(Assignment).where(Assignment.chore_id==3))
    d=core.request_delegation(populated,a.assignment_id,1,2,'Study commitment')
    assert core.responsible_id(populated,a)==1
    core.resolve_delegation(populated,d.delegation_id,2,'accepted')
    assert a.resident_id==1 and core.responsible_id(populated,a)==2
    with pytest.raises(HTTPException) as e:core.complete(populated,a.assignment_id,1)
    assert e.value.status_code==403
    before=core.stats(populated,START)
    assert before[0]['weekly']=={'original':4.5,'actual':0.0,'completed':0.0}
    assert before[1]['weekly']['actual']==8.0 and before[1]['weekly']['completed']==0
    core.complete(populated,a.assignment_id,2)
    after=core.stats(populated,START)
    assert after[1]['weekly']['completed']==4.5
    assert sum(r['weekly']['actual'] for r in after)==13.0
    assert a.completed_at is not None

@pytest.mark.parametrize('invalid',['self','inactive','unavailable'])
def test_substitute_guards(populated,invalid):
    run(populated);a=populated.scalar(select(Assignment).where(Assignment.chore_id==3))
    target=1 if invalid=='self' else 2
    if invalid=='inactive':populated.get(Resident,2).is_active=False
    if invalid=='unavailable':populated.execute(delete(Availability).where(Availability.resident_id==2,Availability.weekday==4))
    populated.flush()
    with pytest.raises(HTTPException):core.request_delegation(populated,a.assignment_id,1,target,'Reason')

def test_duplicate_active_and_no_chains(populated):
    run(populated);a=populated.scalar(select(Assignment).where(Assignment.chore_id==3))
    d=core.request_delegation(populated,a.assignment_id,1,2,'Reason')
    with pytest.raises(HTTPException):core.request_delegation(populated,a.assignment_id,1,3,'Other reason')
    core.resolve_delegation(populated,d.delegation_id,2,'accepted')
    with pytest.raises(HTTPException):core.request_delegation(populated,a.assignment_id,1,3,'Another reason')
    with pytest.raises(HTTPException):core.request_delegation(populated,a.assignment_id,2,3,'Chain')

def test_partial_unique_index(populated):
    run(populated);a=populated.scalar(select(Assignment))
    core.request_delegation(populated,a.assignment_id,a.resident_id,2,'Reason')
    populated.add(Delegation(assignment_id=a.assignment_id,substitute_resident_id=3,reason='Race'))
    with pytest.raises(IntegrityError):populated.flush()

def test_reject_cancel_history_and_authorization(populated):
    run(populated);a=populated.scalar(select(Assignment).where(Assignment.chore_id==3))
    d=core.request_delegation(populated,a.assignment_id,1,2,'Reason')
    with pytest.raises(HTTPException):core.resolve_delegation(populated,d.delegation_id,3,'accepted')
    core.resolve_delegation(populated,d.delegation_id,2,'rejected')
    d2=core.request_delegation(populated,a.assignment_id,1,3,'Retry')
    with pytest.raises(HTTPException):core.resolve_delegation(populated,d2.delegation_id,3,'cancelled')
    core.resolve_delegation(populated,d2.delegation_id,1,'cancelled')
    assert d.status=='rejected' and d2.status=='cancelled'
    assert core.responsible_id(populated,a)==1

def test_complete_cancels_pending_prevents_late_accept(populated):
    run(populated);a=populated.scalar(select(Assignment).where(Assignment.chore_id==3))
    d=core.request_delegation(populated,a.assignment_id,1,2,'Reason')
    core.complete(populated,a.assignment_id,1)
    assert d.status=='cancelled'
    with pytest.raises(HTTPException):core.resolve_delegation(populated,d.delegation_id,2,'accepted')
    with pytest.raises(HTTPException):core.request_delegation(populated,a.assignment_id,1,3,'Late')
    with pytest.raises(HTTPException):core.complete(populated,a.assignment_id,1)

def test_accept_revalidates_availability(populated):
    run(populated);a=populated.scalar(select(Assignment).where(Assignment.chore_id==3))
    d=core.request_delegation(populated,a.assignment_id,1,2,'Reason')
    populated.execute(delete(Availability).where(Availability.resident_id==2,Availability.weekday==4))
    with pytest.raises(HTTPException):core.resolve_delegation(populated,d.delegation_id,2,'accepted')

def test_all_statistics_ranges_and_zero_filling(populated,monkeypatch):
    monkeypatch.setattr(core,'today',lambda:START)
    for n in (2,1,0):run(populated,START-timedelta(weeks=n))
    newcomer=Resident(name='Zero',username='zero',password_hash='not-used',joined_at=datetime(2026,11,9))
    populated.add(newcomer);populated.flush()
    result=core.stats(populated,START)
    zero=result[-1]
    assert zero['weekly']==dict.fromkeys(core.METRICS,0.0)
    assert zero['eligible_weeks']==1 and zero['average']['actual']==0
    assert sum(r['four_week']['actual'] for r in result)==26
    assert sum(r['cumulative']['actual'] for r in result)==39
    assert sum(r['average']['actual'] for r in result[:-1])==13
    assert sum(r['weekly']['completed'] for r in result)==0

def test_future_history_excludes_unfinished_calendar_weeks(populated,monkeypatch):
    monkeypatch.setattr(core,'today',lambda:START+timedelta(days=2))
    run(populated,START)
    future=START+timedelta(weeks=2)
    result=core.generate(populated,future)
    a=populated.get(Assignment,result['created'][0])
    assert a.rationale['historical_average']==0
    assert START.isoformat() not in a.rationale['history_weeks']
