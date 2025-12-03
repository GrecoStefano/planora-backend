from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.dependencies import get_current_active_user, require_manager
from app.models.user import User
from app.models.task import Task, TaskStatus, TaskPriority, TaskAssignee
from app.models.calendar import Event, EventAttendee
from pydantic import BaseModel
from typing import List, Dict

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class PersonalDashboardResponse(BaseModel):
    tasks_by_status: Dict[str, int]
    tasks_by_priority: Dict[str, int]
    upcoming_events: int
    overdue_tasks: int
    total_spent_hours: float


class TeamDashboardResponse(BaseModel):
    team_members: int
    active_tasks: int
    completed_tasks_this_week: int
    average_lead_time: float
    resource_utilization: Dict[str, float]


@router.get("/personal", response_model=PersonalDashboardResponse)
async def get_personal_dashboard(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get personal dashboard metrics."""
    # Tasks by status
    from app.models.task import TaskAssignee
    user_task_ids = select(TaskAssignee.task_id).where(TaskAssignee.user_id == current_user.id)
    tasks_by_status_result = await db.execute(
        select(Task.status, func.count(Task.id))
        .where(Task.id.in_(user_task_ids))
        .group_by(Task.status)
    )
    tasks_by_status = {str(status): count for status, count in tasks_by_status_result.all()}
    
    # Tasks by priority
    tasks_by_priority_result = await db.execute(
        select(Task.priority, func.count(Task.id))
        .where(Task.id.in_(user_task_ids))
        .group_by(Task.priority)
    )
    tasks_by_priority = {str(priority): count for priority, count in tasks_by_priority_result.all()}
    
    # Upcoming events (next 7 days)
    next_week = datetime.utcnow() + timedelta(days=7)
    upcoming_events_result = await db.execute(
        select(func.count(Event.id))
        .join(EventAttendee)
        .where(
            and_(
                EventAttendee.user_id == current_user.id,
                Event.start >= datetime.utcnow(),
                Event.start <= next_week
            )
        )
    )
    upcoming_events = upcoming_events_result.scalar() or 0
    
    # Overdue tasks
    overdue_tasks_result = await db.execute(
        select(func.count(Task.id))
        .join(TaskAssignee)
        .where(
            and_(
                TaskAssignee.user_id == current_user.id,
                Task.due_date < datetime.utcnow(),
                Task.status != TaskStatus.DONE
            )
        )
    )
    overdue_tasks = overdue_tasks_result.scalar() or 0
    
    # Total spent hours
    total_spent_result = await db.execute(
        select(func.sum(Task.spent))
        .where(Task.id.in_(user_task_ids))
    )
    total_spent_hours = total_spent_result.scalar() or 0.0
    
    return PersonalDashboardResponse(
        tasks_by_status=tasks_by_status,
        tasks_by_priority=tasks_by_priority,
        upcoming_events=upcoming_events,
        overdue_tasks=overdue_tasks,
        total_spent_hours=float(total_spent_hours),
    )


@router.get("/team", response_model=TeamDashboardResponse)
async def get_team_dashboard(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get team dashboard metrics (manager/admin only)."""
    # This is a simplified version - in production, filter by actual team
    from app.models.task import TaskAssignee
    
    # Team members (users in same team)
    team_members_result = await db.execute(
        select(func.count(User.id))
        .where(User.team == current_user.team)
    )
    team_members = team_members_result.scalar() or 0
    
    # Active tasks
    active_tasks_result = await db.execute(
        select(func.count(Task.id))
        .where(Task.status != TaskStatus.DONE)
    )
    active_tasks = active_tasks_result.scalar() or 0
    
    # Completed tasks this week
    week_ago = datetime.utcnow() - timedelta(days=7)
    completed_this_week_result = await db.execute(
        select(func.count(Task.id))
        .where(
            and_(
                Task.status == TaskStatus.DONE,
                Task.updated_at >= week_ago
            )
        )
    )
    completed_tasks_this_week = completed_this_week_result.scalar() or 0
    
    return TeamDashboardResponse(
        team_members=team_members,
        active_tasks=active_tasks,
        completed_tasks_this_week=completed_tasks_this_week,
        average_lead_time=0.0,  # Would calculate from task creation to completion
        resource_utilization={},  # Would calculate from events/resources
    )

