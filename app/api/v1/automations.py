from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.automation import AutomationRule
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/automations", tags=["automations"])


class AutomationRuleCreate(BaseModel):
    name: str
    description: str | None = None
    trigger: str
    conditions: dict
    actions: List[dict]
    is_active: bool = True


class AutomationRuleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    trigger: str | None = None
    conditions: dict | None = None
    actions: List[dict] | None = None
    is_active: bool | None = None


class AutomationRuleResponse(BaseModel):
    id: int
    name: str
    description: str | None
    trigger: str
    conditions: dict
    actions: List[dict]
    is_active: bool
    created_by: int
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


@router.get("", response_model=List[AutomationRuleResponse])
async def list_automation_rules(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all automation rules."""
    result = await db.execute(select(AutomationRule))
    rules = result.scalars().all()
    return rules


@router.post("", response_model=AutomationRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_automation_rule(
    rule_data: AutomationRuleCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new automation rule."""
    new_rule = AutomationRule(
        name=rule_data.name,
        description=rule_data.description,
        trigger=rule_data.trigger,
        conditions=rule_data.conditions,
        actions=rule_data.actions,
        is_active=rule_data.is_active,
        created_by=current_user.id,
    )
    
    db.add(new_rule)
    await db.commit()
    await db.refresh(new_rule)
    
    return new_rule


@router.get("/{rule_id}", response_model=AutomationRuleResponse)
async def get_automation_rule(
    rule_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific automation rule."""
    result = await db.execute(select(AutomationRule).where(AutomationRule.id == rule_id))
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Automation rule not found"
        )
    
    return rule


@router.put("/{rule_id}", response_model=AutomationRuleResponse)
async def update_automation_rule(
    rule_id: int,
    rule_data: AutomationRuleUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an automation rule."""
    result = await db.execute(select(AutomationRule).where(AutomationRule.id == rule_id))
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Automation rule not found"
        )
    
    if rule.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator can update this rule"
        )
    
    update_data = rule_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)
    
    await db.commit()
    await db.refresh(rule)
    
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_automation_rule(
    rule_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an automation rule."""
    result = await db.execute(select(AutomationRule).where(AutomationRule.id == rule_id))
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Automation rule not found"
        )
    
    if rule.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator can delete this rule"
        )
    
    await db.delete(rule)
    await db.commit()
    
    return None

