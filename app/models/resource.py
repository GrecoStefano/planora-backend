from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class ResourceType(str, enum.Enum):
    ROOM = "room"
    VEHICLE = "vehicle"
    EQUIPMENT = "equipment"
    OTHER = "other"


class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(Enum(ResourceType), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    calendar_id = Column(Integer, ForeignKey("calendars.id"), unique=True, nullable=False)
    capacity = Column(Integer, default=1, nullable=False)  # For rooms: max people
    location = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    calendar = relationship("Calendar", back_populates="resource")

