from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.calendar import Calendar, CalendarSource
from app.schemas.calendar import (
    CalendarCreate,
    CalendarUpdate,
    CalendarResponse,
)

router = APIRouter(prefix="/calendars", tags=["calendars"])


@router.get("", response_model=List[CalendarResponse])
async def list_calendars(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all calendars accessible by the current user."""
    # Get all calendars and filter in Python to avoid JSON operator issues
    # This is simpler and more reliable for JSON fields
    result = await db.execute(select(Calendar))
    all_calendars = result.scalars().all()
    
    # Filter calendars: owned by user or user is in ACL users array
    accessible_calendars = []
    for cal in all_calendars:
        # Owner has access
        if cal.owner_id == current_user.id:
            accessible_calendars.append(cal)
        # Check if user is in ACL users array
        elif cal.acl and isinstance(cal.acl, dict):
            users = cal.acl.get("users", [])
            if isinstance(users, list) and current_user.id in users:
                accessible_calendars.append(cal)
    
    return accessible_calendars


@router.post("", response_model=CalendarResponse, status_code=status.HTTP_201_CREATED)
async def create_calendar(
    calendar_data: CalendarCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new calendar."""
    new_calendar = Calendar(
        owner_id=current_user.id,
        name=calendar_data.name,
        scope=calendar_data.scope,
        source=calendar_data.source if hasattr(calendar_data, 'source') else CalendarSource.LOCAL,
        color=calendar_data.color,
        description=calendar_data.description,
        is_visible=calendar_data.is_visible,
        acl={"users": [current_user.id], "permissions": {"read": True, "write": True}},
    )
    
    db.add(new_calendar)
    await db.commit()
    await db.refresh(new_calendar)
    
    return new_calendar


@router.get("/{calendar_id}", response_model=CalendarResponse)
async def get_calendar(
    calendar_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific calendar."""
    result = await db.execute(select(Calendar).where(Calendar.id == calendar_id))
    calendar = result.scalar_one_or_none()
    
    if not calendar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar not found"
        )
    
    # Check access
    if calendar.owner_id != current_user.id and current_user.id not in calendar.acl.get("users", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return calendar


@router.put("/{calendar_id}", response_model=CalendarResponse)
async def update_calendar(
    calendar_id: int,
    calendar_data: CalendarUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a calendar."""
    result = await db.execute(select(Calendar).where(Calendar.id == calendar_id))
    calendar = result.scalar_one_or_none()
    
    if not calendar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar not found"
        )
    
    # Check ownership
    if calendar.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can update the calendar"
        )
    
    # Update fields
    update_data = calendar_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(calendar, field, value)
    
    await db.commit()
    await db.refresh(calendar)
    
    return calendar


@router.delete("/{calendar_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_calendar(
    calendar_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a calendar."""
    result = await db.execute(select(Calendar).where(Calendar.id == calendar_id))
    calendar = result.scalar_one_or_none()
    
    if not calendar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar not found"
        )
    
    # Check ownership
    if calendar.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can delete the calendar"
        )
    
    await db.delete(calendar)
    await db.commit()
    
    return None

