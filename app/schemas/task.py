from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.task import TaskStatus, TaskPriority


class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[datetime] = None
    estimate: Optional[float] = None
    recurrence: Optional[str] = None  # RRULE string


class TaskCreate(TaskBase):
    project_id: Optional[int] = None
    parent_id: Optional[int] = None
    assignee_ids: Optional[List[int]] = []
    tag_names: Optional[List[str]] = []


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None
    estimate: Optional[float] = None
    spent: Optional[float] = None
    recurrence: Optional[str] = None
    project_id: Optional[int] = None
    parent_id: Optional[int] = None


class TaskAssigneeResponse(BaseModel):
    id: int
    user_id: int
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    role: str

    class Config:
        from_attributes = True


class TaskCommentResponse(BaseModel):
    id: int
    user_id: int
    user_name: Optional[str] = None
    content: str
    mentions: List[int]
    created_at: datetime

    class Config:
        from_attributes = True


class TaskResponse(TaskBase):
    id: int
    project_id: Optional[int]
    parent_id: Optional[int]
    spent: float
    tags: List[str]
    attachments: List[dict]
    assignees: List[TaskAssigneeResponse] = []
    comments: List[TaskCommentResponse] = []
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TaskCommentCreate(BaseModel):
    content: str
    mentions: Optional[List[int]] = []


class TimeTrackingRequest(BaseModel):
    hours: float
    description: Optional[str] = None

