from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.dependencies import get_current_active_user, require_admin
from app.models.user import User
from app.models.integration import Integration, IntegrationType, IntegrationStatus
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/integrations", tags=["integrations"])


class IntegrationCreate(BaseModel):
    type: IntegrationType
    name: str
    config: dict
    is_active: bool = False


class IntegrationUpdate(BaseModel):
    name: str | None = None
    config: dict | None = None
    is_active: bool | None = None


class IntegrationResponse(BaseModel):
    id: int
    type: IntegrationType
    name: str
    config: dict
    status: IntegrationStatus
    last_sync: datetime | None
    error_message: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


@router.get("", response_model=List[IntegrationResponse])
async def list_integrations(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all integrations (admin only)."""
    result = await db.execute(select(Integration))
    integrations = result.scalars().all()
    return integrations


@router.post("", response_model=IntegrationResponse, status_code=status.HTTP_201_CREATED)
async def create_integration(
    integration_data: IntegrationCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new integration (admin only)."""
    new_integration = Integration(
        type=integration_data.type,
        name=integration_data.name,
        config=integration_data.config,
        status=IntegrationStatus.PENDING,
        is_active=integration_data.is_active,
    )
    
    db.add(new_integration)
    await db.commit()
    await db.refresh(new_integration)
    
    return new_integration


@router.post("/{integration_id}/sync")
async def sync_integration(
    integration_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Trigger sync for an integration."""
    result = await db.execute(select(Integration).where(Integration.id == integration_id))
    integration = result.scalar_one_or_none()
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )
    
    # Import and use appropriate integration class
    # This is a simplified version
    try:
        # Sync logic would go here
        integration.status = IntegrationStatus.ACTIVE
        integration.last_sync = datetime.utcnow()
        await db.commit()
        
        return {"status": "success", "message": "Sync completed"}
    except Exception as e:
        integration.status = IntegrationStatus.ERROR
        integration.error_message = str(e)
        await db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {str(e)}"
        )

