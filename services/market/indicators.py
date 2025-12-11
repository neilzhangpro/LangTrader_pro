import pandas as pd
import pandas_ta as ta
from typing import List
from services.market.type import Kline

class IndicatorCalculator:
    """技术指标计算器（使用 pandas-ta）"""
    
    @staticmethod
    def calculate_ema(klines: List[Kline], period: int) -> float:
        """计算 EMA"""
        if len(klines) < period:
            return 0.0
        
        df = pd.DataFrame([{
            'close': k.close,
            'open': k.open,
            'high': k.high,
            'low': k.low,
            'volume': k.volume
        } for k in klines])
        
        ema = ta.ema(df['close'], length=period)
        return float(ema.iloc[-1]) if not ema.empty else 0.0
    
    @staticmethod
    def calculate_macd(klines: List[Kline]) -> float:
        """计算 MACD"""
        if len(klines) < 26:
            return 0.0
        
        df = pd.DataFrame([k.close for k in klines], columns=['close'])
        macd = ta.macd(df['close'])
        return float(macd['MACD_12_26_9'].iloc[-1]) if not macd.empty else 0.0
    
    @staticmethod
    def calculate_rsi(klines: List[Kline], period: int = 7) -> float:
        """计算 RSI"""
        if len(klines) <= period:
            return 0.0
        
        df = pd.DataFrame([k.close for k in klines], columns=['close'])
        rsi = ta.rsi(df['close'], length=period)
        return float(rsi.iloc[-1]) if not rsi.empty else 0.0
    
    @staticmethod
    def calculate_atr(klines: List[Kline], period: int = 14) -> float:
        """计算 ATR"""
        if len(klines) <= period:
            return 0.0
        
        df = pd.DataFrame([{
            'high': k.high,
            'low': k.low,
            'close': k.close
        } for k in klines])
        
        atr = ta.atr(df['high'], df['low'], df['close'], length=period)
        return float(atr.iloc[-1]) if not atr.empty else 0.0
    
    @staticmethod
    def calculate_atr3(klines: List[Kline]) -> float:
        """计算 ATR（3周期）- 用于4小时K线的短期波动率"""
        return IndicatorCalculator.calculate_atr(klines, period=3)
    
    @staticmethod
    def calculate_volume_stats(klines: List[Kline]) -> dict:
        """计算成交量统计（当前成交量和平均成交量）"""
        if not klines:
            return {
                'current_volume': 0.0,
                'average_volume': 0.0
            }
        
        df = pd.DataFrame([{
            'volume': k.volume
        } for k in klines])
        
        current_volume = float(df['volume'].iloc[-1]) if len(df) > 0 else 0.0
        average_volume = float(df['volume'].mean()) if len(df) > 0 else 0.0
        
        return {
            'current_volume': current_volume,
            'average_volume': average_volume
        }
    
    @staticmethod
    def calculate_series_indicators(klines: List[Kline], periods: List[int] = None) -> dict:
        """计算序列指标（用于历史分析）"""
        if periods is None:
            periods = [7, 14, 20]
        
        df = pd.DataFrame([{
            'close': k.close,
            'high': k.high,
            'low': k.low,
            'volume': k.volume
        } for k in klines])
        
        result = {
            'mid_prices': df['close'].tolist(),
            'ema20_values': ta.ema(df['close'], length=20).tolist() if len(klines) >= 20 else [],
            'macd_values': ta.macd(df['close'])['MACD_12_26_9'].tolist() if len(klines) >= 26 else [],
            'rsi7_values': ta.rsi(df['close'], length=7).tolist() if len(klines) > 7 else [],
            'rsi14_values': ta.rsi(df['close'], length=14).tolist() if len(klines) > 14 else [],
        }
        
        return result