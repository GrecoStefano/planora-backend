from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.project import Project
from pydantic import BaseModel

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectBase(BaseModel):
    name: str
    description: str | None = None
    color: str = "#808080"


class ProjectCreate(ProjectBase):
    team_id: str | None = None


class ProjectResponse(ProjectBase):
    id: int
    owner_id: int
    team_id: str | None
    is_active: bool
    created_at: str

    class Config:
        from_attributes = True


@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all projects accessible by the current user."""
    result = await db.execute(
        select(Project).where(
            (Project.owner_id == current_user.id) |
            (Project.team_id == current_user.team)
        )
    )
    projects = result.scalars().all()
    return projects


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new project."""
    new_project = Project(
        name=project_data.name,
        description=project_data.description,
        owner_id=current_user.id,
        team_id=project_data.team_id or current_user.team,
        color=project_data.color,
        acl={"users": [current_user.id], "permissions": {"read": True, "write": True}},
    )
    
    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)
    
    return new_project

