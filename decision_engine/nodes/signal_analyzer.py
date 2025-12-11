from decision_engine.state import DecisionState
from utils.logger import logger
from services.market.api_client import APIClient
from services.market.feature_engine import FeatureEngine, MarketFeatures
from typing import Optional, Dict
from dataclasses import asdict

# 前向引用，避免循环导入
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from services.market.performance import PerformanceAnalyzer
    from config.settings import Settings

class SignalAnalyzer:
    """信号分析节点 - 计算技术指标和流动性过滤（使用FeatureEngine）"""
    
    # 流动性阈值（USD）
    LIQUIDITY_THRESHOLD_EXISTING = 5_000_000  # 持仓币种：5M USD
    LIQUIDITY_THRESHOLD_NEW = 15_000_000  # 新币种：15M USD
    
    def __init__(
        self, 
        trader_id: Optional[str] = None,
        settings: Optional['Settings'] = None
    ):
        """
        初始化信号分析节点
        
        Args:
            trader_id: 交易员ID
            settings: 设置对象
        """
        self.trader_id = trader_id
        self.settings = settings
        self.api_client: Optional[APIClient] = None  # 延迟初始化
        self.feature_engine: Optional[FeatureEngine] = None  # 延迟初始化
        self.performance_analyzer = None
        
        # 如果提供了 trader_id 和 settings，初始化性能分析器
        if trader_id and settings:
            try:
                from services.market.performance import PerformanceAnalyzer
                self.performance_analyzer = PerformanceAnalyzer(settings)
            except Exception as e:
                logger.warning(f"初始化性能分析器失败: {e}")
    
    def _get_api_client(self, state: DecisionState) -> Optional[APIClient]:
        """从state获取exchange_config并创建APIClient（延迟初始化）"""
        if self.api_client:
            return self.api_client
        
        exchange_config = state.get('exchange_config')
        if exchange_config:
            self.api_client = APIClient()
            self.feature_engine = FeatureEngine(self.api_client)
            return self.api_client
        
        logger.warning("⚠️ exchange_config未设置，无法创建APIClient")
        return None


    def run(self, state: DecisionState) -> DecisionState:
        """分析信号并计算技术指标（使用FeatureEngine）"""
        # 获取API客户端（延迟初始化）
        api_client = self._get_api_client(state)
        if not api_client or not self.feature_engine:
            logger.warning("⚠️ 无法创建APIClient或FeatureEngine，跳过信号分析")
            state['signal_data_map'] = {}
            state['performance'] = None
            state['alerts'] = []
            return state
        
        market_data_map = state.get('market_data_map', {})
        existing_positions = state.get('positions', [])
        signal_data_map = {}
        
        existing_symbols = {pos.get('symbol') for pos in existing_positions if pos.get('symbol')}

        for symbol, raw_data in market_data_map.items():
            try:
                # 检查是否有错误标记
                if 'error' in raw_data:
                    logger.warning(f"{symbol}数据收集失败: {raw_data.get('error')}，跳过")
                    continue
                
                # 获取K线数据
                klines_3m = raw_data.get('klines_3m', [])
                klines_4h = raw_data.get('klines_4h', [])
                
                # 使用FeatureEngine统一计算所有特征
                features = self.feature_engine.calculate_features(symbol, klines_3m, klines_4h)
                if not features:
                    continue
                
                # 流动性过滤
                is_existing_position = symbol in existing_symbols
                if not self._check_liquidity(features, is_existing_position):
                    if not is_existing_position:
                        continue
                    # 持仓币种流动性不足时记录警告但继续处理
                
                # 转换为字典格式（使用dataclasses.asdict简化）
                signal_data_map[symbol] = asdict(features)
                
                logger.debug(f"{symbol}信号分析完成")
                
            except Exception as e:
                logger.error(f"{symbol}信号分析失败: {e}", exc_info=True)
                continue
        
        state['signal_data_map'] = signal_data_map
        
        # 计算性能指标（夏普率等）
        if self.performance_analyzer and self.trader_id:
            try:
                performance = self.performance_analyzer.get_performance_summary(self.trader_id)
                state['performance'] = performance
                logger.debug(f"性能分析完成: 夏普率={performance.get('sharpe_ratio')}")
            except Exception as e:
                logger.warning(f"性能分析失败: {e}")
                state['performance'] = None
        else:
            state['performance'] = None
        
        # 检测市场警报
        alerts = self._detect_alerts(signal_data_map)
        state['alerts'] = alerts
        if alerts:
            logger.warning(f"⚠️ 检测到 {len(alerts)} 个市场警报")
        
        logger.info(f"完成信号分析，共{len(signal_data_map)}个币种")
        return state

    def _detect_alerts(self, signal_data_map: dict) -> list:
        """检测市场警报（KISS原则：简单的阈值检测）"""
        alerts = []
        
        for symbol, signals in signal_data_map.items():
            # 1. 价格异常检测
            price_change_1h = signals.get('price_change_1h', 0)
            price_change_4h = signals.get('price_change_4h', 0)
            
            if abs(price_change_1h) > 10:
                alerts.append({
                    'symbol': symbol,
                    'type': 'price_change',
                    'severity': 'high',
                    'message': f"{symbol} 1小时价格变化异常: {price_change_1h:+.2f}%"
                })
            elif abs(price_change_1h) > 5:
                alerts.append({
                    'symbol': symbol,
                    'type': 'price_change',
                    'severity': 'medium',
                    'message': f"{symbol} 1小时价格变化较大: {price_change_1h:+.2f}%"
                })
            
            if abs(price_change_4h) > 10:
                alerts.append({
                    'symbol': symbol,
                    'type': 'price_change',
                    'severity': 'medium',
                    'message': f"{symbol} 4小时价格变化较大: {price_change_4h:+.2f}%"
                })
            
            # 2. 成交量异常检测
            current_volume_4h = signals.get('current_volume_4h', 0)
            average_volume_4h = signals.get('average_volume_4h', 0)
            
            if average_volume_4h > 0 and current_volume_4h > 0:
                volume_ratio = current_volume_4h / average_volume_4h
                if volume_ratio > 2.0:
                    alerts.append({
                        'symbol': symbol,
                        'type': 'volume_spike',
                        'severity': 'medium',
                        'message': f"{symbol} 成交量异常: 当前 {current_volume_4h:.2f} vs 平均 {average_volume_4h:.2f} (倍数: {volume_ratio:.2f}x)"
                    })
            
            # 3. 技术指标信号检测
            rsi14_4h = signals.get('rsi14_4h', 50)
            if rsi14_4h > 80:
                alerts.append({
                    'symbol': symbol,
                    'type': 'overbought',
                    'severity': 'medium',
                    'message': f"{symbol} RSI14超买: {rsi14_4h:.2f} (建议谨慎开多)"
                })
            elif rsi14_4h < 20:
                alerts.append({
                    'symbol': symbol,
                    'type': 'oversold',
                    'severity': 'medium',
                    'message': f"{symbol} RSI14超卖: {rsi14_4h:.2f} (可能反弹机会)"
                })
            
            # MACD信号检测（简单检测：MACD值的变化趋势）
            macd_4h = signals.get('macd_4h', 0)
            macd_3m = signals.get('macd_3m', 0)
            
            # 如果4小时MACD和3分钟MACD方向相反，可能存在短期波动
            if macd_4h > 0 and macd_3m < 0:
                alerts.append({
                    'symbol': symbol,
                    'type': 'macd_divergence',
                    'severity': 'low',
                    'message': f"{symbol} MACD信号分歧: 4小时看涨({macd_4h:.2f})但3分钟看跌({macd_3m:.2f})"
                })
            elif macd_4h < 0 and macd_3m > 0:
                alerts.append({
                    'symbol': symbol,
                    'type': 'macd_divergence',
                    'severity': 'low',
                    'message': f"{symbol} MACD信号分歧: 4小时看跌({macd_4h:.2f})但3分钟看涨({macd_3m:.2f})"
                })
            
            # 4. 流动性风险检测（持仓量异常下降）
            open_interest = signals.get('open_interest')
            open_interest_average = signals.get('open_interest_average')
            
            if open_interest is not None and open_interest_average is not None and open_interest_average > 0:
                oi_ratio = open_interest / open_interest_average
                if oi_ratio < 0.95:  # 持仓量下降超过5%
                    alerts.append({
                        'symbol': symbol,
                        'type': 'liquidity_risk',
                        'severity': 'medium',
                        'message': f"{symbol} 持仓量下降: 当前 {open_interest:.2f} vs 平均 {open_interest_average:.2f} (下降 {((1-oi_ratio)*100):.1f}%)"
                    })
        
        return alerts
    
    def _check_liquidity(self, features, is_existing_position: bool) -> bool:
        """检查流动性（KISS原则：简单直接的阈值检查）"""
        liquidity_threshold = self.LIQUIDITY_THRESHOLD_EXISTING if is_existing_position else self.LIQUIDITY_THRESHOLD_NEW
        
        logger.debug(f"计算{features.symbol}的流动性（{'持仓币种' if is_existing_position else '新币种'}，阈值: {liquidity_threshold/1_000_000:.0f}M USD）")
        
        if features.open_interest is None or features.open_interest <= 0:
            logger.warning(f"{features.symbol} 无法获取持仓量")
            # 对于持仓币种，即使无法获取也继续处理（避免误平仓）
            return is_existing_position
        
        # 计算持仓价值（USD）= 持仓量（合约数量）× 当前价格
        oi_value_usd = features.open_interest * features.current_price
        
        logger.debug(f"{features.symbol} 持仓量: {features.open_interest:.2f}, 持仓价值: {oi_value_usd/1_000_000:.2f}M USD")
        
        if oi_value_usd < liquidity_threshold:
            threshold_str = f"{self.LIQUIDITY_THRESHOLD_EXISTING/1_000_000:.0f}M" if is_existing_position else f"{self.LIQUIDITY_THRESHOLD_NEW/1_000_000:.0f}M"
            logger.warning(
                f"{features.symbol} 流动性不足 "
                f"(持仓价值: {oi_value_usd/1_000_000:.2f}M USD < {threshold_str})"
            )
            return False
        
        return True
    


            