from config.settings import Settings
from models.exchange import Exchange
import ccxt
from utils.logger import logger
from sqlmodel import select
from typing import Optional
from services.trader.hyperliquid_trder import hyperliquid_trader

class ExchangeService:
    """
    ExchangeService class
    """

    def __init__(self,exchange_config: dict, settings: Settings):
        self.settings = settings
        self.exchange_config = exchange_config
        self.exchange_id = exchange_config.get('id')
        logger.info(f"Exchange {self.exchange_id} initialized")
        logger.info(f"Exchange {self.exchange_config}")
        #CCXT 初始化
        self._ccxt_exchange: Optional[ccxt.Exchange] = None
        #初始化 CCXT 交易所
        self._init_ccxt_exchange()
    
    def _init_ccxt_exchange(self):
        """初始化 CCXT 交易所"""
        #CEX使用CCXT, DEX暂时使用具备SDK的交易所
        try:
            if self.exchange_config.get('type') == 'CEX':
                #cex
                self._init_cex()
            elif self.exchange_config.get('type') == 'DEX':
                #dex
                self._init_dex()
            else:
                logger.error(f"❌ 不支持的交易所类型: {self.exchange_config.get('type')}")
                raise ValueError(f"不支持的交易所类型: {self.exchange_config.get('type')}")
        except Exception as e:
            logger.error(f"❌ 初始化 CCXT 交易所失败: {e}", exc_info=True)
            raise
    
    def _init_cex(self):
        """初始化 CEX 交易所"""
        exchange_name = self.exchange_config.get('name').lower()

        #映射CCXT的CEX交易所
        cex_mapping = {
            'binance': 'binance',
            'binance main': 'binance',
            'binance testnet': 'binance',
            'okx': 'okx',
            'okx main': 'okx',
            'gate.io': 'gate',
            'gate.io main': 'gate',
        }

        ccxt_exchange_name = cex_mapping.get(exchange_name)
        if not ccxt_exchange_name:
            logger.error(f"❌ 不支持的交易所: {exchange_name}")
            raise ValueError(f"不支持的交易所: {exchange_name}")
        
        #初始化 CCXT 交易所
        self._ccxt_exchange = ccxt.create(ccxt_exchange_name, {
            'apiKey': self.exchange_config.get('api_key'),
            'secret': self.exchange_config.get('secret_key'),
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future', #默认合约交易
            }
        })
        logger.info(f"CCXT 交易所 {ccxt_exchange_name} 初始化成功")
    
    def _init_dex(self):
        exchange_name = self.exchange_config.get('name').lower()
        if exchange_name == 'hyperliquid':
            #TODO: 初始化 Hyperliquid 交易所
            self.hyperliquid_trader = hyperliquid_trader(self.exchange_config)
            return self.hyperliquid_trader
        logger.info(f"初始化 DEX 交易所成功")
        pass

    def get_balance(self, symbol: str = '') -> float:
        """获取账户余额（统一接口）"""
        try:
            if self.exchange_config.get('type') == 'CEX':
                # CEX 使用 CCXT
                if self._ccxt_exchange:
                    balance = self._ccxt_exchange.fetch_balance()
                    # 获取 USDT 余额
                    if 'USDT' in balance.get('total', {}):
                        return float(balance['total']['USDT'])
                    # 如果没有 USDT，返回第一个可用余额
                    for currency, amount in balance.get('total', {}).items():
                        if amount > 0:
                            return float(amount)
                    return 0.0
                else:
                    logger.warning("⚠️ CCXT 交易所未初始化")
                    return 0.0
            elif self.exchange_config.get('type') == 'DEX':
                # DEX 使用特定 SDK
                if self.hyperliquid_trader:
                    balance_decimal = self.hyperliquid_trader.get_balance(symbol)
                    return float(balance_decimal)
                else:
                    logger.warning("⚠️ Hyperliquid trader 未初始化")
                    return 0.0
            else:
                logger.warning(f"⚠️ 不支持的交易所类型: {self.exchange_config.get('type')}")
                return 0.0
        except Exception as e:
            logger.error(f"❌ 获取账户余额失败: {e}", exc_info=True)
            return 0.0

    def get_positions(self) -> list:
        """获取所有持仓（统一接口）"""
        try:
            positions = []
            if self.exchange_config.get('type') == 'CEX':
                # CEX 使用 CCXT
                if self._ccxt_exchange:
                    ccxt_positions = self._ccxt_exchange.fetch_positions()
                    for pos in ccxt_positions:
                        if float(pos.get('contracts', 0)) != 0:  # 只返回有持仓的
                            positions.append({
                                'symbol': pos.get('symbol'),
                                'side': pos.get('side'),  # 'long' or 'short'
                                'size': float(pos.get('contracts', 0)),
                                'entry_price': float(pos.get('entryPrice', 0)),
                                'mark_price': float(pos.get('markPrice', 0)),
                                'unrealized_pnl': float(pos.get('unrealizedPnl', 0)),
                                'leverage': int(pos.get('leverage', 1)),
                            })
            elif self.exchange_config.get('type') == 'DEX':
                # DEX 使用特定 SDK
                if self.hyperliquid_trader:
                    # TODO: 实现 Hyperliquid 持仓获取
                    # positions = self.hyperliquid_trader.get_all_position('')
                    pass
            return positions
        except Exception as e:
            logger.error(f"❌ 获取持仓失败: {e}", exc_info=True)
            return []   
