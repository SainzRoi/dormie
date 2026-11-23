from datetime import date, datetime, timezone
from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Base(DeclarativeBase):
    pass

class Resident(Base):
    __tablename__ = 'resident'
    resident_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    username: Mapped[str] = mapped_column(String(40), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    __table_args__ = (CheckConstraint('length(trim(name)) BETWEEN 1 AND 100'),)

class Chore(Base):
    __tablename__ = 'chore'
    chore_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default='')
    frequency: Mapped[str] = mapped_column(String(10), default='weekly')
    due_weekday: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=True)
    __table_args__ = (CheckConstraint("frequency = 'weekly'"), CheckConstraint('due_weekday BETWEEN 1 AND 7'), CheckConstraint('due_weekday = CAST(due_weekday AS INTEGER)', name='due_weekday_integer').ddl_if(dialect='sqlite'), CheckConstraint('length(trim(name)) BETWEEN 1 AND 100'))

class ChoreRating(Base):
    __tablename__ = 'chore_rating'
    rating_id: Mapped[int] = mapped_column(primary_key=True)
    resident_id: Mapped[int] = mapped_column(ForeignKey('resident.resident_id'), index=True)
    chore_id: Mapped[int] = mapped_column(ForeignKey('chore.chore_id'), index=True)
    intensity_rating: Mapped[int] = mapped_column(Integer)
    rated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    __table_args__ = (UniqueConstraint('resident_id', 'chore_id'), CheckConstraint('intensity_rating BETWEEN 1 AND 5'), CheckConstraint('intensity_rating = CAST(intensity_rating AS INTEGER)', name='rating_integer').ddl_if(dialect='sqlite'))

class Week(Base):
    __tablename__ = 'week'
    week_id: Mapped[int] = mapped_column(primary_key=True)
    start_date: Mapped[date] = mapped_column(Date, unique=True)
    end_date: Mapped[date] = mapped_column(Date)
    __table_args__ = (
        CheckConstraint("strftime('%w', start_date) = '1'", name='week_monday').ddl_if(dialect='sqlite'),
        CheckConstraint("end_date = date(start_date, '+6 days')", name='week_sunday').ddl_if(dialect='sqlite'),
        CheckConstraint('WEEKDAY(start_date) = 0', name='week_monday_mysql').ddl_if(dialect='mysql'),
        CheckConstraint('end_date = DATE_ADD(start_date, INTERVAL 6 DAY)', name='week_sunday_mysql').ddl_if(dialect='mysql'),
    )

class Availability(Base):
    __tablename__ = 'availability'
    availability_id: Mapped[int] = mapped_column(primary_key=True)
    resident_id: Mapped[int] = mapped_column(ForeignKey('resident.resident_id'), index=True)
    weekday: Mapped[int] = mapped_column(Integer)
    is_available: Mapped[bool] = mapped_column(Boolean(create_constraint=True))
    __table_args__ = (UniqueConstraint('resident_id', 'weekday'), CheckConstraint('weekday BETWEEN 1 AND 7'), CheckConstraint('weekday = CAST(weekday AS INTEGER)', name='weekday_integer').ddl_if(dialect='sqlite'))

class Assignment(Base):
    __tablename__ = 'assignment'
    assignment_id: Mapped[int] = mapped_column(primary_key=True)
    resident_id: Mapped[int] = mapped_column(ForeignKey('resident.resident_id'), index=True)
    chore_id: Mapped[int] = mapped_column(ForeignKey('chore.chore_id'), index=True)
    week_id: Mapped[int] = mapped_column(ForeignKey('week.week_id'), index=True)
    due_date: Mapped[date] = mapped_column(Date)
    workload_points: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(12), default='pending')
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    rationale: Mapped[dict] = mapped_column(JSON)
    __table_args__ = (UniqueConstraint('chore_id', 'week_id'), CheckConstraint('workload_points BETWEEN 1 AND 5'), CheckConstraint("status IN ('pending','completed')"), CheckConstraint("(status = 'completed' AND completed_at IS NOT NULL) OR (status = 'pending' AND completed_at IS NULL)"))

class Delegation(Base):
    __tablename__ = 'delegation'
    delegation_id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey('assignment.assignment_id'), index=True)
    substitute_resident_id: Mapped[int] = mapped_column(ForeignKey('resident.resident_id'), index=True)
    reason: Mapped[str] = mapped_column(Text)
    delegated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    status: Mapped[str] = mapped_column(String(12), default='pending')
    __table_args__ = (CheckConstraint("status IN ('pending','accepted','rejected','cancelled')"), CheckConstraint('length(trim(reason)) BETWEEN 1 AND 1000'), Index('one_live_delegation', 'assignment_id', unique=True, sqlite_where=text("status IN ('pending','accepted')"), postgresql_where=text("status IN ('pending','accepted')")).ddl_if(dialect=('sqlite', 'postgresql')))
