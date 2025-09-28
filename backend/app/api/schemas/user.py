from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """用户基础Schema"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)


class UserCreate(UserBase):
    """创建用户Schema"""
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    """用户登录Schema"""
    username: str
    password: str


class UserResponse(UserBase):
    """用户响应Schema"""
    id: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    """令牌Schema"""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """令牌数据Schema"""
    email: Optional[str] = None