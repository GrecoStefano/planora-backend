from pydantic_settings import BaseSettings
from typing import List
import os

# Read CORS_ORIGINS before pydantic-settings tries to parse it
_cors_origins_env = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001")
# Temporarily remove from env to avoid pydantic parsing
if "CORS_ORIGINS" in os.environ:
    _cors_origins_backup = os.environ.pop("CORS_ORIGINS")


class Settings(BaseSettings):
    # App
    PROJECT_NAME: str = "Planora"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://planora:planora_dev@localhost:5432/planora"
    )
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Email
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "noreply@planora.com")
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_DIR: str = "uploads"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        # Ignore CORS_ORIGINS from env file (we'll parse it manually)
        env_ignore_empty = True
        extra = "ignore"  # Ignore extra fields from env


# Create settings instance
settings = Settings()

# Restore CORS_ORIGINS to env if it was there
if "_cors_origins_backup" in locals():
    os.environ["CORS_ORIGINS"] = _cors_origins_backup

# Parse CORS_ORIGINS manually and add as attribute
settings.CORS_ORIGINS = [origin.strip() for origin in _cors_origins_env.split(",") if origin.strip()]

