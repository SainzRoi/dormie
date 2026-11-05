# Verification record

## Passed

- **29 model/service/seed tests** using a real temporary SQLite database, SQLAlchemy 2.0.55, and Python 3.12. These exercise mean scores, rating/availability uniqueness, SQLite constraints, zero ratings, weekdays and due dates, recurring availability, fairness/history/newcomers/tie-breaks, idempotency, frozen snapshots, delegation lifecycle/authorization, completion, weekly and all-time statistics, and repeatable demo seeding.
- **4 frontend behavior tests** using Node 24 and locally available JSDOM 16.7.0. These render all six authenticated views, test text escaping, submit rating and availability forms, and exercise the login/register switch. API responses are fixtures, not a running FastAPI backend.
- Python source compilation and JavaScript syntax validation.

Commands executed in this restricted environment:

```bash
PYTHONPATH=/tmp/ds187-offline .venv312/bin/python -m unittest tests.test_domain -v
NODE_PATH=/home/roi/Documents/Projects/Tic-Tac-Toe/Sandbox/node_modules node tests/frontend.test.cjs
.venv312/bin/python -m compileall -q app alembic tests
node --check app/static/app.js
```

`/tmp/ds187-offline` contains a local copy of the already-installed SQLAlchemy package; the Python 3.12 test environment uses the cached Codex runtime and cached Argon2 wheels. No business framework was stubbed to produce these results. These machine-specific paths are not application dependencies; a normal installation uses `requirements.txt` and the README commands.

## Blocked / not verified

Package downloads failed with DNS/network restrictions. FastAPI, Starlette, Alembic, Uvicorn, and pytest were unavailable in the local caches. Attempts to execute pytest and Alembic reported missing modules.

Consequently, the **8 pytest HTTP/integration tests in `tests/test_api.py` have been written but not executed**, Alembic upgrade/downgrade and its SQL view/triggers have not been run, and the actual HTTP application has not been launched. Service tests create the schema using SQLAlchemy metadata and do not validate migration-only SQL. No desktop/mobile visual browser QA has been performed; JSDOM checks behavior, not layout.

After dependency installation, run:

```bash
python -m alembic upgrade head
python -m app.seed
python -m pytest -q
python -m uvicorn app.main:app --reload
```

Then follow the README walkthrough and check the UI at desktop and mobile widths. Full acceptance remains pending those checks.
