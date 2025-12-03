from sqlalchemy import Column, Integer, String, DateTime, Enum, JSON, Boolean
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class IntegrationType(str, enum.Enum):
    SSO_AZURE = "sso_azure"
    SSO_GOOGLE = "sso_google"
    SSO_SAML = "sso_saml"
    CALENDAR_M365 = "calendar_m365"
    CALENDAR_GOOGLE = "calendar_google"
    CHAT_SLACK = "chat_slack"
    CHAT_TEAMS = "chat_teams"
    TICKETING_JIRA = "ticketing_jira"
    TICKETING_GITLAB = "ticketing_gitlab"
    TICKETING_GITHUB = "ticketing_github"
    HR = "hr"
    STORAGE_ONEDRIVE = "storage_onedrive"
    STORAGE_SHAREPOINT = "storage_sharepoint"
    STORAGE_GOOGLE_DRIVE = "storage_google_drive"
    STORAGE_S3 = "storage_s3"
    VIDEO_TEAMS = "video_teams"
    VIDEO_ZOOM = "video_zoom"
    VIDEO_MEET = "video_meet"


class IntegrationStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PENDING = "pending"


class Integration(Base):
    __tablename__ = "integrations"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(Enum(IntegrationType), nullable=False)
    name = Column(String, nullable=False)
    config = Column(JSON, default=dict, nullable=False)  # Configuration (credentials, settings)
    status = Column(Enum(IntegrationStatus), default=IntegrationStatus.INACTIVE, nullable=False)
    last_sync = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(String, nullable=True)
    is_active = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

