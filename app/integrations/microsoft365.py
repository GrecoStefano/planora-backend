"""
Microsoft 365 Integration
"""
from app.integrations.base import CalendarSyncIntegration, SSOIntegration
from app.models.integration import Integration
from typing import Dict, Any, Optional
import httpx


class Microsoft365CalendarSync(CalendarSyncIntegration):
    """Microsoft 365 Calendar Sync."""
    
    async def connect(self) -> bool:
        """Test connection to Microsoft Graph API."""
        try:
            access_token = self.config.get("access_token")
            if not access_token:
                return False
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                return response.status_code == 200
        except Exception:
            return False
    
    async def sync_calendar(self, calendar_id: str) -> Dict[str, Any]:
        """Sync calendar from Microsoft 365."""
        access_token = self.config.get("access_token")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://graph.microsoft.com/v1.0/me/calendars/{calendar_id}/events",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            return response.json()
    
    async def create_event(self, event_data: Dict[str, Any]) -> str:
        """Create event in Microsoft 365."""
        access_token = self.config.get("access_token")
        calendar_id = self.config.get("calendar_id", "calendar")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://graph.microsoft.com/v1.0/me/calendars/{calendar_id}/events",
                headers={"Authorization": f"Bearer {access_token}"},
                json=event_data,
            )
            result = response.json()
            return result.get("id", "")
    
    async def update_event(self, event_id: str, event_data: Dict[str, Any]) -> bool:
        """Update event in Microsoft 365."""
        access_token = self.config.get("access_token")
        
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"https://graph.microsoft.com/v1.0/me/events/{event_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                json=event_data,
            )
            return response.status_code == 200
    
    async def sync(self) -> Dict[str, Any]:
        """Perform full sync."""
        if not await self.connect():
            return {"status": "error", "message": "Connection failed"}
        
        # Sync logic here
        return {"status": "success", "synced": 0}


class Microsoft365SSO(SSOIntegration):
    """Microsoft 365 SSO."""
    
    async def connect(self) -> bool:
        return True  # SSO doesn't need persistent connection
    
    async def authenticate(self, token: str) -> Optional[Dict[str, Any]]:
        """Authenticate with Azure AD token."""
        client_id = self.config.get("client_id")
        client_secret = self.config.get("client_secret")
        tenant_id = self.config.get("tenant_id")
        
        # Verify token with Azure AD
        # Implementation would verify JWT token
        return None
    
    async def sync(self) -> Dict[str, Any]:
        return {"status": "success"}
    
    async def disconnect(self) -> bool:
        return True

