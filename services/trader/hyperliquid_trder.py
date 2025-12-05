from models import trader
from services.trader.interface import ExchangeInterface
from utils.logger import logger
from decimal import Decimal
import eth_account
from hyperliquid.utils import constants
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info

class hyperliquid_trader(ExchangeInterface):
    def __init__(self,exchang_config: dict) -> None:
        logger.info(f"Hyperliquid 交易所初始化")
        self.exchange_config = exchang_config
        self.wallet_address = exchang_config.get('wallet_address')
        self.secret_key = exchang_config.get('secret_key')
        self.testnet = exchang_config.get('testnet',False)
        if not self.wallet_address or not self.secret_key:
            logger.error(f"Hyperliquid 交易所配置错误: 钱包地址或私钥不能为空")
            raise ValueError(f"Hyperliquid 交易所配置错误: 钱包地址或私钥不能为空")
        
        #初始化钱包
        try:
            self.wallet = eth_account.Account.from_key(self.secret_key)
        except Exception as e:
            logger.error(f"Hyperliquid 交易所初始化失败: {e}")
            raise
        
        # 选择 API URL
        api_url = constants.TESTNET_API_URL if self.testnet else constants.MAINNET_API_URL
        #初始化Exchange和Info
        self.exchange = Exchange(self.wallet,api_url)
        self.info = Info(api_url, skip_ws=True)
        logger.info(f"Hyperliquid 交易所初始化成功")
        # 修复：使用正确的 f-string 格式化
        #balance = self.get_balance('')
        #logger.info(f"账户余额: {balance}")

    
    def get_balance(self, symbol: str) -> Decimal:
        """获取账户余额"""
        try:
            user_state = self.info.user_state(self.wallet_address)
            
            if not user_state:
                logger.warning(f"⚠️ user_state 返回为空")
                return Decimal('0')
            
            # 检查响应结构
            if isinstance(user_state, dict):
                # 优先从 marginSummary 获取 accountValue
                if 'marginSummary' in user_state:
                    margin_summary = user_state['marginSummary']
                    if isinstance(margin_summary, dict):
                        account_value = margin_summary.get('accountValue', 0)
                        return Decimal(str(account_value))
                
                # 如果没有 marginSummary，尝试直接获取 accountValue
                if 'accountValue' in user_state:
                    account_value = user_state['accountValue']
                    return Decimal(str(account_value))
                
                # 最后尝试获取 withdrawable（可提取余额）
                if 'withdrawable' in user_state:
                    withdrawable = user_state['withdrawable']
                    return Decimal(str(withdrawable))
            
            return Decimal('0')
        except Exception as e:
            logger.error(f"❌ 获取余额失败: {e}", exc_info=True)
            return Decimal('0')

    def get_all_position(self, symbol: str) -> Decimal:
        pass
    
    def openLong(self, symbol: str, quantity: Decimal, leverage: int) -> Decimal:
        pass
    
    def openShort(self, symbol: str, quantity: Decimal, leverage: int) -> Decimal:
        pass
    
    def closeLong(self, symbol: str, quantity: Decimal) -> Decimal:
        pass
    
    def closeShort(self, symbol: str, quantity: Decimal) -> Decimal:
        pass
    
    def setLeverage(self, symbol: str, leverage: int) -> Decimal:
        pass
    
    def setMarginMode(self, isCrossMargin: bool) -> Decimal:
        pass
    
    def getMarketPrice(self, symbol: str) -> Decimal:
        pass

    def setStopLoss(self, symbol: str, positionSide: str, quantity: Decimal, stopPrice: Decimal) -> Decimal:
        pass
    
    def setTakeProfit(self, symbol: str, positionSide: str, quantity: Decimal, takeProfitPrice: Decimal) -> Decimal:
        pass
    
    def cancelAllOrders(self, symbol: str) -> Decimal:
        pass
    
    def formatQuantity(self, symbol: str, quantity: Decimal) -> Decimal:
        return Decimal(str(quantity)).quantize(Decimal('0.00000001'))
   
    def _conver_symbol(self, symbol: str) -> str:
        return symbol.split('/')[0]