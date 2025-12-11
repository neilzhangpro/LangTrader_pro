from decision_engine.state import DecisionState
from services.market.api_client import APIClient
from utils.logger import logger
from typing import Optional, List, Dict
from services.market.monitor import MarketMonitor
import asyncio
import threading

class DataCollector:
    """数据收集节点 - 收集市场数据（K线、价格等）和交易所信息（余额、持仓）"""
    
    # K线数据配置
    KLINE_LIMIT = 200  # K线数据获取数量
    
    # WebSocket订阅配置
    WS_SUBSCRIBE_TIMEOUT_SECONDS = 5  # WebSocket订阅超时时间（秒）
    
    def __init__(self, market_monitor: Optional[MarketMonitor] = None):
        """
        初始化数据收集节点
        
        Args:
            market_monitor: 市场数据监控器（可选）
        """
        self.market_monitor = market_monitor
        self.api_client: Optional[APIClient] = None  # 延迟初始化

    def _get_api_client(self, state: DecisionState) -> Optional[APIClient]:
        """从state获取exchange_config并创建APIClient（延迟初始化）"""
        if self.api_client:
            return self.api_client
        
        exchange_config = state.get('exchange_config')
        if exchange_config:
            self.api_client = APIClient()
            logger.info(f"创建APIClient成功: {self.api_client}")
            return self.api_client
        
        logger.warning("⚠️ exchange_config未设置，无法创建APIClient")
        return None

    def _get_account_balance(self, state: DecisionState) -> float:
        """
        获取账户余额（留空，等待Exchange服务重构完成）
        
        Args:
            state: 决策状态，包含exchange_config
            
        Returns:
            账户余额（USD），当前返回0.0表示未实现
        """
        exchange_config = state.get('exchange_config')
        if not exchange_config:
            logger.debug("exchange_config未设置，无法获取账户余额")
            return 0.0
        
        # TODO: 实现获取账户余额的逻辑
        # 当前返回0.0，表示未实现
        logger.debug("获取账户余额（待实现）")
        return 0.0

    def _get_positions(self, state: DecisionState) -> List[Dict]:
        """
        获取所有持仓（留空，等待Exchange服务重构完成）
        
        Args:
            state: 决策状态，包含exchange_config
            
        Returns:
            持仓列表，当前返回空列表表示未实现
        """
        exchange_config = state.get('exchange_config')
        if not exchange_config:
            logger.debug("exchange_config未设置，无法获取持仓")
            return []
        
        # TODO: 实现获取持仓的逻辑
        # 当前返回空列表，表示未实现
        logger.debug("获取持仓信息（待实现）")
        return []

    def run(self, state: DecisionState) -> DecisionState:
        """
        收集市场数据和交易所信息（批量模式：为所有需要的币种收集数据）
        
        职责：
        1. 获取账户余额和持仓信息
        2. 收集市场数据（K线、价格等）
        """
        logger.info("-"*30)
        logger.info("Strat DataCollector*********************************>>>>>>>>>>>>>")
        # 1. 获取账户信息（余额、持仓）
        account_balance = self._get_account_balance(state)
        positions = self._get_positions(state)
        
        # 填充到state
        state['account_balance'] = account_balance
        state['positions'] = positions
        
        if positions:
            logger.info(f"✓ 获取到 {len(positions)} 个持仓")
        if account_balance > 0:
            logger.info(f"✓ 账户余额: {account_balance} USDT")
        
        # 2. 获取持仓币种（用于收集市场数据）
        position_symbols = {pos.get('symbol') for pos in positions if pos.get('symbol')}
        
        # 3. 获取候选币种（用于开仓决策）
        candidate_symbols = state.get('candidate_symbols', [])
        
        # 4. 合并去重，确保所有需要的币种都有数据
        all_symbols = list(set(position_symbols) | set(candidate_symbols))
        
        if not all_symbols:
            logger.warning("没有需要收集数据的币种，跳过市场数据收集")
            state['market_data_map'] = {}
            return state
        
        logger.info(f"开始收集市场数据: 持仓币种={len(position_symbols)}个, 候选币种={len(candidate_symbols)}个, 总计={len(all_symbols)}个")
        
        # 5. 确保所有币种都已添加到监控器（动态订阅WebSocket）
        if self.market_monitor:
            self._ensure_symbols_monitored(all_symbols)
        
        # 6. 获取API客户端（延迟初始化）
        api_client = self._get_api_client(state)
        if not api_client:
            logger.warning("⚠️ 无法创建APIClient，跳过市场数据收集")
            state['market_data_map'] = {}
            return state
        
        # 7. 收集市场数据
        market_data_map = {}
        
        for symbol in all_symbols:
            try:
                # 优先从监控器缓存获取数据
                if self.market_monitor and self.market_monitor.is_monitoring(symbol):
                    klines_3m = self.market_monitor.get_klines(symbol, "3m", limit=self.KLINE_LIMIT)
                    klines_4h = self.market_monitor.get_klines(symbol, "4h", limit=self.KLINE_LIMIT)
                    latest_price = self.market_monitor.get_latest_price(symbol)
                    
                    market_data_map[symbol] = {
                        'symbol': symbol,
                        'current_price': latest_price,
                        'klines_3m': klines_3m,
                        'klines_4h': klines_4h,
                        'source': 'websocket_cache',
                        'is_position': symbol in position_symbols,  # 标记是否为持仓币种
                        'is_candidate': symbol in candidate_symbols  # 标记是否为候选币种
                    }
                    logger.debug(f"{symbol}: 从监控器缓存获取数据")
                else:
                    # 回退到 REST API
                    klines_3m = api_client.get_Klines(symbol, "3m", limit=self.KLINE_LIMIT)
                    klines_4h = api_client.get_Klines(symbol, "4h", limit=self.KLINE_LIMIT)
                    
                    market_data_map[symbol] = {
                        'symbol': symbol,
                        'klines_3m': klines_3m or [],
                        'klines_4h': klines_4h or [],
                        'source': 'rest_api',
                        'is_position': symbol in position_symbols,
                        'is_candidate': symbol in candidate_symbols
                    }
                    logger.debug(f"{symbol}: 从REST API获取数据")
            except Exception as e:
                logger.error(f"收集{symbol}市场数据失败: {e}", exc_info=True)
                market_data_map[symbol] = {
                    'symbol': symbol,
                    'error': str(e)
                }
        
        state['market_data_map'] = market_data_map
        logger.info(f"完成数据收集，共{len(market_data_map)}个币种")
        return state
    
    def _ensure_symbols_monitored(self, symbols: list):
        """确保所有币种都已添加到监控器（动态订阅WebSocket）"""
        if not self.market_monitor:
            return
        
        # 检查哪些币种需要添加
        symbols_to_add = [s for s in symbols if not self.market_monitor.is_monitoring(s)]
        
        if not symbols_to_add:
            logger.debug("所有币种已在监控中")
            return
        
        logger.debug(f"需要添加{len(symbols_to_add)}个币种到监控器")
        
        # 在独立线程中运行异步操作（因为监控器的事件循环在另一个线程）
        def add_symbols_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                for symbol in symbols_to_add:
                    try:
                        loop.run_until_complete(
                            self.market_monitor.add_symbol(symbol, intervals=["3m", "4h"])
                        )
                        logger.debug(f"已添加{symbol}到监控器并订阅WebSocket")
                    except Exception as e:
                        logger.error(f"添加{symbol}到监控器失败: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"添加币种到监控器失败: {e}", exc_info=True)
            finally:
                loop.close()
        
        # 在后台线程中执行（不阻塞主流程）
        thread = threading.Thread(target=add_symbols_async, daemon=True)
        thread.start()
        # 等待订阅完成
        thread.join(timeout=self.WS_SUBSCRIBE_TIMEOUT_SECONDS)
        
        if thread.is_alive():
            logger.warning("添加币种到监控器超时，将使用REST API回退")
        else:
            # 验证订阅状态
            failed_symbols = [s for s in symbols_to_add if not self.market_monitor.is_monitoring(s)]
            if failed_symbols:
                logger.warning(f"以下币种订阅失败，将使用REST API: {failed_symbols}")
    