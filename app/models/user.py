from sqlalchemy import Column, Integer, String, Enum, JSON, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class UserRole(str, enum.Enum):
    USER = "user"
    MANAGER = "manager"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    team = Column(String, nullable=True)
    timezone = Column(String, default="UTC", nullable=False)
    preferences = Column(JSON, default=dict, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    owned_calendars = relationship("Calendar", back_populates="owner", foreign_keys="Calendar.owner_id")
    events = relationship("Event", back_populates="creator")
    event_attendances = relationship("EventAttendee", back_populates="user")
    assigned_tasks = relationship("TaskAssignee", back_populates="user")
    watched_tasks = relationship("TaskWatcher", back_populates="user")
    owned_projects = relationship("Project", back_populates="owner", foreign_keys="Project.owner_id")
    notifications = relationship("Notification", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")

