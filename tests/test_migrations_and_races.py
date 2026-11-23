from concurrent.futures import ThreadPoolExecutor
from datetime import date
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from app.api.routes import write_lock
from app.models import Assignment, Delegation
from app.services import core

START=date(2026,11,9)

def test_fresh_migration_seed_and_cross_table_guards(tmp_path):
    database=tmp_path/'migrated.db'
    env={**os.environ,'DATABASE_URL':f'sqlite:///{database}'}
    subprocess.run([sys.executable,'-m','alembic','upgrade','head'],env=env,check=True,capture_output=True)
    subprocess.run([sys.executable,'-m','app.seed'],env=env,check=True,capture_output=True)
    with sqlite3.connect(database) as conn:
        tables={row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert len(tables-{'alembic_version'})==7
        assert conn.execute('SELECT count(*) FROM assignment').fetchone()[0]==20
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE assignment SET due_date='2026-11-10' WHERE assignment_id=1")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute('UPDATE chore SET due_weekday=7 WHERE chore_id=3')
        before=conn.execute('SELECT count(*) FROM resident').fetchone()[0]
    subprocess.run([sys.executable,'-m','app.seed'],env=env,check=True,capture_output=True)
    with sqlite3.connect(database) as conn:
        assert conn.execute('SELECT count(*) FROM resident').fetchone()[0]==before
    subprocess.run([sys.executable,'-m','alembic','downgrade','base'],env=env,check=True,capture_output=True)
    subprocess.run([sys.executable,'-m','alembic','upgrade','head'],env=env,check=True,capture_output=True)

def test_concurrent_generation_keeps_one_assignment_per_chore(factory,populated):
    def worker():
        with factory() as db:
            write_lock(db)
            result=core.generate(db,START,as_of=START)
            db.commit()
            return result
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:worker(),range(2)))
    assert sorted(len(r['created']) for r in results)==[0,4]
    with factory() as db:
        assert len(db.scalars(select(Assignment)).all())==4

def test_completion_acceptance_race_preserves_consistency(factory,populated):
    core.generate(populated,START,as_of=START)
    a=populated.scalar(select(Assignment).where(Assignment.chore_id==3))
    d=core.request_delegation(populated,a.assignment_id,1,2,'Race test')
    populated.commit()
    aid,did=a.assignment_id,d.delegation_id
    def worker(action):
        with factory() as db:
            write_lock(db)
            try:
                if action=='complete':core.complete(db,aid,1)
                else:core.resolve_delegation(db,did,2,'accepted')
                db.commit()
                return 'success'
            except HTTPException:
                db.rollback()
                return 'conflict'
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(worker,['complete','accept']))
    assert sorted(results)==['conflict','success']
    with factory() as db:
        a,d=db.get(Assignment,aid),db.get(Delegation,did)
        assert (a.status,d.status) in [('completed','cancelled'),('pending','accepted')]
