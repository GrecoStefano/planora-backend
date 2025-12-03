"""
Base classes for integrations
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.models.integration import Integration, IntegrationStatus


class IntegrationBase(ABC):
    """Base class for all integrations."""
    
    def __init__(self, integration: Integration):
        self.integration = integration
        self.config = integration.config
    
    @abstractmethod
    async def connect(self) -> bool:
        """Test connection to external service."""
        pass
    
    @abstractmethod
    async def sync(self) -> Dict[str, Any]:
        """Perform synchronization."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from external service."""
        pass


class SSOIntegration(IntegrationBase):
    """Base class for SSO integrations."""
    
    @abstractmethod
    async def authenticate(self, token: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with SSO token."""
        pass


class CalendarSyncIntegration(IntegrationBase):
    """Base class for calendar sync integrations."""
    
    @abstractmethod
    async def sync_calendar(self, calendar_id: str) -> Dict[str, Any]:
        """Sync a specific calendar."""
        pass
    
    @abstractmethod
    async def create_event(self, event_data: Dict[str, Any]) -> str:
        """Create event in external calendar."""
        pass
    
    @abstractmethod
    async def update_event(self, event_id: str, event_data: Dict[str, Any]) -> bool:
        """Update event in external calendar."""
        pass


class ChatIntegration(IntegrationBase):
    """Base class for chat integrations (Slack, Teams)."""
    
    @abstractmethod
    async def send_message(self, channel: str, message: str) -> bool:
        """Send message to chat channel."""
        pass
    
    @abstractmethod
    async def handle_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming webhook from chat service."""
        pass


class TicketingIntegration(IntegrationBase):
    """Base class for ticketing integrations (Jira, GitLab, etc.)."""
    
    @abstractmethod
    async def link_task(self, task_id: int, ticket_id: str) -> bool:
        """Link a task to an external ticket."""
        pass
    
    @abstractmethod
    async def create_ticket(self, ticket_data: Dict[str, Any]) -> str:
        """Create ticket in external system."""
        pass


class StorageIntegration(IntegrationBase):
    """Base class for storage integrations."""
    
    @abstractmethod
    async def upload_file(self, file_path: str, destination: str) -> str:
        """Upload file to storage."""
        pass
    
    @abstractmethod
    async def get_file_url(self, file_id: str) -> str:
        """Get public URL for file."""
        pass

