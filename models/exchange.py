from sqlmodel import SQLModel, Field, Column, String
from models.base import BaseModel

class Exchange(BaseModel, table=True):
    """交易所配置表"""
    __tablename__ = "exchanges"
    
    user_id: str = Field(foreign_key="users.id", index=True)
    name: str = Field(max_length=255)
    type: str = Field(max_length=10)  # 'cex' or 'dex'
    enabled: bool = Field(default=False)
    api_key: str = Field(default="")
    secret_key: str = Field(default="")
    testnet: bool = Field(default=False)
    
    # 钱包
    wallet_address: str = Field(default="", max_length=255)
