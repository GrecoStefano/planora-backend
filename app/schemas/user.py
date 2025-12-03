from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    team: Optional[str] = None
    timezone: str = "UTC"


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    team: Optional[str] = None
    timezone: Optional[str] = None
    preferences: Optional[dict] = None


class UserResponse(UserBase):
    id: int
    role: UserRole
    is_active: bool
    preferences: dict
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None

