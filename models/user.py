from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from models.base import BaseModel

class User(BaseModel, table=True):
    """用户模型"""
    __tablename__ = "users"

    email: str = Field(unique=True, index=True)
    password_hash: str
    otp_secret: Optional[str] = None
    otp_verified: bool = False