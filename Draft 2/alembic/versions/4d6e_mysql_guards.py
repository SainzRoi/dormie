"""MySQL integrity guards and transactional write mutex."""
from alembic import op
import sqlalchemy as sa

revision = '4d6e_mysql_guards'
down_revision = '3c5d_integer_validation'
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name != 'mysql':
        return
    # NULL values allow unlimited rejected/cancelled history per assignment.
    op.add_column('delegation', sa.Column('live_assignment_id', sa.Integer(),
        sa.Computed("CASE WHEN status IN ('pending','accepted') THEN assignment_id ELSE NULL END")))
    op.create_index('one_live_delegation', 'delegation', ['live_assignment_id'], unique=True)
    op.create_table('app_write_lock', sa.Column('id', sa.Integer(), primary_key=True), mysql_engine='InnoDB')
    op.execute('INSERT INTO app_write_lock (id) VALUES (1)')
    for operation in ('INSERT', 'UPDATE'):
        op.execute(f"""CREATE TRIGGER assignment_due_{operation.lower()}
          BEFORE {operation} ON assignment FOR EACH ROW
          BEGIN
            IF NOT EXISTS (
              SELECT 1 FROM week w JOIN chore c ON c.chore_id = NEW.chore_id
              WHERE w.week_id = NEW.week_id
                AND NEW.due_date = DATE_ADD(w.start_date, INTERVAL (c.due_weekday - 1) DAY)
            ) THEN
              SIGNAL SQLSTATE '23000' SET MESSAGE_TEXT = 'Assignment due date must match chore and week';
            END IF;
          END""")
    op.execute("""CREATE TRIGGER chore_due_history BEFORE UPDATE ON chore FOR EACH ROW
      BEGIN
        IF NEW.due_weekday != OLD.due_weekday AND EXISTS (
          SELECT 1 FROM assignment WHERE chore_id = OLD.chore_id
        ) THEN
          SIGNAL SQLSTATE '23000' SET MESSAGE_TEXT = 'Retire and replace chores to change historical weekdays';
        END IF;
      END""")
    op.execute("""CREATE TRIGGER week_dates_history BEFORE UPDATE ON week FOR EACH ROW
      BEGIN
        IF (NEW.start_date != OLD.start_date OR NEW.end_date != OLD.end_date)
          AND EXISTS (SELECT 1 FROM assignment WHERE week_id = OLD.week_id) THEN
          SIGNAL SQLSTATE '23000' SET MESSAGE_TEXT = 'Assigned week dates are immutable';
        END IF;
      END""")


def downgrade():
    if op.get_bind().dialect.name != 'mysql':
        return
    for name in ('assignment_due_insert', 'assignment_due_update', 'chore_due_history', 'week_dates_history'):
        op.execute(f'DROP TRIGGER {name}')
    op.drop_table('app_write_lock')
    op.drop_index('one_live_delegation', table_name='delegation')
    op.drop_column('delegation', 'live_assignment_id')
