from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean
from sqlalchemy.sql import func
from app.core.database import Base


class AutomationRule(Base):
    __tablename__ = "automation_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    trigger = Column(String, nullable=False)  # e.g., "task_created", "event_updated"
    conditions = Column(JSON, default=dict, nullable=False)  # If conditions
    actions = Column(JSON, default=list, nullable=False)  # Then actions
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(Integer, nullable=False)  # User ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

