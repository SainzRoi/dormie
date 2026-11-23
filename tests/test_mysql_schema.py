"""Compile the complete MySQL migration chain even without a running server."""
import os
import subprocess
import sys


def test_mysql_migrations_compile(tmp_path):
    result = subprocess.run(
        [sys.executable, '-m', 'alembic', 'upgrade', 'head', '--sql'],
        env={**os.environ, 'DATABASE_URL': 'mysql+pymysql://dormie:unused@localhost/dormie'},
        check=True, capture_output=True, text=True,
    )
    sql = result.stdout
    assert 'strftime' not in sql
    assert 'WEEKDAY(start_date)' in sql
    assert 'GENERATED ALWAYS AS' in sql
    assert 'CREATE UNIQUE INDEX one_live_delegation ON delegation (live_assignment_id)' in sql
    assert 'CREATE TRIGGER assignment_due_insert' in sql
    assert 'CREATE TABLE app_write_lock' in sql
    assert 'ENGINE=InnoDB' in sql
