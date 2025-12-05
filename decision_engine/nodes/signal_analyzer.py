from decision_engine.state import DecisionState
from utils.logger import logger
from services.market.indicators import IndicatorCalculator
from services.market.api_client import APIClient

class SignalAnalyzer:
    def __init__(self, exchange_config: dict):
        self.api_client = APIClient(exchange_config)
        logger.info(f"SignalAnalyzer initialized")

    def run(self, state: DecisionState):
        logger.info(f"SignalAnalyzer run")
        #分析信号
        market_data_map = state.get('market_data_map',{})
        existing_positions = state.get('positions',[])
        signal_data_map = {}

        for symbol, raw_data in market_data_map.items():
            try:
                #1. 计算技术指标
                klines_3m = raw_data.get('klines_3m',[])
                klines_4h = raw_data.get('klines_4h',[])

                #使用indicators计算技术指标
                ema20_3m = IndicatorCalculator.calculate_ema(klines_3m, 20)
                ema20_4h = IndicatorCalculator.calculate_ema(klines_4h, 20)
                ema50_4h = IndicatorCalculator.calculate_ema(klines_4h, 50)
                macd_3m = IndicatorCalculator.calculate_macd(klines_3m)
                macd_4h = IndicatorCalculator.calculate_macd(klines_4h)
                rsi7_3m = IndicatorCalculator.calculate_rsi(klines_3m, 7)
                rsi7_4h = IndicatorCalculator.calculate_rsi(klines_4h, 7)
                rsi14_3m = IndicatorCalculator.calculate_rsi(klines_3m, 14)
                rsi14_4h = IndicatorCalculator.calculate_rsi(klines_4h, 14)
                atr_4h = IndicatorCalculator.calculate_atr(klines_4h, 14)
                
                #3.计算价格变化
                # 获取当前价格（优先使用3分钟K线，如果没有则使用4小时K线）
                if len(klines_3m) > 0:
                    current_price = klines_3m[-1].close
                elif len(klines_4h) > 0:
                    current_price = klines_4h[-1].close
                else:
                    logger.warning(f"⚠️ {symbol} 没有K线数据，跳过")
                    continue
                
                # 计算1小时价格变化
                if len(klines_3m) >= 20:
                    price_1h_ago = klines_3m[-20].close  # 约1小时前（20根3分钟K线）
                    price_change_1h = (current_price - price_1h_ago) / price_1h_ago * 100
                else:
                    price_change_1h = 0.0
                
                # 计算4小时价格变化（使用前一根4小时K线的收盘价）
                if len(klines_4h) >= 2:
                    price_4h_ago = klines_4h[-2].close  # 前一根4小时K线（约4小时前）
                    price_change_4h = (current_price - price_4h_ago) / price_4h_ago * 100 if price_4h_ago > 0 else 0.0
                else:
                    price_change_4h = 0.0
                
                # 5.流动性过滤
                existing_symbols = {pos.get('symbol') for pos in existing_positions if pos.get('symbol')}
                is_existing_position = symbol in existing_symbols
                
                if not is_existing_position:
                    logger.info(f"🔍 计算 {symbol} 的流动性")
                    
                    # 获取持仓量（合约数量）
                    open_interest = self.api_client.get_open_interest(symbol)
                    
                    if open_interest is None or open_interest <= 0:
                        logger.debug(f"⚠️ {symbol} 无法获取持仓量，假设流动性充足")
                        # 无法获取时，不过滤（假设流动性充足）
                    else:
                        # 计算持仓价值（USD）= 持仓量（合约数量）× 当前价格
                        oi_value_usd = open_interest * current_price
                        
                        logger.info(f"📊 {symbol} 持仓量: {open_interest:.2f}, 持仓价值: {oi_value_usd/1_000_000:.2f}M USD")
                        
                        if oi_value_usd < 15_000_000:  # 15M USD
                            logger.warning(
                                f"⚠️ {symbol} 流动性不足 "
                                f"(持仓价值: {oi_value_usd/1_000_000:.2f}M USD < 15M)，跳过"
                            )
                            continue  # 跳过此币种
                #6 计算序列指标(用于AI分析历史趋势)
                intraday_series = IndicatorCalculator.calculate_series_indicators(klines_3m)
                longer_term_series = IndicatorCalculator.calculate_series_indicators(klines_4h)
                # 7. 格式化数据（准备给AI使用）
                signal_data_map[symbol] = {
                    'current_price': current_price,
                    'price_change_1h': price_change_1h,
                    'price_change_4h': price_change_4h,
                    
                    # 3分钟指标
                    'ema20_3m': ema20_3m,
                    'macd_3m': macd_3m,
                    'rsi7_3m': rsi7_3m,
                    'rsi7_4h': rsi7_4h,
                    'rsi14_3m': rsi14_3m,
                    
                    # 4小时指标
                    'ema20_4h': ema20_4h,
                    'ema50_4h': ema50_4h,
                    'macd_4h': macd_4h,
                    'rsi14_4h': rsi14_4h,
                    'atr_4h': atr_4h,
                    
                    # 序列数据（用于AI分析）
                    'intraday_series': intraday_series,
                    'longer_term_series': longer_term_series,
                }
                
                logger.debug(f"✅ {symbol} 信号分析完成")
                
            except Exception as e:
                logger.error(f"❌ {symbol} 信号分析失败: {e}", exc_info=True)
                continue
        
        state['signal_data_map'] = signal_data_map
        #logger.debug(f"📝 signal_data_map: {signal_data_map}")
        logger.info(f"✅ 完成信号分析，共 {len(signal_data_map)} 个币种")
        return state



            