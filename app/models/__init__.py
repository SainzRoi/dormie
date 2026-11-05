from datetime import date, datetime, timezone
from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

def utcnow():
    return datetime.now(timezone.utc)

class Resident(Base):
    __tablename__ = "resident"
    resident_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (CheckConstraint("length(trim(name)) > 0", name="resident_name"),)

class Chore(Base):
    __tablename__ = "chore"
    chore_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    frequency: Mapped[str] = mapped_column(String(20), default="weekly")
    due_weekday: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (CheckConstraint("frequency = 'weekly'", name="weekly_only"), CheckConstraint("due_weekday BETWEEN 1 AND 7", name="chore_day"), CheckConstraint("length(trim(name)) > 0", name="chore_name"))

class ChoreRating(Base):
    __tablename__ = "chore_rating"
    rating_id: Mapped[int] = mapped_column(primary_key=True)
    resident_id: Mapped[int] = mapped_column(ForeignKey("resident.resident_id"), index=True)
    chore_id: Mapped[int] = mapped_column(ForeignKey("chore.chore_id"), index=True)
    intensity_rating: Mapped[int] = mapped_column(Integer)
    rated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint("resident_id", "chore_id"), CheckConstraint("intensity_rating BETWEEN 1 AND 5", name="rating_range"))

class Week(Base):
    __tablename__ = "week"
    week_id: Mapped[int] = mapped_column(primary_key=True)
    start_date: Mapped[date] = mapped_column(Date, unique=True)
    end_date: Mapped[date] = mapped_column(Date)
    __table_args__ = (CheckConstraint("strftime('%w', start_date) = '1' AND end_date = date(start_date, '+6 days')", name="monday_sunday").ddl_if(dialect="sqlite"),)

class Availability(Base):
    __tablename__ = "availability"
    availability_id: Mapped[int] = mapped_column(primary_key=True)
    resident_id: Mapped[int] = mapped_column(ForeignKey("resident.resident_id"), index=True)
    weekday: Mapped[int] = mapped_column(Integer)
    is_available: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (UniqueConstraint("resident_id", "weekday"), CheckConstraint("weekday BETWEEN 1 AND 7", name="availability_day"))

class Assignment(Base):
    __tablename__ = "assignment"
    assignment_id: Mapped[int] = mapped_column(primary_key=True)
    resident_id: Mapped[int] = mapped_column(ForeignKey("resident.resident_id"), index=True)
    chore_id: Mapped[int] = mapped_column(ForeignKey("chore.chore_id"), index=True)
    week_id: Mapped[int] = mapped_column(ForeignKey("week.week_id"), index=True)
    due_date: Mapped[date] = mapped_column(Date)
    workload_points: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rationale: Mapped[str] = mapped_column(Text, default="")
    __table_args__ = (UniqueConstraint("chore_id", "week_id"), CheckConstraint("workload_points BETWEEN 1 AND 5", name="points_range"), CheckConstraint("(status = 'pending' AND completed_at IS NULL) OR (status = 'completed' AND completed_at IS NOT NULL)", name="completion_consistent"))

class Delegation(Base):
    __tablename__ = "delegation"
    delegation_id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignment.assignment_id"), index=True)
    substitute_resident_id: Mapped[int] = mapped_column(ForeignKey("resident.resident_id"), index=True)
    reason: Mapped[str] = mapped_column(Text)
    delegated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    __table_args__ = (CheckConstraint("status IN ('pending','accepted','rejected','cancelled')", name="delegation_status"), CheckConstraint("length(trim(reason)) > 0", name="delegation_reason"), Index("uq_active_delegation", "assignment_id", unique=True, sqlite_where=text("status IN ('pending','accepted')"), postgresql_where=text("status IN ('pending','accepted')")))
