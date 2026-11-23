"""Enforce integer weekday/rating values on SQLite's dynamically typed columns."""
from alembic import op
revision = '3c5d_integer_validation'
down_revision = '2a4b_due_date_guards'
branch_labels = None
depends_on = None

FIELDS = [('chore_rating', 'intensity_rating'), ('chore','due_weekday'), ('availability','weekday')]

def upgrade():
    # Triggers avoid rebuilding referenced tables and preserve existing FK history.
    if op.get_bind().dialect.name == 'sqlite':
        for table, column in FIELDS:
            for operation in ('INSERT','UPDATE'):
                op.execute(f"""CREATE TRIGGER {table}_integer_{operation.lower()}
                  BEFORE {operation} ON {table} FOR EACH ROW
                  WHEN typeof(NEW.{column}) != 'integer'
                  BEGIN SELECT RAISE(ABORT, 'Rating and weekday values must be integers'); END""")

def downgrade():
    if op.get_bind().dialect.name == 'sqlite':
        for table, column in FIELDS:
            for operation in ('insert','update'):
                op.execute(f'DROP TRIGGER {table}_integer_{operation}')
