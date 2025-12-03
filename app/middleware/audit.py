"""
Audit logging middleware
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models.audit import AuditLog, AuditAction
from app.core.security import decode_access_token
import json
import time


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware to log all API requests for audit purposes."""
    
    async def dispatch(self, request: Request, call_next):
        # Skip audit for health checks and static files
        if request.url.path in ["/health", "/", "/api/docs", "/api/openapi.json"]:
            return await call_next(request)
        
        start_time = time.time()
        
        # Get user from token if available
        user_id = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            payload = decode_access_token(token)
            if payload:
                user_id = payload.get("sub")
        
        # Process request
        response = await call_next(request)
        
        # Determine action type from method and path
        action = self._determine_action(request.method, request.url.path)
        
        # Log audit entry for write operations
        if request.method in ["POST", "PUT", "PATCH", "DELETE"] and user_id:
            try:
                from app.core.database import AsyncSessionLocal
                async with AsyncSessionLocal() as db:
                    # Extract entity info from path
                    entity_type, entity_id = self._extract_entity_info(request.url.path)
                    
                    if entity_type:
                        audit_log = AuditLog(
                            entity_type=entity_type,
                            entity_id=entity_id or 0,
                            action=action,
                            user_id=user_id,
                            diff={},
                            ip_address=request.client.host if request.client else None,
                            user_agent=request.headers.get("user-agent"),
                        )
                        db.add(audit_log)
                        await db.commit()
            except Exception as e:
                # Don't fail request if audit logging fails
                import logging
                logging.error(f"Audit logging error: {e}")
        
        return response
    
    def _determine_action(self, method: str, path: str) -> AuditAction:
        """Determine audit action from HTTP method."""
        if method == "POST":
            return AuditAction.CREATE
        elif method in ["PUT", "PATCH"]:
            return AuditAction.UPDATE
        elif method == "DELETE":
            return AuditAction.DELETE
        elif method == "GET":
            return AuditAction.VIEW
        return AuditAction.VIEW
    
    def _extract_entity_info(self, path: str) -> tuple[str | None, int | None]:
        """Extract entity type and ID from URL path."""
        parts = path.split("/")
        entity_id = None
        
        # Look for common patterns like /api/v1/events/123
        if len(parts) >= 4:
            entity_type = parts[3]  # events, tasks, calendars, etc.
            if len(parts) > 4 and parts[4].isdigit():
                entity_id = int(parts[4])
            return entity_type, entity_id
        
        return None, None

