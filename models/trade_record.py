from sqlmodel import SQLModel, Field, Column, String
from typing import Optional
from decimal import Decimal
from datetime import datetime
from models.base import BaseModel

class TradeRecord(BaseModel, table=True):
    """交易记录表"""
    __tablename__ = "trade_records"
    
    trader_id: str = Field(foreign_key="traders.id", index=True)
    symbol: str = Field(max_length=50, index=True)  # 'BTC/USDT'
    side: str = Field(max_length=10)  # 'buy' or 'sell'
    amount: Decimal = Field(max_digits=20, decimal_places=8)
    price: Decimal = Field(max_digits=20, decimal_places=8)
    leverage: int = Field(default=1)
    order_id: Optional[str] = Field(default=None, max_length=255)
    status: str = Field(default="pending", max_length=50)  # 'pending', 'filled', 'cancelled', 'failed'
    executed_at: Optional[datetime] = Field(default=None)  # 执行时间
    # created_at 和 updated_at 继承自 BaseModel
