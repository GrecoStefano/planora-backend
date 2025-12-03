from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from app.core.database import get_db
from app.core.dependencies import get_current_active_user, require_manager
from app.models.user import User, UserRole
from pydantic import BaseModel
import enum

router = APIRouter(prefix="/collaboration", tags=["collaboration"])


class ApprovalType(str, enum.Enum):
    LEAVE = "leave"
    PERMISSION = "permission"
    APPOINTMENT = "appointment"
    OTHER = "other"


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalRequestCreate(BaseModel):
    type: ApprovalType
    title: str
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    approver_id: int


class ApprovalRequestResponse(BaseModel):
    id: int
    requester_id: int
    approver_id: int
    type: ApprovalType
    title: str
    description: Optional[str] = None
    status: ApprovalStatus
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# In a real implementation, these would be database models
# For now, we'll use a simple in-memory store (replace with DB models)
approval_requests_store = []
delegations_store = []


@router.post("/approvals", response_model=ApprovalRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_approval_request(
    request_data: ApprovalRequestCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create an approval request."""
    # Verify approver exists
    approver_result = await db.execute(select(User).where(User.id == request_data.approver_id))
    approver = approver_result.scalar_one_or_none()
    
    if not approver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approver not found"
        )
    
    # In production, save to database
    approval_request = {
        "id": len(approval_requests_store) + 1,
        "requester_id": current_user.id,
        "approver_id": request_data.approver_id,
        "type": request_data.type,
        "title": request_data.title,
        "description": request_data.description,
        "status": ApprovalStatus.PENDING,
        "start_date": request_data.start_date,
        "end_date": request_data.end_date,
        "created_at": datetime.utcnow(),
    }
    approval_requests_store.append(approval_request)
    
    return ApprovalRequestResponse(**approval_request)


@router.get("/approvals", response_model=List[ApprovalRequestResponse])
async def list_approval_requests(
    status: Optional[ApprovalStatus] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List approval requests (as requester or approver)."""
    requests = [
        r for r in approval_requests_store
        if r["requester_id"] == current_user.id or r["approver_id"] == current_user.id
    ]
    
    if status:
        requests = [r for r in requests if r["status"] == status]
    
    return [ApprovalRequestResponse(**r) for r in requests]


@router.put("/approvals/{approval_id}/approve", response_model=ApprovalRequestResponse)
async def approve_request(
    approval_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve an approval request."""
    request = next((r for r in approval_requests_store if r["id"] == approval_id), None)
    
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval request not found"
        )
    
    if request["approver_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the approver can approve this request"
        )
    
    request["status"] = ApprovalStatus.APPROVED
    return ApprovalRequestResponse(**request)


@router.put("/approvals/{approval_id}/reject", response_model=ApprovalRequestResponse)
async def reject_request(
    approval_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Reject an approval request."""
    request = next((r for r in approval_requests_store if r["id"] == approval_id), None)
    
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval request not found"
        )
    
    if request["approver_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the approver can reject this request"
        )
    
    request["status"] = ApprovalStatus.REJECTED
    return ApprovalRequestResponse(**request)


class DelegationCreate(BaseModel):
    delegate_to_user_id: int
    start_date: datetime
    end_date: datetime
    permissions: List[str] = ["read", "write"]


class DelegationResponse(BaseModel):
    id: int
    delegator_id: int
    delegate_to_user_id: int
    start_date: datetime
    end_date: datetime
    permissions: List[str]
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/delegations", response_model=DelegationResponse, status_code=status.HTTP_201_CREATED)
async def create_delegation(
    delegation_data: DelegationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a delegation."""
    # Verify delegate exists
    delegate_result = await db.execute(select(User).where(User.id == delegation_data.delegate_to_user_id))
    delegate = delegate_result.scalar_one_or_none()
    
    if not delegate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delegate user not found"
        )
    
    delegation = {
        "id": len(delegations_store) + 1,
        "delegator_id": current_user.id,
        "delegate_to_user_id": delegation_data.delegate_to_user_id,
        "start_date": delegation_data.start_date,
        "end_date": delegation_data.end_date,
        "permissions": delegation_data.permissions,
        "created_at": datetime.utcnow(),
    }
    delegations_store.append(delegation)
    
    return DelegationResponse(**delegation)


@router.get("/delegations", response_model=List[DelegationResponse])
async def list_delegations(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List delegations (as delegator or delegate)."""
    delegations = [
        d for d in delegations_store
        if d["delegator_id"] == current_user.id or d["delegate_to_user_id"] == current_user.id
    ]
    
    return [DelegationResponse(**d) for d in delegations]

