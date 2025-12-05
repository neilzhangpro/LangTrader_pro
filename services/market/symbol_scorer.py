"""
币种评分器 - 使用AI或技术指标对币种进行评分
"""
from typing import List, Dict, Optional
import re
from utils.logger import logger
from services.market.indicators import IndicatorCalculator
from langchain_core.messages import SystemMessage, HumanMessage

# 前向引用，避免循环导入
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from services.market.monitor import MarketMonitor


class SymbolScorer:
    """币种评分器 - 使用AI或技术指标对币种进行评分"""
    
    def __init__(self, ai_model_config: Optional[dict] = None):
        """初始化币种评分器
        
        Args:
            ai_model_config: AI模型配置，如果提供且enabled=True，将使用LLM评分
        """
        self.ai_model_config = ai_model_config
        self.llm = None
        if ai_model_config and ai_model_config.get('enabled'):
            self.llm = self._init_llm(ai_model_config)
            if self.llm:
                logger.info("✅ AI模型已初始化，将使用LLM进行币种评分")
            else:
                logger.warning("⚠️ AI模型初始化失败，将回退到技术指标评分")
    
    def _init_llm(self, ai_model_config: dict):
        """初始化LLM（复用 AIDecision 的逻辑）"""
        from langchain_openai import ChatOpenAI
        from langchain_anthropic import ChatAnthropic
        from langchain_ollama import ChatOllama
        
        provider = ai_model_config.get('provider', 'ollama')
        
        try:
            if provider == 'openai':
                return ChatOpenAI(
                    model=ai_model_config.get('model_name', 'gpt-4'),
                    api_key=ai_model_config.get('api_key', ''),
                    base_url=ai_model_config.get('base_url', ''),
                    temperature=0.0,
                )
            elif provider == 'anthropic':
                return ChatAnthropic(
                    model=ai_model_config.get('model_name', 'claude-3-5-sonnet-20241022'),
                    api_key=ai_model_config.get('api_key', ''),
                    base_url=ai_model_config.get('base_url', ''),
                    temperature=0.0,
                )
            elif provider == 'ollama':
                return ChatOllama(
                    model=ai_model_config.get('model_name', 'qwen2.5:7b'),
                    temperature=0.0,
                    base_url=ai_model_config.get('base_url', 'http://localhost:11434'),
                )
            else:
                logger.warning(f"⚠️ 不支持的LLM提供商: {provider}")
                return None
        except Exception as e:
            logger.error(f"❌ 初始化LLM失败: {e}", exc_info=True)
            return None
    
    def score_symbols(self, symbols: List[str], market_monitor: 'MarketMonitor') -> List[dict]:
        """批量评分币种
        
        Args:
            symbols: 要评分的币种列表
            market_monitor: MarketMonitor实例，用于获取K线数据
            
        Returns:
            评分结果列表，每个元素包含 {'symbol': str, 'score': int}
        """
        if self.llm:
            return self._score_with_llm(symbols, market_monitor)
        else:
            return self._score_with_technical(symbols, market_monitor)
    
    def _score_with_llm(self, symbols: List[str], market_monitor: 'MarketMonitor') -> List[dict]:
        """使用LLM进行评分"""
        scored_coins = []
        
        logger.info(f"🤖 开始使用LLM对 {len(symbols)} 个币种进行AI评分...")
        
        # 批量处理（每批10个币种，避免token过多）
        batch_size = 10
        for i in range(0, len(symbols), batch_size):
            batch_symbols = symbols[i:i+batch_size]
            batch_scores = self._score_batch_with_llm(batch_symbols, market_monitor)
            scored_coins.extend(batch_scores)
            
            if (i + batch_size) % 50 == 0:
                logger.info(f"📊 已评分 {min(i + batch_size, len(symbols))}/{len(symbols)} 个币种...")
        
        logger.info(f"✅ AI评分完成，共评分 {len(scored_coins)} 个币种")
        return scored_coins
    
    def _score_batch_with_llm(self, symbols: List[str], market_monitor: 'MarketMonitor') -> List[dict]:
        """使用LLM批量评分币种"""
        scored_coins = []
        
        for symbol in symbols:
            try:
                # 获取K线数据
                klines_3m = market_monitor.get_klines(symbol, "3m", limit=100)
                klines_4h = market_monitor.get_klines(symbol, "4h", limit=100)
                
                if not klines_3m or not klines_4h or len(klines_3m) < 20 or len(klines_4h) < 20:
                    continue
                
                # 计算技术指标
                ema20_3m = IndicatorCalculator.calculate_ema(klines_3m, 20)
                ema20_4h = IndicatorCalculator.calculate_ema(klines_4h, 20)
                ema50_4h = IndicatorCalculator.calculate_ema(klines_4h, 50)
                macd_3m = IndicatorCalculator.calculate_macd(klines_3m)
                macd_4h = IndicatorCalculator.calculate_macd(klines_4h)
                rsi7_3m = IndicatorCalculator.calculate_rsi(klines_3m, 7)
                rsi14_3m = IndicatorCalculator.calculate_rsi(klines_3m, 14)
                rsi14_4h = IndicatorCalculator.calculate_rsi(klines_4h, 14)
                atr_4h = IndicatorCalculator.calculate_atr(klines_4h, 14)
                
                current_price = klines_3m[-1].close
                
                # 计算价格变化
                price_change_1h = 0.0
                if len(klines_3m) >= 20:
                    price_1h_ago = klines_3m[-20].close
                    price_change_1h = (current_price - price_1h_ago) / price_1h_ago * 100
                
                price_change_4h = 0.0
                if len(klines_4h) >= 2:
                    price_4h_ago = klines_4h[-2].close
                    price_change_4h = (current_price - price_4h_ago) / price_4h_ago * 100 if price_4h_ago > 0 else 0.0
                
                # 构建提示词
                system_prompt = """你是一个专业的加密货币交易分析师。你的任务是对币种进行综合评分（0-100分），评估其交易潜力。

评分标准：
1. 技术指标信号强度（40分）
   - EMA趋势：价格相对EMA20/EMA50的位置
   - MACD信号：金叉/死叉、动量强度
   - RSI状态：超买/超卖程度
   - ATR波动率：市场活跃度

2. 价格动量（30分）
   - 短期价格变化（1小时）
   - 中期价格变化（4小时）
   - 价格趋势一致性

3. 市场结构（30分）
   - 多时间框架一致性（3分钟 vs 4小时）
   - 趋势强度
   - 突破潜力

请只返回一个0-100的整数分数，不要其他解释。"""

                user_prompt = f"""币种: {symbol}

【价格信息】
- 当前价格: {current_price:.4f}
- 1小时涨跌: {price_change_1h:+.2f}%
- 4小时涨跌: {price_change_4h:+.2f}%

【3分钟指标】
- EMA20: {ema20_3m:.4f} (价格{'高于' if current_price > ema20_3m else '低于'}EMA20)
- MACD: {macd_3m:.4f} ({'看涨' if macd_3m > 0 else '看跌'})
- RSI7: {rsi7_3m:.2f}
- RSI14: {rsi14_3m:.2f} ({'超买' if rsi14_3m > 70 else '超卖' if rsi14_3m < 30 else '正常'})

【4小时指标】
- EMA20: {ema20_4h:.4f} (价格{'高于' if current_price > ema20_4h else '低于'}EMA20)
- EMA50: {ema50_4h:.4f}
- MACD: {macd_4h:.4f} ({'看涨' if macd_4h > 0 else '看跌'})
- RSI14: {rsi14_4h:.2f} ({'超买' if rsi14_4h > 70 else '超卖' if rsi14_4h < 30 else '正常'})
- ATR: {atr_4h:.4f} (波动率)

请给出综合评分（0-100的整数）："""

                # 调用LLM
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt)
                ]
                
                response = self.llm.invoke(messages)
                
                # 解析分数
                score_text = response.content.strip()
                # 尝试提取数字
                score_match = re.search(r'\d+', score_text)
                if score_match:
                    score = int(score_match.group())
                    score = max(0, min(100, score))  # 确保在0-100范围内
                else:
                    logger.warning(f"⚠️ {symbol} LLM返回格式异常: {score_text}，使用默认分50")
                    score = 50
                
                scored_coins.append({
                    'symbol': symbol,
                    'score': score
                })
                
            except Exception as e:
                logger.debug(f"⚠️ {symbol} AI评分失败: {e}")
                continue
        
        return scored_coins
    
    def _score_with_technical(self, symbols: List[str], market_monitor: 'MarketMonitor') -> List[dict]:
        """使用技术指标进行评分（回退方案）"""
        scored_coins = []
        
        logger.info(f"📊 开始使用技术指标对 {len(symbols)} 个币种进行评分...")
        
        for symbol in symbols:
            try:
                klines_3m = market_monitor.get_klines(symbol, "3m", limit=100)
                klines_4h = market_monitor.get_klines(symbol, "4h", limit=100)
                
                if not klines_3m or not klines_4h or len(klines_3m) < 20 or len(klines_4h) < 20:
                    continue
                
                # 计算技术指标
                ema20_3m = IndicatorCalculator.calculate_ema(klines_3m, 20)
                ema20_4h = IndicatorCalculator.calculate_ema(klines_4h, 20)
                macd_3m = IndicatorCalculator.calculate_macd(klines_3m)
                macd_4h = IndicatorCalculator.calculate_macd(klines_4h)
                rsi14_3m = IndicatorCalculator.calculate_rsi(klines_3m, 14)
                rsi14_4h = IndicatorCalculator.calculate_rsi(klines_4h, 14)
                
                current_price = klines_3m[-1].close
                
                # 简化的评分算法（0-100分）
                score = 50  # 基础分
                
                # 价格相对EMA位置（3分钟）
                if current_price > ema20_3m:
                    score += 10
                else:
                    score -= 10
                
                # 价格相对EMA位置（4小时）
                if current_price > ema20_4h:
                    score += 15
                else:
                    score -= 15
                
                # MACD信号（3分钟）
                if macd_3m > 0:
                    score += 10
                else:
                    score -= 10
                
                # MACD信号（4小时）
                if macd_4h > 0:
                    score += 15
                else:
                    score -= 15
                
                # RSI状态（避免极端超买/超卖）
                if 30 < rsi14_3m < 70:
                    score += 5
                if 30 < rsi14_4h < 70:
                    score += 5
                
                # 确保分数在0-100范围内
                score = max(0, min(100, score))
                
                scored_coins.append({
                    'symbol': symbol,
                    'score': score
                })
            except Exception as e:
                logger.debug(f"⚠️ {symbol} 评分失败: {e}")
                continue
        
        logger.info(f"✅ 技术指标评分完成，共评分 {len(scored_coins)} 个币种")
        return scored_coins

