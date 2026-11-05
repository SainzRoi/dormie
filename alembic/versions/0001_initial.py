"""Seven domain tables, integrity constraints and reporting view."""
from alembic import op
import sqlalchemy as sa
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('resident', sa.Column('resident_id', sa.Integer, primary_key=True), sa.Column('name', sa.String(100), nullable=False), sa.Column('username', sa.String(50), nullable=False, unique=True), sa.Column('password_hash', sa.String(255), nullable=False), sa.Column('is_active', sa.Boolean, nullable=False), sa.Column('joined_at', sa.DateTime(timezone=True), nullable=False), sa.CheckConstraint('length(trim(name)) > 0', name='resident_name'))
    op.create_table('chore', sa.Column('chore_id', sa.Integer, primary_key=True), sa.Column('name', sa.String(100), nullable=False), sa.Column('description', sa.Text, nullable=False), sa.Column('frequency', sa.String(20), nullable=False), sa.Column('due_weekday', sa.Integer, nullable=False), sa.Column('is_active', sa.Boolean, nullable=False), sa.CheckConstraint("frequency = 'weekly'", name='weekly_only'), sa.CheckConstraint('due_weekday BETWEEN 1 AND 7', name='chore_day'), sa.CheckConstraint('length(trim(name)) > 0', name='chore_name'))
    op.create_table('chore_rating', sa.Column('rating_id', sa.Integer, primary_key=True), sa.Column('resident_id', sa.Integer, sa.ForeignKey('resident.resident_id'), nullable=False), sa.Column('chore_id', sa.Integer, sa.ForeignKey('chore.chore_id'), nullable=False), sa.Column('intensity_rating', sa.Integer, nullable=False), sa.Column('rated_at', sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint('resident_id', 'chore_id'), sa.CheckConstraint('intensity_rating BETWEEN 1 AND 5', name='rating_range'))
    constraints = [sa.CheckConstraint("strftime('%w', start_date) = '1' AND end_date = date(start_date, '+6 days')", name='monday_sunday')] if op.get_bind().dialect.name == 'sqlite' else []
    op.create_table('week', sa.Column('week_id', sa.Integer, primary_key=True), sa.Column('start_date', sa.Date, nullable=False, unique=True), sa.Column('end_date', sa.Date, nullable=False), *constraints)
    op.create_table('availability', sa.Column('availability_id', sa.Integer, primary_key=True), sa.Column('resident_id', sa.Integer, sa.ForeignKey('resident.resident_id'), nullable=False), sa.Column('weekday', sa.Integer, nullable=False), sa.Column('is_available', sa.Boolean, nullable=False), sa.UniqueConstraint('resident_id', 'weekday'), sa.CheckConstraint('weekday BETWEEN 1 AND 7', name='availability_day'))
    op.create_table('assignment', sa.Column('assignment_id', sa.Integer, primary_key=True), sa.Column('resident_id', sa.Integer, sa.ForeignKey('resident.resident_id'), nullable=False), sa.Column('chore_id', sa.Integer, sa.ForeignKey('chore.chore_id'), nullable=False), sa.Column('week_id', sa.Integer, sa.ForeignKey('week.week_id'), nullable=False), sa.Column('due_date', sa.Date, nullable=False), sa.Column('workload_points', sa.Float, nullable=False), sa.Column('status', sa.String(20), nullable=False), sa.Column('completed_at', sa.DateTime(timezone=True)), sa.Column('rationale', sa.Text, nullable=False), sa.UniqueConstraint('chore_id', 'week_id'), sa.CheckConstraint('workload_points BETWEEN 1 AND 5', name='points_range'), sa.CheckConstraint("(status = 'pending' AND completed_at IS NULL) OR (status = 'completed' AND completed_at IS NOT NULL)", name='completion_consistent'))
    op.create_table('delegation', sa.Column('delegation_id', sa.Integer, primary_key=True), sa.Column('assignment_id', sa.Integer, sa.ForeignKey('assignment.assignment_id'), nullable=False), sa.Column('substitute_resident_id', sa.Integer, sa.ForeignKey('resident.resident_id'), nullable=False), sa.Column('reason', sa.Text, nullable=False), sa.Column('delegated_at', sa.DateTime(timezone=True), nullable=False), sa.Column('status', sa.String(20), nullable=False), sa.CheckConstraint("status IN ('pending','accepted','rejected','cancelled')", name='delegation_status'), sa.CheckConstraint('length(trim(reason)) > 0', name='delegation_reason'))
    for table, columns in {'chore_rating': ['resident_id', 'chore_id'], 'availability': ['resident_id'], 'assignment': ['resident_id', 'chore_id', 'week_id'], 'delegation': ['assignment_id', 'substitute_resident_id']}.items():
        for column in columns:
            op.create_index(f'ix_{table}_{column}', table, [column])
    op.create_index('uq_active_delegation', 'delegation', ['assignment_id'], unique=True, sqlite_where=sa.text("status IN ('pending','accepted')"), postgresql_where=sa.text("status IN ('pending','accepted')"))
    op.execute('''CREATE VIEW weekly_workload AS
        SELECT r.resident_id, w.week_id, w.start_date,
        COALESCE(SUM(CASE WHEN a.resident_id = r.resident_id THEN a.workload_points ELSE 0 END), 0) AS originally_assigned,
        COALESCE(SUM(CASE WHEN COALESCE(d.substitute_resident_id, a.resident_id) = r.resident_id THEN a.workload_points ELSE 0 END), 0) AS actual_responsibility,
        COALESCE(SUM(CASE WHEN COALESCE(d.substitute_resident_id, a.resident_id) = r.resident_id AND a.status = 'completed' THEN a.workload_points ELSE 0 END), 0) AS completed
        FROM resident r CROSS JOIN week w
        LEFT JOIN assignment a ON a.week_id = w.week_id
        LEFT JOIN delegation d ON d.assignment_id = a.assignment_id AND d.status = 'accepted'
        GROUP BY r.resident_id, w.week_id, w.start_date''')
    if op.get_bind().dialect.name == 'sqlite':
        for event in ('INSERT', 'UPDATE'):
            op.execute(f'''CREATE TRIGGER assignment_due_{event.lower()} BEFORE {event} ON assignment
                WHEN NOT EXISTS (SELECT 1 FROM week w JOIN chore c ON c.chore_id = NEW.chore_id WHERE w.week_id = NEW.week_id AND NEW.due_date = date(w.start_date, '+' || (c.due_weekday - 1) || ' days'))
                BEGIN SELECT RAISE(ABORT, 'Assignment due date must match chore weekday and week'); END''')
        op.execute('''CREATE TRIGGER chore_weekday_history BEFORE UPDATE OF due_weekday ON chore
            WHEN NEW.due_weekday != OLD.due_weekday AND EXISTS (SELECT 1 FROM assignment WHERE chore_id = OLD.chore_id)
            BEGIN SELECT RAISE(ABORT, 'Retire chores with history instead of changing their weekday'); END''')

def downgrade():
    op.execute('DROP VIEW weekly_workload')
    for table in ['delegation', 'assignment', 'availability', 'week', 'chore_rating', 'chore', 'resident']:
        op.drop_table(table)
