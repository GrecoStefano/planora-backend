from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text, JSON, Enum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class CalendarScope(str, enum.Enum):
    PERSONAL = "personal"
    TEAM = "team"
    PROJECT = "project"
    RESOURCE = "resource"


class RSVPStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    TENTATIVE = "tentative"
    DECLINED = "declined"


class PrivacyLevel(str, enum.Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    CONFIDENTIAL = "confidential"


class Calendar(Base):
    __tablename__ = "calendars"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    scope = Column(Enum(CalendarScope), default=CalendarScope.PERSONAL, nullable=False)
    color = Column(String, default="#3788d8", nullable=False)
    description = Column(Text, nullable=True)
    acl = Column(JSON, default=dict, nullable=False)  # Access Control List
    is_visible = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    owner = relationship("User", back_populates="owned_calendars", foreign_keys=[owner_id])
    events = relationship("Event", back_populates="calendar", cascade="all, delete-orphan")
    resource = relationship("Resource", back_populates="calendar", uselist=False)


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    calendar_id = Column(Integer, ForeignKey("calendars.id"), nullable=False)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    start = Column(DateTime(timezone=True), nullable=False)
    end = Column(DateTime(timezone=True), nullable=False)
    all_day = Column(Boolean, default=False, nullable=False)
    recurrence = Column(String, nullable=True)  # RRULE string
    location = Column(String, nullable=True)
    video_link = Column(String, nullable=True)
    privacy_level = Column(Enum(PrivacyLevel), default=PrivacyLevel.PRIVATE, nullable=False)
    attachments = Column(JSON, default=list, nullable=False)
    event_metadata = Column("metadata", JSON, default=dict, nullable=False)  # For event type, subtype, etc.
    timezone = Column(String, default="UTC", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    calendar = relationship("Calendar", back_populates="events")
    creator = relationship("User", back_populates="events")
    attendees = relationship("EventAttendee", back_populates="event", cascade="all, delete-orphan")


class EventAttendee(Base):
    __tablename__ = "event_attendees"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rsvp_status = Column(Enum(RSVPStatus), default=RSVPStatus.PENDING, nullable=False)
    is_organizer = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    event = relationship("Event", back_populates="attendees")
    user = relationship("User", back_populates="event_attendances")

