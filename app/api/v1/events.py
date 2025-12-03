from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from datetime import datetime
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.calendar import Calendar, Event, EventAttendee, RSVPStatus
from app.schemas.calendar import (
    EventCreate,
    EventUpdate,
    EventResponse,
    EventAttendeeResponse,
    RSVPRequest,
)

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=List[EventResponse])
async def list_events(
    calendar_id: Optional[int] = Query(None),
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List events with optional filters."""
    query = select(Event)
    
    # Filter by calendar if provided
    if calendar_id:
        query = query.where(Event.calendar_id == calendar_id)
    
    # Filter by date range
    if start:
        query = query.where(Event.end >= start)
    if end:
        query = query.where(Event.start <= end)
    
    # Only show events from calendars user has access to
    # This is simplified - in production, check ACL properly
    result = await db.execute(query)
    events = result.scalars().all()
    
    # Load attendees for each event
    event_list = []
    for event in events:
        attendee_result = await db.execute(
            select(EventAttendee).where(EventAttendee.event_id == event.id)
        )
        attendees = attendee_result.scalars().all()
        
        attendee_responses = []
        for attendee in attendees:
            user_result = await db.execute(
                select(User).where(User.id == attendee.user_id)
            )
            user = user_result.scalar_one_or_none()
            attendee_responses.append(
                EventAttendeeResponse(
                    id=attendee.id,
                    user_id=attendee.user_id,
                    user_name=user.full_name if user else None,
                    user_email=user.email if user else None,
                    rsvp_status=attendee.rsvp_status,
                    is_organizer=attendee.is_organizer,
                )
            )
        
        event_dict = EventResponse.model_validate(event)
        event_dict.attendees = attendee_responses
        event_list.append(event_dict)
    
    return event_list


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_data: EventCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new event."""
    # Verify calendar exists and user has access
    calendar_result = await db.execute(
        select(Calendar).where(Calendar.id == event_data.calendar_id)
    )
    calendar = calendar_result.scalar_one_or_none()
    
    if not calendar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar not found"
        )
    
    if calendar.owner_id != current_user.id and current_user.id not in calendar.acl.get("users", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to calendar"
        )
    
    # Create event
    new_event = Event(
        calendar_id=event_data.calendar_id,
        creator_id=current_user.id,
        title=event_data.title,
        description=event_data.description,
        start=event_data.start,
        end=event_data.end,
        all_day=event_data.all_day,
        recurrence=event_data.recurrence,
        location=event_data.location,
        video_link=event_data.video_link,
        privacy_level=event_data.privacy_level,
        timezone=event_data.timezone,
        attachments=[],
    )
    
    db.add(new_event)
    await db.commit()
    await db.refresh(new_event)
    
    # Add attendees
    if event_data.attendees:
        for user_id in event_data.attendees:
            attendee = EventAttendee(
                event_id=new_event.id,
                user_id=user_id,
                rsvp_status=RSVPStatus.PENDING,
                is_organizer=(user_id == current_user.id),
            )
            db.add(attendee)
    
    # Add creator as attendee if not already included
    if current_user.id not in (event_data.attendees or []):
        creator_attendee = EventAttendee(
            event_id=new_event.id,
            user_id=current_user.id,
            rsvp_status=RSVPStatus.ACCEPTED,
            is_organizer=True,
        )
        db.add(creator_attendee)
    
    await db.commit()
    await db.refresh(new_event)
    
    # Load attendees for response
    attendee_result = await db.execute(
        select(EventAttendee).where(EventAttendee.event_id == new_event.id)
    )
    attendees = attendee_result.scalars().all()
    
    attendee_responses = []
    for attendee in attendees:
        user_result = await db.execute(
            select(User).where(User.id == attendee.user_id)
        )
        user = user_result.scalar_one_or_none()
        attendee_responses.append(
            EventAttendeeResponse(
                id=attendee.id,
                user_id=attendee.user_id,
                user_name=user.full_name if user else None,
                user_email=user.email if user else None,
                rsvp_status=attendee.rsvp_status,
                is_organizer=attendee.is_organizer,
            )
        )
    
    event_response = EventResponse.model_validate(new_event)
    event_response.attendees = attendee_responses
    return event_response


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific event."""
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # Check access via calendar
    calendar_result = await db.execute(
        select(Calendar).where(Calendar.id == event.calendar_id)
    )
    calendar = calendar_result.scalar_one_or_none()
    
    if calendar.owner_id != current_user.id and current_user.id not in calendar.acl.get("users", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Load attendees
    attendee_result = await db.execute(
        select(EventAttendee).where(EventAttendee.event_id == event.id)
    )
    attendees = attendee_result.scalars().all()
    
    attendee_responses = []
    for attendee in attendees:
        user_result = await db.execute(
            select(User).where(User.id == attendee.user_id)
        )
        user = user_result.scalar_one_or_none()
        attendee_responses.append(
            EventAttendeeResponse(
                id=attendee.id,
                user_id=attendee.user_id,
                user_name=user.full_name if user else None,
                user_email=user.email if user else None,
                rsvp_status=attendee.rsvp_status,
                is_organizer=attendee.is_organizer,
            )
        )
    
    event_response = EventResponse.model_validate(event)
    event_response.attendees = attendee_responses
    return event_response


@router.put("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: int,
    event_data: EventUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an event."""
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # Check if user is creator or has write access to calendar
    if event.creator_id != current_user.id:
        calendar_result = await db.execute(
            select(Calendar).where(Calendar.id == event.calendar_id)
        )
        calendar = calendar_result.scalar_one_or_none()
        if calendar.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the creator can update the event"
            )
    
    # Update fields
    update_data = event_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)
    
    await db.commit()
    await db.refresh(event)
    
    # Load attendees
    attendee_result = await db.execute(
        select(EventAttendee).where(EventAttendee.event_id == event.id)
    )
    attendees = attendee_result.scalars().all()
    
    attendee_responses = []
    for attendee in attendees:
        user_result = await db.execute(
            select(User).where(User.id == attendee.user_id)
        )
        user = user_result.scalar_one_or_none()
        attendee_responses.append(
            EventAttendeeResponse(
                id=attendee.id,
                user_id=attendee.user_id,
                user_name=user.full_name if user else None,
                user_email=user.email if user else None,
                rsvp_status=attendee.rsvp_status,
                is_organizer=attendee.is_organizer,
            )
        )
    
    event_response = EventResponse.model_validate(event)
    event_response.attendees = attendee_responses
    return event_response


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an event."""
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # Check if user is creator
    if event.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator can delete the event"
        )
    
    await db.delete(event)
    await db.commit()
    
    return None


@router.put("/{event_id}/rsvp", response_model=EventAttendeeResponse)
async def update_rsvp(
    event_id: int,
    rsvp_data: RSVPRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update RSVP status for current user."""
    # Find attendee record
    result = await db.execute(
        select(EventAttendee).where(
            and_(
                EventAttendee.event_id == event_id,
                EventAttendee.user_id == current_user.id
            )
        )
    )
    attendee = result.scalar_one_or_none()
    
    if not attendee:
        # Create new attendee record if doesn't exist
        attendee = EventAttendee(
            event_id=event_id,
            user_id=current_user.id,
            rsvp_status=rsvp_data.status,
            is_organizer=False,
        )
        db.add(attendee)
    else:
        attendee.rsvp_status = rsvp_data.status
    
    await db.commit()
    await db.refresh(attendee)
    
    return EventAttendeeResponse(
        id=attendee.id,
        user_id=attendee.user_id,
        user_name=current_user.full_name,
        user_email=current_user.email,
        rsvp_status=attendee.rsvp_status,
        is_organizer=attendee.is_organizer,
    )

