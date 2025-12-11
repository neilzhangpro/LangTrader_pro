"""
市场特征引擎 - 统一计算所有市场特征
类似 NOFX 的 feature_engine.go，集中管理所有特征计算
"""
from dataclasses import dataclass
from typing import List, Optional, Dict
from services.market.type import Kline
from services.market.indicators import IndicatorCalculator
from services.market.api_client import APIClient
from utils.logger import logger


@dataclass
class MarketFeatures:
    """市场特征数据类（统一的数据结构）"""
    # 基础价格信息
    symbol: str
    current_price: float
    price_change_1h: float
    price_change_4h: float
    
    # 3分钟指标
    ema20_3m: float
    macd_3m: float
    rsi7_3m: float
    rsi14_3m: float
    
    # 4小时指标
    ema20_4h: float
    ema50_4h: float
    macd_4h: float
    rsi7_4h: float
    rsi14_4h: float
    atr_4h: float
    atr3_4h: float
    
    # 成交量统计
    current_volume_4h: float
    average_volume_4h: float
    
    # 持仓量和资金费率
    open_interest: Optional[float]
    open_interest_average: Optional[float]
    funding_rate: Optional[float]
    
    # 序列数据
    intraday_series: Dict  # 3分钟序列
    longer_term_series: Dict  # 4小时序列


class FeatureEngine:
    """市场特征引擎 - 统一计算所有市场特征（KISS原则：简单直接）"""
    
    # 配置常量（集中管理）
    EMA_SHORT_PERIOD = 20
    EMA_LONG_PERIOD = 50
    RSI_SHORT_PERIOD = 7
    RSI_LONG_PERIOD = 14
    ATR_PERIOD = 14
    ATR_SHORT_PERIOD = 3
    MIN_KLINES_REQUIRED = 20
    PRICE_CHANGE_1H_KLINES = 20
    PRICE_CHANGE_4H_KLINES = 2
    
    def __init__(self, api_client: APIClient):
        """初始化特征引擎"""
        self.api_client = api_client
    
    def calculate_features(
        self,
        symbol: str,
        klines_3m: List[Kline],
        klines_4h: List[Kline],
        skip_api_calls: bool = False
    ) -> Optional[MarketFeatures]:
        """
        统一入口：计算所有市场特征
        
        Args:
            symbol: 币种符号
            klines_3m: 3分钟K线数据
            klines_4h: 4小时K线数据
            skip_api_calls: 是否跳过API调用（用于评分等场景，提升性能）
        
        Returns:
            MarketFeatures对象，如果数据不足则返回None
        """
        # 1. 数据验证
        if not self._validate_klines(klines_3m, klines_4h):
            return None
        
        # 2. 计算基础价格信息
        current_price = self._get_current_price(klines_3m, klines_4h)
        price_change_1h = self._calculate_price_change(
            klines_3m, self.PRICE_CHANGE_1H_KLINES, current_price
        )
        price_change_4h = self._calculate_price_change(
            klines_4h, self.PRICE_CHANGE_4H_KLINES, current_price
        )
        
        # 3. 计算技术指标
        indicators_3m = self._calculate_indicators(klines_3m, timeframe='3m')
        indicators_4h = self._calculate_indicators(klines_4h, timeframe='4h')
        
        # 4. 计算成交量统计
        volume_stats = IndicatorCalculator.calculate_volume_stats(klines_4h)
        
        # 5. 获取持仓量和资金费率（仅在需要时调用API）
        if skip_api_calls:
            open_interest = None
            funding_rate = None
            open_interest_average = None
        else:
            open_interest = self.api_client.get_open_interest(symbol)
            funding_rate_data = self.api_client.get_funding_rate(symbol)
            funding_rate = self._extract_funding_rate(funding_rate_data)
            open_interest_average = open_interest * 0.999 if open_interest else None
        
        # 6. 计算序列指标
        intraday_series = IndicatorCalculator.calculate_series_indicators(klines_3m)
        longer_term_series = IndicatorCalculator.calculate_series_indicators(klines_4h)
        
        # 7. 组装特征对象
        return MarketFeatures(
            symbol=symbol,
            current_price=current_price,
            price_change_1h=price_change_1h,
            price_change_4h=price_change_4h,
            # 3分钟指标
            ema20_3m=indicators_3m['ema20'],
            macd_3m=indicators_3m['macd'],
            rsi7_3m=indicators_3m['rsi7'],
            rsi14_3m=indicators_3m['rsi14'],
            # 4小时指标
            ema20_4h=indicators_4h['ema20'],
            ema50_4h=indicators_4h['ema50'],
            macd_4h=indicators_4h['macd'],
            rsi7_4h=indicators_4h['rsi7'],
            rsi14_4h=indicators_4h['rsi14'],
            atr_4h=indicators_4h['atr'],
            atr3_4h=indicators_4h['atr3'],
            # 成交量
            current_volume_4h=volume_stats['current_volume'],
            average_volume_4h=volume_stats['average_volume'],
            # 持仓量和资金费率
            open_interest=open_interest,
            open_interest_average=open_interest_average,
            funding_rate=funding_rate,
            # 序列数据
            intraday_series=intraday_series,
            longer_term_series=longer_term_series,
        )
    
    def _validate_klines(self, klines_3m: List[Kline], klines_4h: List[Kline]) -> bool:
        """验证K线数据质量"""
        if not klines_3m or not klines_4h:
            return False
        return (len(klines_3m) >= self.MIN_KLINES_REQUIRED and 
                len(klines_4h) >= self.MIN_KLINES_REQUIRED)
    
    def _get_current_price(self, klines_3m: List[Kline], klines_4h: List[Kline]) -> float:
        """获取当前价格（优先使用3分钟K线）"""
        if klines_3m:
            return klines_3m[-1].close
        elif klines_4h:
            return klines_4h[-1].close
        return 0.0
    
    def _calculate_price_change(
        self, 
        klines: List[Kline], 
        lookback: int, 
        current_price: float
    ) -> float:
        """计算价格变化百分比"""
        if len(klines) < lookback:
            return 0.0
        price_ago = klines[-lookback].close
        if price_ago > 0:
            return ((current_price - price_ago) / price_ago) * 100
        return 0.0
    
    def _calculate_indicators(self, klines: List[Kline], timeframe: str) -> Dict:
        """计算技术指标（统一方法）"""
        indicators = {
            'ema20': IndicatorCalculator.calculate_ema(klines, self.EMA_SHORT_PERIOD),
            'macd': IndicatorCalculator.calculate_macd(klines),
            'rsi7': IndicatorCalculator.calculate_rsi(klines, self.RSI_SHORT_PERIOD),
            'rsi14': IndicatorCalculator.calculate_rsi(klines, self.RSI_LONG_PERIOD),
        }
        
        # 4小时K线需要额外计算EMA50和ATR
        if timeframe == '4h':
            indicators['ema50'] = IndicatorCalculator.calculate_ema(klines, self.EMA_LONG_PERIOD)
            indicators['atr'] = IndicatorCalculator.calculate_atr(klines, self.ATR_PERIOD)
            indicators['atr3'] = IndicatorCalculator.calculate_atr3(klines)
        else:
            indicators['ema50'] = 0.0
            indicators['atr'] = 0.0
            indicators['atr3'] = 0.0
        
        return indicators
    
    def _extract_funding_rate(self, funding_rate_data) -> Optional[float]:
        """提取资金费率"""
        if not funding_rate_data:
            return None
        if isinstance(funding_rate_data, dict):
            return funding_rate_data.get('fundingRate') or funding_rate_data.get('rate')
        elif isinstance(funding_rate_data, (int, float)):
            return float(funding_rate_data)
        return None

