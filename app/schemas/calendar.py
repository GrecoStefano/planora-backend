from pydantic import BaseModel, Field, field_serializer
from typing import Optional, List
from datetime import datetime
from app.models.calendar import CalendarScope, RSVPStatus, PrivacyLevel


class CalendarBase(BaseModel):
    name: str
    scope: CalendarScope
    color: str = "#3788d8"
    description: Optional[str] = None
    is_visible: bool = True


class CalendarCreate(CalendarBase):
    pass


class CalendarUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None
    is_visible: Optional[bool] = None
    acl: Optional[dict] = None


class CalendarResponse(CalendarBase):
    id: int
    owner_id: int
    acl: dict
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EventBase(BaseModel):
    title: str
    description: Optional[str] = None
    start: datetime
    end: datetime
    all_day: bool = False
    recurrence: Optional[str] = None  # RRULE string
    location: Optional[str] = None
    video_link: Optional[str] = None
    privacy_level: PrivacyLevel = PrivacyLevel.PRIVATE
    timezone: str = "UTC"
    metadata: Optional[dict] = None  # For event type, subtype, etc.


class EventCreate(EventBase):
    calendar_id: int
    attendees: Optional[List[int]] = []  # List of user IDs


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    all_day: Optional[bool] = None
    recurrence: Optional[str] = None
    location: Optional[str] = None
    video_link: Optional[str] = None
    privacy_level: Optional[PrivacyLevel] = None
    timezone: Optional[str] = None
    metadata: Optional[dict] = None


class EventAttendeeResponse(BaseModel):
    id: int
    user_id: int
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    rsvp_status: RSVPStatus
    is_organizer: bool

    class Config:
        from_attributes = True


class EventResponse(EventBase):
    id: int
    calendar_id: int
    creator_id: int
    attachments: List[dict]
    metadata: dict = Field(alias="event_metadata")
    attendees: List[EventAttendeeResponse] = []
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        populate_by_name = True  # Allow both alias and original name


class RSVPRequest(BaseModel):
    status: RSVPStatus


class AvailabilityRequest(BaseModel):
    user_ids: List[int]
    start: datetime
    end: datetime
    duration_minutes: int = 60


class AvailabilitySlot(BaseModel):
    start: datetime
    end: datetime
    available_users: List[int]


class AvailabilityResponse(BaseModel):
    slots: List[AvailabilitySlot]

