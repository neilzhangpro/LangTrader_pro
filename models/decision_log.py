from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON
from typing import Optional, Dict, Any
from decimal import Decimal
from models.base import BaseModel

class DecisionLog(BaseModel, table=True):
    """决策日志表"""
    __tablename__ = "decision_logs"
    
    trader_id: str = Field(foreign_key="traders.id", index=True)
    symbol: str = Field(max_length=50, index=True)
    decision_state: Dict[str, Any] = Field(sa_column=Column(JSON))  # JSONB，存储为字典
    decision_result: Optional[str] = Field(default=None, max_length=50)  # 'open_long', 'open_short', 'close_long', 'close_short', 'hold', 'wait'
    reasoning: Optional[str] = None
    confidence: Optional[Decimal] = Field(
        default=None,
        max_digits=5,
        decimal_places=4
    )
    
    # 注意：created_at 继承自 BaseModel
