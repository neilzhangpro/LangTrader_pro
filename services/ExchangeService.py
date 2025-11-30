from config.settings import Settings
from models.exchange import Exchange
import ccxt
from utils.logger import logger
from sqlmodel import select
from typing import Optional

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
            logger.info(f"初始化 Hyperliquid 交易所")
        logger.info(f"初始化 DEX 交易所成功")
        pass

