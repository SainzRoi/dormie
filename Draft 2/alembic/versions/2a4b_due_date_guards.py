"""SQLite cross-table due-date guards; services validate on every supported database."""
from alembic import op
revision = '2a4b_due_date_guards'
down_revision = 'd4702198f1a8'
branch_labels = None
depends_on = None

def upgrade():
    if op.get_bind().dialect.name != 'sqlite':
        return
    for operation in ('INSERT','UPDATE'):
        op.execute(f"""CREATE TRIGGER assignment_due_{operation.lower()}
        BEFORE {operation} ON assignment
        FOR EACH ROW WHEN NOT EXISTS (
          SELECT 1 FROM week w JOIN chore c ON c.chore_id = NEW.chore_id
          WHERE w.week_id = NEW.week_id
            AND NEW.due_date = date(w.start_date, '+' || (c.due_weekday - 1) || ' days')
        ) BEGIN SELECT RAISE(ABORT, 'Assignment due date must match chore and week'); END""")
    op.execute("""CREATE TRIGGER chore_due_history BEFORE UPDATE OF due_weekday ON chore
      FOR EACH ROW WHEN NEW.due_weekday != OLD.due_weekday AND EXISTS (
        SELECT 1 FROM assignment WHERE chore_id = OLD.chore_id
      ) BEGIN SELECT RAISE(ABORT, 'Retire and replace chores to change historical weekdays'); END""")
    op.execute("""CREATE TRIGGER week_dates_history BEFORE UPDATE OF start_date, end_date ON week
      FOR EACH ROW WHEN (NEW.start_date != OLD.start_date OR NEW.end_date != OLD.end_date)
        AND EXISTS (SELECT 1 FROM assignment WHERE week_id = OLD.week_id)
      BEGIN SELECT RAISE(ABORT, 'Assigned week dates are immutable'); END""")

def downgrade():
    if op.get_bind().dialect.name == 'sqlite':
        for name in ('assignment_due_insert','assignment_due_update','chore_due_history','week_dates_history'):
            op.execute(f'DROP TRIGGER {name}')
