from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
import hashlib
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    # Try direct verification first
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except ValueError:
        # If password was pre-hashed (longer than 72 bytes), hash it first
        if len(plain_password.encode('utf-8')) > 72:
            pre_hashed = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
            return pwd_context.verify(pre_hashed, hashed_password)
        raise


def get_password_hash(password: str) -> str:
    """Hash a password. Bcrypt has a 72 byte limit, so we hash with SHA256 first if needed."""
    # Bcrypt has a 72 byte limit. If password is longer, hash it first with SHA256
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        # Hash with SHA256 first to get a fixed 64-char hex string (32 bytes)
        password = hashlib.sha256(password_bytes).hexdigest()
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    import logging
    logger = logging.getLogger(__name__)
    
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    logger.info(f"Creazione token con data: {to_encode}, SECRET_KEY: {settings.SECRET_KEY[:20]}..., ALGORITHM: {settings.ALGORITHM}")
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    logger.info(f"Token creato (primi 50 caratteri): {encoded_jwt[:50]}...")
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT token."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Tentativo di decodifica token con SECRET_KEY: {settings.SECRET_KEY[:20]}...")
        logger.info(f"ALGORITHM: {settings.ALGORITHM}")
        
        # Try to decode without verification first (for debugging)
        try:
            unverified = jwt.decode(token, options={"verify_signature": False})
            logger.info(f"Token decodificato senza verifica: {unverified}")
        except Exception as e:
            logger.error(f"Errore nella decodifica senza verifica: {e}")
        
        # Now decode with verification
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        logger.info(f"Token decodificato con successo: {payload}")
        return payload
    except JWTError as e:
        logger.error(f"Errore JWT durante decodifica: {type(e).__name__}: {e}")
        return None
    except Exception as e:
        logger.error(f"Errore generico durante decodifica: {type(e).__name__}: {e}")
        return None

