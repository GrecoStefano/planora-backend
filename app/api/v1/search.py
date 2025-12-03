from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func, text
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.task import Task
from app.models.calendar import Event
from pydantic import BaseModel

router = APIRouter(prefix="/search", tags=["search"])


class SearchResult(BaseModel):
    type: str  # "task" or "event"
    id: int
    title: str
    description: Optional[str] = None
    score: Optional[float] = None


class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int


@router.get("", response_model=SearchResponse)
async def search(
    q: str = Query(..., description="Search query"),
    type: Optional[str] = Query(None, description="Filter by type: task, event, or all"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Full-text search across tasks and events."""
    results = []
    
    # Search tasks
    if not type or type == "task" or type == "all":
        # Using PostgreSQL full-text search
        task_query = select(Task).where(
            or_(
                Task.title.ilike(f"%{q}%"),
                Task.description.ilike(f"%{q}%"),
                # Full-text search with tsvector (if configured)
                func.to_tsvector('italian', func.coalesce(Task.title, '') + ' ' + func.coalesce(Task.description, '')).match(func.plainto_tsquery('italian', q))
            )
        )
        
        task_result = await db.execute(task_query)
        tasks = task_result.scalars().all()
        
        for task in tasks:
            results.append(SearchResult(
                type="task",
                id=task.id,
                title=task.title,
                description=task.description,
            ))
    
    # Search events
    if not type or type == "event" or type == "all":
        event_query = select(Event).where(
            or_(
                Event.title.ilike(f"%{q}%"),
                Event.description.ilike(f"%{q}%"),
            )
        )
        
        event_result = await db.execute(event_query)
        events = event_result.scalars().all()
        
        for event in events:
            results.append(SearchResult(
                type="event",
                id=event.id,
                title=event.title,
                description=event.description,
            ))
    
    return SearchResponse(results=results, total=len(results))

