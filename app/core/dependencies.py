from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current authenticated user from JWT token."""
    import logging
    logger = logging.getLogger(__name__)
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        logger.warning("Nessun token ricevuto")
        raise credentials_exception
    
    logger.info(f"Token ricevuto (primi 50 caratteri): {token[:50]}...")
    logger.info(f"Lunghezza token: {len(token)}")
    
    payload = decode_access_token(token)
    if payload is None:
        logger.warning("Token decodificazione fallita - verificare SECRET_KEY e formato token")
        raise credentials_exception
    
    logger.info(f"Payload decodificato: {payload}")
    
    user_id_raw = payload.get("sub")
    if user_id_raw is None:
        logger.warning("user_id non trovato nel payload")
        raise credentials_exception
    
    # Convert to int if it's a string (JWT standard allows both)
    user_id: int = int(user_id_raw) if isinstance(user_id_raw, str) else user_id_raw
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        logger.warning(f"Utente con id {user_id} non trovato")
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive"
        )
    return current_user


def require_role(allowed_roles: list[UserRole]):
    """Dependency factory for role-based access control."""
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return role_checker


# Common role dependencies
require_admin = require_role([UserRole.ADMIN])
require_manager = require_role([UserRole.MANAGER, UserRole.ADMIN])
require_user = require_role([UserRole.USER, UserRole.MANAGER, UserRole.ADMIN])

