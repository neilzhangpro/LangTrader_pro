"""
历史数据加载器 - 批量加载多个币种的历史K线数据
"""
from typing import List, Dict
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.logger import logger
from services.market.api_client import APIClient
from services.market.type import Kline


class HistoricalDataLoader:
    """历史数据加载器 - 并发加载多个币种的历史K线数据"""
    
    def __init__(self, api_client: APIClient):
        """初始化历史数据加载器
        
        Args:
            api_client: API客户端，用于获取K线数据
        """
        self.api_client = api_client
    
    def get_all_tradable_symbols(self) -> List[str]:
        """获取所有可交易币种（USDT永续合约）"""
        try:
            # 使用 CCXT 获取交易所信息
            markets = self.api_client.exchange.markets
            
            symbols = []
            for symbol, market in markets.items():
                # 筛选条件：永续合约、USDT计价、可交易
                market_type = market.get('type', '')
                settle = market.get('settle', '')
                active = market.get('active', True)
                
                # 检查是否是USDT永续合约
                is_usdt_swap = (
                    (market_type == 'swap' or market_type == 'future') and
                    settle == 'USDT' and
                    active
                )
                
                if is_usdt_swap:
                    # 转换为标准格式（去掉 :USDT 后缀，统一为 BTC/USDT 格式）
                    if ':USDT' in symbol:
                        normalized = symbol.replace(':USDT', '')
                    elif symbol.endswith('/USDT'):
                        normalized = symbol
                    else:
                        # 如果格式不标准，尝试从 base 和 quote 构建
                        base = market.get('base', '')
                        quote = market.get('quote', '')
                        if base and quote == 'USDT':
                            normalized = f"{base}/{quote}"
                        else:
                            continue
                    
                    symbols.append(normalized)
            
            logger.info(f"✅ 获取到 {len(symbols)} 个USDT永续合约交易对")
            return symbols
        except Exception as e:
            logger.error(f"❌ 获取所有交易对失败: {e}", exc_info=True)
            return []
    
    def load_historical_data(
        self, 
        symbols: List[str], 
        intervals: List[str], 
        cache: Dict[str, deque],
        cache_lock
    ) -> int:
        """加载历史数据到缓存（并发获取，类似 Nofx 的流式获取）
        
        Args:
            symbols: 币种列表
            intervals: 时间周期列表，如 ["3m", "4h"]
            cache: K线缓存字典，用于存储加载的数据
            cache_lock: 线程锁，用于保护缓存访问
            
        Returns:
            成功加载的币种数量
        """
        logger.info(f"开始初始化 {len(symbols)} 个币种的历史数据...")
        
        def fetch_symbol_data(symbol: str):
            """获取单个币种的历史数据"""
            try:
                klines_map = {}
                success = True
                
                # 获取所有时间周期的K线
                for interval in intervals:
                    klines = self.api_client.get_Klines(symbol, interval, limit=100)
                    if klines:
                        klines_map[interval] = klines
                    else:
                        success = False
                        break
                
                if success and klines_map:
                    normalized_symbol = symbol.replace('/', '').lower()
                    with cache_lock:
                        # 缓存每个时间周期的K线
                        for interval, klines in klines_map.items():
                            cache_key = f"{normalized_symbol}_{interval}"
                            cache[cache_key] = deque(klines, maxlen=1000)
                    
                    return symbol, True
                return symbol, False
            except Exception as e:
                logger.debug(f"⚠️ {symbol} 历史数据获取失败: {e}")
                return symbol, False
        
        # 使用线程池并发获取（限制并发数为5，避免API限速）
        success_count = 0
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fetch_symbol_data, symbol): symbol for symbol in symbols}
            
            for future in as_completed(futures):
                symbol, success = future.result()
                if success:
                    success_count += 1
                    if success_count % 50 == 0:
                        logger.info(f"📊 已加载 {success_count} 个币种的历史数据...")
        
        logger.info(f"✅ 历史数据初始化完成，成功加载 {success_count}/{len(symbols)} 个币种")
        return success_count

