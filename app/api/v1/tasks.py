from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from datetime import datetime
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.task import (
    Task,
    TaskAssignee,
    TaskWatcher,
    TaskDependency,
    TaskTag,
    Tag,
    TaskComment,
    TaskStatus,
    TaskPriority,
)
from app.models.project import Project
from app.schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskAssigneeResponse,
    TaskCommentCreate,
    TaskCommentResponse,
    TimeTrackingRequest,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    project_id: Optional[int] = Query(None),
    status: Optional[TaskStatus] = Query(None),
    priority: Optional[TaskPriority] = Query(None),
    assignee_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List tasks with optional filters."""
    query = select(Task)
    
    if project_id:
        query = query.where(Task.project_id == project_id)
    if status:
        query = query.where(Task.status == status)
    if priority:
        query = query.where(Task.priority == priority)
    if assignee_id:
        # Filter by assignee
        assignee_query = select(TaskAssignee.task_id).where(TaskAssignee.user_id == assignee_id)
        query = query.where(Task.id.in_(assignee_query))
    
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    # Load related data for each task
    task_list = []
    for task in tasks:
        # Load assignees
        assignee_result = await db.execute(
            select(TaskAssignee).where(TaskAssignee.task_id == task.id)
        )
        assignees = assignee_result.scalars().all()
        
        assignee_responses = []
        for assignee in assignees:
            user_result = await db.execute(
                select(User).where(User.id == assignee.user_id)
            )
            user = user_result.scalar_one_or_none()
            assignee_responses.append(
                TaskAssigneeResponse(
                    id=assignee.id,
                    user_id=assignee.user_id,
                    user_name=user.full_name if user else None,
                    user_email=user.email if user else None,
                    role=assignee.role,
                )
            )
        
        # Load comments
        comment_result = await db.execute(
            select(TaskComment).where(TaskComment.task_id == task.id)
        )
        comments = comment_result.scalars().all()
        
        comment_responses = []
        for comment in comments:
            user_result = await db.execute(
                select(User).where(User.id == comment.user_id)
            )
            user = user_result.scalar_one_or_none()
            comment_responses.append(
                TaskCommentResponse(
                    id=comment.id,
                    user_id=comment.user_id,
                    user_name=user.full_name if user else None,
                    content=comment.content,
                    mentions=comment.mentions,
                    created_at=comment.created_at,
                )
            )
        
        task_dict = TaskResponse.model_validate(task)
        task_dict.assignees = assignee_responses
        task_dict.comments = comment_responses
        task_list.append(task_dict)
    
    return task_list


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new task."""
    # Verify project if provided
    if task_data.project_id:
        project_result = await db.execute(
            select(Project).where(Project.id == task_data.project_id)
        )
        project = project_result.scalar_one_or_none()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
    
    # Create task
    new_task = Task(
        project_id=task_data.project_id,
        parent_id=task_data.parent_id,
        title=task_data.title,
        description=task_data.description,
        status=task_data.status,
        priority=task_data.priority,
        due_date=task_data.due_date,
        estimate=task_data.estimate,
        recurrence=task_data.recurrence,
        tags=task_data.tag_names or [],
        attachments=[],
        metadata={},
    )
    
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    
    # Add assignees
    if task_data.assignee_ids:
        for user_id in task_data.assignee_ids:
            assignee = TaskAssignee(
                task_id=new_task.id,
                user_id=user_id,
                role="assignee",
            )
            db.add(assignee)
    
    # Add tags
    if task_data.tag_names:
        for tag_name in task_data.tag_names:
            # Find or create tag
            tag_result = await db.execute(
                select(Tag).where(Tag.name == tag_name)
            )
            tag = tag_result.scalar_one_or_none()
            
            if not tag:
                tag = Tag(name=tag_name, color="#808080")
                db.add(tag)
                await db.flush()
            
            task_tag = TaskTag(task_id=new_task.id, tag_id=tag.id)
            db.add(task_tag)
    
    await db.commit()
    await db.refresh(new_task)
    
    # Load assignees and comments for response
    assignee_result = await db.execute(
        select(TaskAssignee).where(TaskAssignee.task_id == new_task.id)
    )
    assignees = assignee_result.scalars().all()
    
    assignee_responses = []
    for assignee in assignees:
        user_result = await db.execute(
            select(User).where(User.id == assignee.user_id)
        )
        user = user_result.scalar_one_or_none()
        assignee_responses.append(
            TaskAssigneeResponse(
                id=assignee.id,
                user_id=assignee.user_id,
                user_name=user.full_name if user else None,
                user_email=user.email if user else None,
                role=assignee.role,
            )
        )
    
    task_response = TaskResponse.model_validate(new_task)
    task_response.assignees = assignee_responses
    task_response.comments = []
    return task_response


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific task."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Load assignees
    assignee_result = await db.execute(
        select(TaskAssignee).where(TaskAssignee.task_id == task.id)
    )
    assignees = assignee_result.scalars().all()
    
    assignee_responses = []
    for assignee in assignees:
        user_result = await db.execute(
            select(User).where(User.id == assignee.user_id)
        )
        user = user_result.scalar_one_or_none()
        assignee_responses.append(
            TaskAssigneeResponse(
                id=assignee.id,
                user_id=assignee.user_id,
                user_name=user.full_name if user else None,
                user_email=user.email if user else None,
                role=assignee.role,
            )
        )
    
    # Load comments
    comment_result = await db.execute(
        select(TaskComment).where(TaskComment.task_id == task.id)
    )
    comments = comment_result.scalars().all()
    
    comment_responses = []
    for comment in comments:
        user_result = await db.execute(
            select(User).where(User.id == comment.user_id)
        )
        user = user_result.scalar_one_or_none()
        comment_responses.append(
            TaskCommentResponse(
                id=comment.id,
                user_id=comment.user_id,
                user_name=user.full_name if user else None,
                content=comment.content,
                mentions=comment.mentions,
                created_at=comment.created_at,
            )
        )
    
    task_response = TaskResponse.model_validate(task)
    task_response.assignees = assignee_responses
    task_response.comments = comment_responses
    return task_response


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a task."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Update fields
    update_data = task_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    
    await db.commit()
    await db.refresh(task)
    
    # Load assignees and comments
    assignee_result = await db.execute(
        select(TaskAssignee).where(TaskAssignee.task_id == task.id)
    )
    assignees = assignee_result.scalars().all()
    
    assignee_responses = []
    for assignee in assignees:
        user_result = await db.execute(
            select(User).where(User.id == assignee.user_id)
        )
        user = user_result.scalar_one_or_none()
        assignee_responses.append(
            TaskAssigneeResponse(
                id=assignee.id,
                user_id=assignee.user_id,
                user_name=user.full_name if user else None,
                user_email=user.email if user else None,
                role=assignee.role,
            )
        )
    
    comment_result = await db.execute(
        select(TaskComment).where(TaskComment.task_id == task.id)
    )
    comments = comment_result.scalars().all()
    
    comment_responses = []
    for comment in comments:
        user_result = await db.execute(
            select(User).where(User.id == comment.user_id)
        )
        user = user_result.scalar_one_or_none()
        comment_responses.append(
            TaskCommentResponse(
                id=comment.id,
                user_id=comment.user_id,
                user_name=user.full_name if user else None,
                content=comment.content,
                mentions=comment.mentions,
                created_at=comment.created_at,
            )
        )
    
    task_response = TaskResponse.model_validate(task)
    task_response.assignees = assignee_responses
    task_response.comments = comment_responses
    return task_response


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a task."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    await db.delete(task)
    await db.commit()
    
    return None


@router.post("/{task_id}/comments", response_model=TaskCommentResponse)
async def add_comment(
    task_id: int,
    comment_data: TaskCommentCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a comment to a task."""
    # Verify task exists
    task_result = await db.execute(select(Task).where(Task.id == task_id))
    task = task_result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Create comment
    new_comment = TaskComment(
        task_id=task_id,
        user_id=current_user.id,
        content=comment_data.content,
        mentions=comment_data.mentions or [],
    )
    
    db.add(new_comment)
    await db.commit()
    await db.refresh(new_comment)
    
    return TaskCommentResponse(
        id=new_comment.id,
        user_id=new_comment.user_id,
        user_name=current_user.full_name,
        content=new_comment.content,
        mentions=new_comment.mentions,
        created_at=new_comment.created_at,
    )


@router.post("/{task_id}/time-tracking")
async def track_time(
    task_id: int,
    time_data: TimeTrackingRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Track time spent on a task."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Update spent time
    task.spent = (task.spent or 0) + time_data.hours
    
    await db.commit()
    await db.refresh(task)
    
    return {"message": "Time tracked successfully", "total_spent": task.spent}

