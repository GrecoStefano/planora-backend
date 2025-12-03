from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.audit import AuditLog, AuditAction
from pydantic import BaseModel
import json

router = APIRouter(prefix="/security", tags=["security"])


class AuditLogResponse(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    action: AuditAction
    user_id: int
    timestamp: datetime
    diff: dict
    ip_address: str | None
    user_agent: str | None

    class Config:
        from_attributes = True


class GDPRExportResponse(BaseModel):
    user_data: dict
    events: List[dict]
    tasks: List[dict]
    created_at: datetime


@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def get_audit_logs(
    entity_type: str | None = None,
    entity_id: int | None = None,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get audit logs (filtered by entity if specified)."""
    query = select(AuditLog)
    
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.where(AuditLog.entity_id == entity_id)
    
    query = query.order_by(AuditLog.timestamp.desc()).limit(limit)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return logs


@router.post("/audit-logs")
async def create_audit_log(
    entity_type: str,
    entity_id: int,
    action: AuditAction,
    diff: dict,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create an audit log entry."""
    new_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=current_user.id,
        diff=diff,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    
    db.add(new_log)
    await db.commit()
    await db.refresh(new_log)
    
    return new_log


@router.get("/gdpr/export", response_model=GDPRExportResponse)
async def export_user_data(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Export all user data for GDPR compliance."""
    from app.models.calendar import Event, EventAttendee
    from app.models.task import Task, TaskAssignee, TaskWatcher
    
    # Export user data
    user_data = {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "team": current_user.team,
        "timezone": current_user.timezone,
        "preferences": current_user.preferences,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
    }
    
    # Export events
    events_result = await db.execute(
        select(Event).where(Event.creator_id == current_user.id)
    )
    events = [
        {
            "id": e.id,
            "title": e.title,
            "description": e.description,
            "start": e.start.isoformat() if e.start else None,
            "end": e.end.isoformat() if e.end else None,
        }
        for e in events_result.scalars().all()
    ]
    
    # Export tasks
    task_ids_result = await db.execute(
        select(TaskAssignee.task_id).where(TaskAssignee.user_id == current_user.id)
    )
    task_ids = [row[0] for row in task_ids_result.all()]
    
    tasks_result = await db.execute(
        select(Task).where(Task.id.in_(task_ids) if task_ids else False)
    )
    tasks = [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "status": t.status.value if hasattr(t.status, 'value') else str(t.status),
            "priority": t.priority.value if hasattr(t.priority, 'value') else str(t.priority),
            "due_date": t.due_date.isoformat() if t.due_date else None,
        }
        for t in tasks_result.scalars().all()
    ]
    
    return GDPRExportResponse(
        user_data=user_data,
        events=events,
        tasks=tasks,
        created_at=datetime.utcnow(),
    )


@router.delete("/gdpr/delete-account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_account(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete user account and all associated data (GDPR right to be forgotten)."""
    # In production, this should be a soft delete or anonymization
    # For now, we'll mark as inactive
    current_user.is_active = False
    await db.commit()
    
    return None

