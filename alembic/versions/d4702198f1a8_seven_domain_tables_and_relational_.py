"""seven domain tables and relational constraints"""
from alembic import op
import sqlalchemy as sa

revision = 'd4702198f1a8'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    mysql = op.get_bind().dialect.name == 'mysql'
    op.create_table('chore',
    sa.Column('chore_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('frequency', sa.String(length=10), nullable=False),
    sa.Column('due_weekday', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(create_constraint=True), nullable=False),
    sa.CheckConstraint("frequency = 'weekly'"),
    sa.CheckConstraint('due_weekday BETWEEN 1 AND 7'),
    sa.CheckConstraint(('char_length' if mysql else 'length') + '(trim(name)) BETWEEN 1 AND 100'),
    sa.PrimaryKeyConstraint('chore_id'),
    mysql_engine='InnoDB'
    )
    op.create_table('resident',
    sa.Column('resident_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('username', sa.String(length=40), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('is_active', sa.Boolean(create_constraint=True), nullable=False),
    sa.Column('joined_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint(('char_length' if mysql else 'length') + '(trim(name)) BETWEEN 1 AND 100'),
    sa.PrimaryKeyConstraint('resident_id'),
    sa.UniqueConstraint('username'),
    mysql_engine='InnoDB'
    )
    op.create_table('week',
    sa.Column('week_id', sa.Integer(), nullable=False),
    sa.Column('start_date', sa.Date(), nullable=False),
    sa.Column('end_date', sa.Date(), nullable=False),
    sa.CheckConstraint("end_date = DATE_ADD(start_date, INTERVAL 6 DAY)" if mysql else "end_date = date(start_date, '+6 days')", name='week_sunday'),
    sa.CheckConstraint("WEEKDAY(start_date) = 0" if mysql else "strftime('%w', start_date) = '1'", name='week_monday'),
    sa.PrimaryKeyConstraint('week_id'),
    sa.UniqueConstraint('start_date'),
    mysql_engine='InnoDB'
    )
    op.create_table('assignment',
    sa.Column('assignment_id', sa.Integer(), nullable=False),
    sa.Column('resident_id', sa.Integer(), nullable=False),
    sa.Column('chore_id', sa.Integer(), nullable=False),
    sa.Column('week_id', sa.Integer(), nullable=False),
    sa.Column('due_date', sa.Date(), nullable=False),
    sa.Column('workload_points', sa.Float(), nullable=False),
    sa.Column('status', sa.String(length=12), nullable=False),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.Column('rationale', sa.JSON(), nullable=False),
    sa.CheckConstraint("(status = 'completed' AND completed_at IS NOT NULL) OR (status = 'pending' AND completed_at IS NULL)"),
    sa.CheckConstraint("status IN ('pending','completed')"),
    sa.CheckConstraint('workload_points BETWEEN 1 AND 5'),
    sa.ForeignKeyConstraint(['chore_id'], ['chore.chore_id'], ),
    sa.ForeignKeyConstraint(['resident_id'], ['resident.resident_id'], ),
    sa.ForeignKeyConstraint(['week_id'], ['week.week_id'], ),
    sa.PrimaryKeyConstraint('assignment_id'),
    sa.UniqueConstraint('chore_id', 'week_id'),
    mysql_engine='InnoDB'
    )
    with op.batch_alter_table('assignment', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_assignment_chore_id'), ['chore_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_assignment_resident_id'), ['resident_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_assignment_week_id'), ['week_id'], unique=False)

    op.create_table('availability',
    sa.Column('availability_id', sa.Integer(), nullable=False),
    sa.Column('resident_id', sa.Integer(), nullable=False),
    sa.Column('weekday', sa.Integer(), nullable=False),
    sa.Column('is_available', sa.Boolean(create_constraint=True), nullable=False),
    sa.CheckConstraint('weekday BETWEEN 1 AND 7'),
    sa.ForeignKeyConstraint(['resident_id'], ['resident.resident_id'], ),
    sa.PrimaryKeyConstraint('availability_id'),
    sa.UniqueConstraint('resident_id', 'weekday'),
    mysql_engine='InnoDB'
    )
    with op.batch_alter_table('availability', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_availability_resident_id'), ['resident_id'], unique=False)

    op.create_table('chore_rating',
    sa.Column('rating_id', sa.Integer(), nullable=False),
    sa.Column('resident_id', sa.Integer(), nullable=False),
    sa.Column('chore_id', sa.Integer(), nullable=False),
    sa.Column('intensity_rating', sa.Integer(), nullable=False),
    sa.Column('rated_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint('intensity_rating BETWEEN 1 AND 5'),
    sa.ForeignKeyConstraint(['chore_id'], ['chore.chore_id'], ),
    sa.ForeignKeyConstraint(['resident_id'], ['resident.resident_id'], ),
    sa.PrimaryKeyConstraint('rating_id'),
    sa.UniqueConstraint('resident_id', 'chore_id'),
    mysql_engine='InnoDB'
    )
    with op.batch_alter_table('chore_rating', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_chore_rating_chore_id'), ['chore_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_chore_rating_resident_id'), ['resident_id'], unique=False)

    op.create_table('delegation',
    sa.Column('delegation_id', sa.Integer(), nullable=False),
    sa.Column('assignment_id', sa.Integer(), nullable=False),
    sa.Column('substitute_resident_id', sa.Integer(), nullable=False),
    sa.Column('reason', sa.Text(), nullable=False),
    sa.Column('delegated_at', sa.DateTime(), nullable=False),
    sa.Column('status', sa.String(length=12), nullable=False),
    sa.CheckConstraint("status IN ('pending','accepted','rejected','cancelled')"),
    sa.CheckConstraint(('char_length' if mysql else 'length') + '(trim(reason)) BETWEEN 1 AND 1000'),
    sa.ForeignKeyConstraint(['assignment_id'], ['assignment.assignment_id'], ),
    sa.ForeignKeyConstraint(['substitute_resident_id'], ['resident.resident_id'], ),
    sa.PrimaryKeyConstraint('delegation_id'),
    mysql_engine='InnoDB'
    )
    with op.batch_alter_table('delegation', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_delegation_assignment_id'), ['assignment_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_delegation_substitute_resident_id'), ['substitute_resident_id'], unique=False)
        if not mysql:
            batch_op.create_index('one_live_delegation', ['assignment_id'], unique=True, sqlite_where=sa.text("status IN ('pending','accepted')"), postgresql_where=sa.text("status IN ('pending','accepted')"))

    # ### end Alembic commands ###

def downgrade():
    if op.get_bind().dialect.name == 'mysql':
        # InnoDB requires FK-supporting indexes until the table is removed.
        for table in ('delegation', 'chore_rating', 'availability', 'assignment', 'week', 'resident', 'chore'):
            op.drop_table(table)
        return
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('delegation', schema=None) as batch_op:
        if op.get_bind().dialect.name != 'mysql':
            batch_op.drop_index('one_live_delegation', sqlite_where=sa.text("status IN ('pending','accepted')"), postgresql_where=sa.text("status IN ('pending','accepted')"))
        batch_op.drop_index(batch_op.f('ix_delegation_substitute_resident_id'))
        batch_op.drop_index(batch_op.f('ix_delegation_assignment_id'))

    op.drop_table('delegation')
    with op.batch_alter_table('chore_rating', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_chore_rating_resident_id'))
        batch_op.drop_index(batch_op.f('ix_chore_rating_chore_id'))

    op.drop_table('chore_rating')
    with op.batch_alter_table('availability', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_availability_resident_id'))

    op.drop_table('availability')
    with op.batch_alter_table('assignment', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_assignment_week_id'))
        batch_op.drop_index(batch_op.f('ix_assignment_resident_id'))
        batch_op.drop_index(batch_op.f('ix_assignment_chore_id'))

    op.drop_table('assignment')
    op.drop_table('week')
    op.drop_table('resident')
    op.drop_table('chore')
    # ### end Alembic commands ###
