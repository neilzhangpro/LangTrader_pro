"""
币种筛选器 - 管理筛选后的币种列表（对应 Nofx 的 FilterSymbol）
"""
import threading
import time
from typing import List, Optional, Set
from utils.logger import logger

# 前向引用，避免循环导入
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from services.market.monitor import MarketMonitor
    from services.market.symbol_scorer import SymbolScorer


class SymbolFilter:
    """币种筛选器 - 管理筛选后的币种列表（对应 Nofx 的 FilterSymbol）"""
    
    def __init__(
        self, 
        market_monitor: 'MarketMonitor', 
        symbol_scorer: 'SymbolScorer',
        all_symbols: List[str],
        running_flag: Optional[threading.Event] = None
    ):
        """初始化币种筛选器
        
        Args:
            market_monitor: 市场监控器，用于获取K线数据
            symbol_scorer: 币种评分器，用于评分
            all_symbols: 所有可交易币种列表
            running_flag: 运行标志，用于控制筛选任务的生命周期
        """
        self.market_monitor = market_monitor
        self.symbol_scorer = symbol_scorer
        self.all_symbols = all_symbols
        self.running_flag = running_flag
        
        # 筛选后的币种列表（对应 Nofx 的 FilterSymbol）
        self.filtered_symbols: List[str] = []
        self._filtered_symbols_lock = threading.Lock()
        
        # 筛选任务线程
        self._filtering_thread: Optional[threading.Thread] = None
        self._running = False
    
    def start(self):
        """启动筛选任务（后台定期更新 filtered_symbols，类似 Nofx 的定时更新）"""
        if self._running:
            logger.warning("筛选任务已在运行")
            return
        
        if self._filtering_thread and self._filtering_thread.is_alive():
            logger.warning("筛选任务已在运行")
            return
        
        self._running = True
        
        def filtering_loop():
            logger.info("🚀 内置AI评分筛选任务已启动")
            
            while self._running:
                # 检查外部停止标志
                if self.running_flag and self.running_flag.is_set():
                    logger.info("收到停止信号，筛选任务将退出")
                    break
                
                try:
                    # 执行筛选
                    filtered = self._perform_filtering()
                    
                    with self._filtered_symbols_lock:
                        self.filtered_symbols = filtered
                    
                    logger.info(f"✅ 内置AI评分完成，筛选出 {len(filtered)} 个币种")
                except Exception as e:
                    logger.error(f"❌ 内置AI评分失败: {e}", exc_info=True)
                
                # 每分钟更新一次（类似 Nofx 的 time.Sleep(1 * time.Minute)）
                # 使用 running_flag 的 wait 方法，可以响应停止信号
                if self.running_flag:
                    if self.running_flag.wait(timeout=60):
                        # 如果 wait 返回 True，说明收到了停止信号
                        break
                else:
                    time.sleep(60)
            
            self._running = False
            logger.info("筛选任务已停止")
        
        self._filtering_thread = threading.Thread(
            target=filtering_loop,
            daemon=True,
            name="FilteringTask"
        )
        self._filtering_thread.start()
    
    def stop(self):
        """停止筛选任务"""
        if not self._running:
            return
        
        self._running = False
        
        if self._filtering_thread:
            self._filtering_thread.join(timeout=10)
            self._filtering_thread = None
        
        logger.info("✅ 币种筛选任务已停止")
    
    def _perform_filtering(self) -> List[str]:
        """执行筛选逻辑
        
        Returns:
            筛选后的币种列表（Top N）
        """
        # 获取要评分的币种列表
        symbols_to_score = self.all_symbols if self.all_symbols else list(self.market_monitor._monitored_symbols)
        
        if not symbols_to_score:
            logger.warning("⚠️ 没有可评分的币种")
            return []
        
        # 使用 SymbolScorer 进行评分
        scored_coins = self.symbol_scorer.score_symbols(symbols_to_score, self.market_monitor)
        
        if not scored_coins:
            logger.warning("⚠️ 评分结果为空")
            return []
        
        # 按分数排序，选择Top 20
        scored_coins.sort(key=lambda x: x['score'], reverse=True)
        top_n = 20
        top_symbols = [coin['symbol'] for coin in scored_coins[:top_n]]
        
        logger.debug(f"📊 AI评分Top {top_n}: {[(c['symbol'], c['score']) for c in scored_coins[:top_n]]}")
        
        return top_symbols
    
    def get_filtered_symbols(self) -> List[str]:
        """获取筛选后的币种列表（对应 Nofx 的 FilterSymbol）"""
        with self._filtered_symbols_lock:
            return self.filtered_symbols.copy()

