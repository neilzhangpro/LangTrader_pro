"""
币种筛选器 - 管理筛选后的币种列表（对应 Nofx 的 FilterSymbol）
整合了币种评分功能
"""
import threading
import time
from typing import List, Optional
from utils.logger import logger
from services.market.indicators import IndicatorCalculator
from services.market.feature_engine import FeatureEngine
from services.market.api_client import APIClient

# 前向引用，避免循环导入
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from services.market.monitor import MarketMonitor


class SymbolFilter:
    """币种筛选器 - 管理筛选后的币种列表（整合了评分功能）"""
    
    # 筛选配置常量
    TOP_N = 20  # 选择Top N个币种
    
    def __init__(
        self, 
        market_monitor: 'MarketMonitor', 
        api_client: Optional[APIClient] = None,
        all_symbols: Optional[List[str]] = None,
        running_flag: Optional[threading.Event] = None
    ):
        """初始化币种筛选器
        
        Args:
            market_monitor: 市场监控器，用于获取K线数据
            api_client: API客户端（用于FeatureEngine，可选）
            all_symbols: 所有可交易币种列表
            running_flag: 运行标志，用于控制筛选任务的生命周期
        """
        self.market_monitor = market_monitor
        self.all_symbols = all_symbols or []
        self.running_flag = running_flag
        
        # 初始化FeatureEngine（如果提供了api_client）
        self.feature_engine = None
        if api_client:
            self.feature_engine = FeatureEngine(api_client)
        
        # 筛选后的币种列表（对应 Nofx 的 FilterSymbol）
        self.filtered_symbols: List[str] = []
        self._filtered_symbols_lock = threading.Lock()
        
        # 筛选任务线程
        self._filtering_thread: Optional[threading.Thread] = None
        self._running = False
        
        logger.info("SymbolFilter 初始化完成（整合评分功能）")
    
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
            logger.info("🚀 币种筛选任务已启动")
            
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
                    
                    logger.info(f"✅ 币种筛选完成，筛选出 {len(filtered)} 个币种")
                except Exception as e:
                    logger.error(f"❌ 币种筛选失败: {e}", exc_info=True)
                
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
    
    def get_filtered_symbols(self) -> List[str]:
        """获取筛选后的币种列表（对应 Nofx 的 FilterSymbol）"""
        with self._filtered_symbols_lock:
            return self.filtered_symbols.copy()
    
    def _perform_filtering(self) -> List[str]:
        """执行筛选逻辑
        
        Returns:
            筛选后的币种列表（Top N）
        """
        # 如果 all_symbols 为空，等待数据准备好（数据正在后台加载）
        if not self.all_symbols:
            logger.debug("⏳ 等待币种数据加载完成...")
            return []  # 返回空列表，等待下次循环
        
        # 获取要评分的币种列表
        symbols_to_score = self.all_symbols if self.all_symbols else list(self.market_monitor._monitored_symbols)
        
        if not symbols_to_score:
            logger.warning("⚠️ 没有可评分的币种")
            return []
        
        # 使用技术指标进行评分
        scored_coins = self._score_symbols(symbols_to_score)
        
        if not scored_coins:
            logger.warning("⚠️ 评分结果为空")
            return []
        
        # 按分数排序，选择Top N
        scored_coins.sort(key=lambda x: x.get('score', 0), reverse=True)
        top_symbols = [coin.get('symbol') for coin in scored_coins[:self.TOP_N] if coin.get('symbol')]
        
        logger.debug(f"📊 技术指标评分Top {self.TOP_N}: {[(c.get('symbol', 'N/A'), c.get('score', 0)) for c in scored_coins[:self.TOP_N]]}")
        
        return top_symbols
    
    def _score_symbols(self, symbols: List[str]) -> List[dict]:
        """批量评分币种（使用技术指标）
        
        Args:
            symbols: 要评分的币种列表
            
        Returns:
            评分结果列表，每个元素包含 {'symbol': str, 'score': int}
        """
        scored_coins = []
        
        logger.info(f"📊 开始使用技术指标对 {len(symbols)} 个币种进行评分...")
        
        for symbol in symbols:
            try:
                klines_3m = self.market_monitor.get_klines(symbol, "3m", limit=100)
                klines_4h = self.market_monitor.get_klines(symbol, "4h", limit=100)
                
                # 使用FeatureEngine计算特征（轻量级模式，跳过API调用）
                if self.feature_engine:
                    features = self.feature_engine.calculate_features(
                        symbol, klines_3m, klines_4h, skip_api_calls=True
                    )
                    if not features:
                        continue
                    score = self._calculate_score_from_features(features)
                else:
                    # FeatureEngine不可用，跳过该币种
                    logger.warning(f"⚠️ {symbol} FeatureEngine不可用，跳过评分（建议检查配置）")
                    continue
                
                scored_coins.append({
                    'symbol': symbol,
                    'score': score
                })
            except Exception as e:
                logger.debug(f"⚠️ {symbol} 评分失败: {e}")
                continue
        
        logger.info(f"✅ 技术指标评分完成，共评分 {len(scored_coins)} 个币种")
        return scored_coins
    
    def _calculate_score_from_features(self, features) -> int:
        """基于MarketFeatures计算评分（KISS原则：简单直接的算法）"""
        score = 50  # 基础分
        
        # 价格相对EMA位置（3分钟）
        if features.current_price > features.ema20_3m:
            score += 10
        else:
            score -= 10
        
        # 价格相对EMA位置（4小时）
        if features.current_price > features.ema20_4h:
            score += 15
        else:
            score -= 15
        
        # MACD信号（3分钟）
        if features.macd_3m > 0:
            score += 10
        else:
            score -= 10
        
        # MACD信号（4小时）
        if features.macd_4h > 0:
            score += 15
        else:
            score -= 15
        
        # RSI状态（避免极端超买/超卖）
        if 30 < features.rsi14_3m < 70:
            score += 5
        if 30 < features.rsi14_4h < 70:
            score += 5
        
        # 确保分数在0-100范围内
        return max(0, min(100, score))
