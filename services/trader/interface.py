#交易所统一接口类
#用来抹平CCXT以及具备SDK的交易所的差异
from abc import ABC, abstractmethod
from typing import Optional
from decimal import Decimal

class ExchangeInterface(ABC):
    """交易所统一接口类"""
    @abstractmethod
    def get_balance(self, symbol: str) -> Decimal:
        """获取账户余额"""
        pass
    
    @abstractmethod
    def get_all_position(self, symbol: str) -> Decimal:
        """获取所有持仓"""
        pass
    
    @abstractmethod
    def openLong(self, symbol: str, quantity: Decimal, leverage: int) -> Decimal:
        """开多仓"""
        pass
    
    @abstractmethod
    def openShort(self, symbol: str, quantity: Decimal, leverage: int) -> Decimal:
        """开空仓"""
        pass
    
    @abstractmethod
    def closeLong(self, symbol: str, quantity: Decimal) -> Decimal:
        """平多仓 quantity=0 表示平仓所有"""
        pass
    
    @abstractmethod
    def closeShort(self, symbol: str, quantity: Decimal) -> Decimal:
        """平空仓 quantity=0 表示平仓所有"""
        pass
    
    @abstractmethod
    def setLeverage(self, symbol: str, leverage: int) -> Decimal:
        """设置杠杆"""
        pass

    @abstractmethod
    def setMarginMode(self, isCrossMargin: bool) -> Decimal:
        """设置保证金模式 全仓/逐仓 isCrossMargin=True 表示全仓, isCrossMargin=False 表示逐仓"""
        pass
    
    @abstractmethod
    def getMarketPrice(self, symbol: str) -> Decimal:
        """获取市场价格"""
        pass

    
    @abstractmethod
    def setStopLoss(self, symbol: str, positionSide: str, quantity: Decimal, stopPrice: Decimal) -> Decimal:
        """设置止损 positionSide=long 表示多仓, positionSide=short 表示空仓 quantity=0 表示设置所有仓位止损 stopPrice=0 表示不设置止损"""
        pass
    
    @abstractmethod
    def setTakeProfit(self, symbol: str, positionSide: str, quantity: Decimal, takeProfitPrice: Decimal) -> Decimal:
        """设置止盈 positionSide=long 表示多仓, positionSide=short 表示空仓 quantity=0 表示设置所有仓位止盈 takeProfitPrice=0 表示不设置止盈"""
        pass

    @abstractmethod
    def cancelAllOrders(self, symbol: str) -> Decimal:
        """取消所有订单"""
        pass

    @abstractmethod
    def formatQuantity(self, symbol: str, quantity: Decimal) -> Decimal:
        """格式化数量到正确的精度"""
        pass
    