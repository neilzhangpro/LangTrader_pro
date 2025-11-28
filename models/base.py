from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
import uuid

class BaseModel(SQLModel):
    """基础模型类"""
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        nullable=False,
    )