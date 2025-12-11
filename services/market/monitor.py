"""
市场数据监控器 - 后台运行 WebSocket 客户端，持续接收并缓存市场数据
类似 Nofx 的 monitor.go
"""
import asyncio
import threading
from typing import Dict, List, Optional, Set
from collections import defaultdict, deque
from datetime import datetime
from utils.logger import logger
from services.market.client import WSClient
from services.market.api_client import APIClient
from services.market.type import Kline

class MarketMonitor:
    """市场数据监控器 - 后台运行，缓存实时数据"""
    
    def __init__(self, exchange_config: dict):
        self.exchange_config = exchange_config
        self.api_client = APIClient()
        self.ws_client = WSClient()
        
        # 数据缓存
        self.kline_cache: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))  # 最多保存1000根K线
        self.price_cache: Dict[str, float] = {}  # 最新价格
        self.ticker_cache: Dict[str, dict] = {}  # Ticker数据
        
        # 运行状态
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitored_symbols: Set[str] = set()
        
        # 线程安全锁
        self._cache_lock = threading.Lock()
        
        logger.info("MarketMonitor 初始化完成")
        
    def start(self):
        """启动监控器（在后台线程中运行异步事件循环）"""
        if self._running:
            logger.warning("MarketMonitor 已在运行")
            return
        
        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._run_event_loop,
            daemon=True,
            name="MarketMonitor"
        )
        self._monitor_thread.start()
        logger.info("✅ MarketMonitor 已启动")
    
    def stop(self):
        """停止监控器"""
        if not self._running:
            return
        
        self._running = False
        
        # 不需要在这里停止 WebSocket，_monitor_loop 会在同一个事件循环中处理
        # 只需要等待监控线程结束
        
        if self._monitor_thread:
            self._monitor_thread.join(timeout=10)  # 增加超时时间
        
        logger.info("✅ MarketMonitor 已停止")
    
    def _run_event_loop(self):
        """在独立线程中运行异步事件循环"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(self._monitor_loop())
        except Exception as e:
            logger.error(f"监控循环错误: {e}", exc_info=True)
        finally:
            # 确保清理所有任务
            try:
                # 取消所有待处理的任务
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                # 等待所有任务完成
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception as e:
                logger.error(f"清理任务时出错: {e}")
            finally:
                loop.close()
    
    async def _monitor_loop(self):
        """监控循环（异步）"""
        # 启动 WebSocket 客户端
        await self.ws_client.start()
        logger.info("WebSocket 客户端已启动")
        
        # 等待停止信号
        while self._running:
            await asyncio.sleep(1)
        
        # 停止 WebSocket 客户端（在同一个事件循环中）
        await self.ws_client.stop()
        logger.info("WebSocket 客户端已停止")
    
    async def add_symbol(self, symbol: str, intervals: List[str] = ["3m", "4h"]):
        """添加监控的交易对"""
        if symbol in self._monitored_symbols:
            logger.info(f"{symbol} 已在监控中")
            return
        
        self._monitored_symbols.add(symbol)
        normalized_symbol = symbol.replace('/', '').lower()
        
        # 使用 API 获取历史数据初始化缓存
        try:
            for interval in intervals:
                klines = self.api_client.get_Klines(symbol, interval, limit=200)
                if klines:
                    cache_key = f"{normalized_symbol}_{interval}"
                    with self._cache_lock:
                        self.kline_cache[cache_key] = deque(klines, maxlen=1000)
                    logger.info(f"✅ 已加载 {symbol} {interval} 历史K线: {len(klines)} 根")
        except Exception as e:
            logger.error(f"❌ 加载 {symbol} 历史数据失败: {e}", exc_info=True)
        
        # 订阅 WebSocket 流
        for interval in intervals:
            stream_name = f"{normalized_symbol}@kline_{interval}"
            await self.ws_client.subscribe(stream_name, self._on_kline_message)
            logger.info(f"✅ 已订阅: {stream_name}")
        
        # 订阅 Ticker（获取最新价格）
        ticker_stream = f"{normalized_symbol}@ticker"
        await self.ws_client.subscribe(ticker_stream, self._on_ticker_message)
        logger.info(f"✅ 已订阅: {ticker_stream}")
    
    async def remove_symbol(self, symbol: str):
        """移除监控的交易对"""
        if symbol not in self._monitored_symbols:
            return
        
        self._monitored_symbols.remove(symbol)
        normalized_symbol = symbol.replace('/', '').lower()
        
        # 清理缓存
        with self._cache_lock:
            # 清理相关缓存键
            keys_to_remove = [k for k in self.kline_cache.keys() if k.startswith(normalized_symbol)]
            for key in keys_to_remove:
                del self.kline_cache[key]
            
            if normalized_symbol.upper() in self.price_cache:
                del self.price_cache[normalized_symbol.upper()]
            if normalized_symbol.upper() in self.ticker_cache:
                del self.ticker_cache[normalized_symbol.upper()]
        
        logger.info(f"✅ 已移除监控: {symbol}")
    
    def _on_kline_message(self, message: dict):
        """处理K线消息（在WebSocket线程中调用）"""
        try:
            # Binance K线数据格式
            kline_data = message.get("k", {})
            if not kline_data:
                return
            
            symbol = kline_data.get("s", "").upper()  # BTCUSDT
            interval = kline_data.get("i", "")  # 1m, 3m, 4h等
            is_closed = kline_data.get("x", False)  # K线是否已结束
            
            if is_closed:
                # 只有K线结束时才更新缓存
                kline = Kline(
                    open_time=int(kline_data["t"]),
                    open=float(kline_data["o"]),
                    high=float(kline_data["h"]),
                    low=float(kline_data["l"]),
                    close=float(kline_data["c"]),
                    volume=float(kline_data.get("v", 0)),
                    close_time=int(kline_data["T"]),
                    quote_volume=float(kline_data.get("q", 0)),
                    trades=int(kline_data.get("n", 0))
                )
                
                cache_key = f"{symbol.lower()}_{interval}"
                with self._cache_lock:
                    # 如果已存在相同时间的K线，替换它；否则添加新的
                    existing = False
                    for i, existing_kline in enumerate(self.kline_cache[cache_key]):
                        if existing_kline.open_time == kline.open_time:
                            self.kline_cache[cache_key][i] = kline
                            existing = True
                            break
                    
                    if not existing:
                        self.kline_cache[cache_key].append(kline)
                    
                    # 更新最新价格
                    self.price_cache[symbol] = float(kline_data["c"])
                
                logger.debug(f"📊 K线更新: {symbol} {interval} @ {kline.close}")
        except Exception as e:
            logger.error(f"❌ 处理K线消息失败: {e}", exc_info=True)
    
    def _on_ticker_message(self, message: dict):
        """处理Ticker消息"""
        try:
            symbol = message.get("s", "").upper()
            with self._cache_lock:
                self.ticker_cache[symbol] = message
                self.price_cache[symbol] = float(message.get("c", 0))
        except Exception as e:
            logger.error(f"❌ 处理Ticker消息失败: {e}", exc_info=True)
    
    def get_klines(self, symbol: str, interval: str, limit: int = 100) -> List[Kline]:
        """获取缓存的K线数据（线程安全）"""
        normalized_symbol = symbol.replace('/', '').upper()
        cache_key = f"{normalized_symbol.lower()}_{interval}"
        
        with self._cache_lock:
            klines = list(self.kline_cache.get(cache_key, deque()))
            return klines[-limit:] if len(klines) > limit else klines
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """获取最新价格（线程安全）"""
        normalized_symbol = symbol.replace('/', '').upper()
        with self._cache_lock:
            return self.price_cache.get(normalized_symbol)
    
    def get_ticker(self, symbol: str) -> Optional[dict]:
        """获取Ticker数据（线程安全）"""
        normalized_symbol = symbol.replace('/', '').upper()
        with self._cache_lock:
            return self.ticker_cache.get(normalized_symbol)
    
    def is_monitoring(self, symbol: str) -> bool:
        """检查是否正在监控某个交易对"""
        return symbol in self._monitored_symbols