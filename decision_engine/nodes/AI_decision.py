from decision_engine.state import DecisionState
from utils.logger import logger
from pprint import pprint
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage
from typing import Optional

class AIDecision:
    def __init__(self, exchange_config: dict, trader_cfg: dict, exchange_service: Optional):
        self.exchange_config = exchange_config
        self.trader_cfg = trader_cfg
        logger.info(f"--AIDecision initialized--")
        logger.info(f"exchange_config:{self.exchange_config}")
        if not self.trader_cfg['ai_model']['enabled']:
            logger.warning(f"AI模型未启用，跳过AI决策")
            return
        self.llm = self._get_llm(self.trader_cfg['ai_model']['provider'])
        self.system_prompt = self.trader_cfg['prompt']
        self.exchange_service = exchange_service
        logger.info(f"exchange_service initialized")
        logger.info(f"exchange balance:{self.exchange_service.get_balance()}")


    def _get_llm(self,llm_provider: str):
        if llm_provider == 'openai': #兼容所有openai api 协议的SDK，包括google\deepseek等
            return ChatOpenAI(
                model = self.trader_cfg['ai_model']['model_name'],
                api_key = self.trader_cfg['ai_model']['api_key'],
                base_url = self.trader_cfg['ai_model']['base_url'],
                temperature = 0.0,
            )
        elif llm_provider == 'anthropic':#anthropic api 协议的SDK
            return ChatAnthropic(
                model = self.trader_cfg['ai_model']['model_name'],
                api_key = self.trader_cfg['ai_model']['api_key'],
                base_url = self.trader_cfg['ai_model']['base_url'],
                temperature = 0.0,
            )
        
        elif llm_provider == 'ollama':#ollama api 协议的SDK
            return ChatOllama(
                model = self.trader_cfg['ai_model']['model_name'],
                temperature = 0.0,
                base_url = self.trader_cfg['ai_model']['base_url'],
            )
       
    def _format_market_data(self, market_data_map: dict) -> str:
        """格式化市场数据，保留K线但结构化展示"""
        if not market_data_map:
            return "无市场数据"
        
        formatted_lines = []
        for symbol, data in market_data_map.items():
            current_price = data.get('current_price')
            klines_3m = data.get('klines_3m', [])
            klines_4h = data.get('klines_4h', [])
            source = data.get('source', 'unknown')
            
            # 修复：先格式化价格，避免在格式说明符中使用三元表达式
            price_str = f"{current_price:.2f}" if current_price is not None else "N/A"
            
            # 格式化3分钟K线（显示最近20根的关键信息）
            klines_3m_str = ""
            if klines_3m:
                recent_3m = klines_3m[-20:] if len(klines_3m) > 20 else klines_3m
                klines_3m_str = "\n".join([
                    f"        [{i+1}] 时间: {kline.open_time if hasattr(kline, 'open_time') else 'N/A'}, "
                    f"开: {kline.open:.2f}, 高: {kline.high:.2f}, 低: {kline.low:.2f}, "
                    f"收: {kline.close:.2f}, 量: {kline.volume:.2f}"
                    for i, kline in enumerate(recent_3m)
                ])
                if len(klines_3m) > 20:
                    klines_3m_str += f"\n        ... (共 {len(klines_3m)} 根K线，仅显示最近20根)"
            
            # 格式化4小时K线（显示最近10根的关键信息）
            klines_4h_str = ""
            if klines_4h:
                recent_4h = klines_4h[-10:] if len(klines_4h) > 10 else klines_4h
                klines_4h_str = "\n".join([
                    f"        [{i+1}] 时间: {kline.open_time if hasattr(kline, 'open_time') else 'N/A'}, "
                    f"开: {kline.open:.2f}, 高: {kline.high:.2f}, 低: {kline.low:.2f}, "
                    f"收: {kline.close:.2f}, 量: {kline.volume:.2f}"
                    for i, kline in enumerate(recent_4h)
                ])
                if len(klines_4h) > 10:
                    klines_4h_str += f"\n        ... (共 {len(klines_4h)} 根K线，仅显示最近10根)"
            
            formatted_lines.append(
                f"  {symbol}:\n"
                f"    - 当前价格: {price_str}\n"  # 使用预先格式化的字符串
                f"    - 数据来源: {source}\n"
                f"    - 3分钟K线数据 ({len(klines_3m)} 根):\n{klines_3m_str if klines_3m_str else '        无数据'}\n"
                f"    - 4小时K线数据 ({len(klines_4h)} 根):\n{klines_4h_str if klines_4h_str else '        无数据'}"
            )
        
        return "\n".join(formatted_lines) if formatted_lines else "无市场数据"

    def _format_signal_data(self, signal_data_map: dict) -> str:
        """格式化信号数据，提取关键指标并保留序列数据"""
        if not signal_data_map:
            return "无信号数据"
        
        formatted_lines = []
        for symbol, signals in signal_data_map.items():
            # 价格信息
            current_price = signals.get('current_price', 0)
            price_change_1h = signals.get('price_change_1h', 0)
            price_change_4h = signals.get('price_change_4h', 0)
            
            # 3分钟指标
            ema20_3m = signals.get('ema20_3m', 0)
            macd_3m = signals.get('macd_3m', 0)
            rsi7_3m = signals.get('rsi7_3m', 0)
            rsi14_3m = signals.get('rsi14_3m', 0)
            
            # 4小时指标
            ema20_4h = signals.get('ema20_4h', 0)
            ema50_4h = signals.get('ema50_4h', 0)
            macd_4h = signals.get('macd_4h', 0)
            rsi7_4h = signals.get('rsi7_4h', 0)
            rsi14_4h = signals.get('rsi14_4h', 0)
            atr_4h = signals.get('atr_4h', 0)
            
            # 趋势判断
            price_vs_ema20_3m = "高于" if current_price > ema20_3m else "低于" if current_price < ema20_3m else "等于"
            price_vs_ema20_4h = "高于" if current_price > ema20_4h else "低于" if current_price < ema20_4h else "等于"
            macd_signal_3m = "看涨" if macd_3m > 0 else "看跌" if macd_3m < 0 else "中性"
            macd_signal_4h = "看涨" if macd_4h > 0 else "看跌" if macd_4h < 0 else "中性"
            rsi_status_3m = "超买" if rsi14_3m > 70 else "超卖" if rsi14_3m < 30 else "正常"
            rsi_status_4h = "超买" if rsi14_4h > 70 else "超卖" if rsi14_4h < 30 else "正常"
            
            # 序列数据摘要（保留关键趋势信息）
            intraday_series = signals.get('intraday_series', {})
            longer_term_series = signals.get('longer_term_series', {})
            
            # 格式化序列数据摘要
            intraday_summary = ""
            if intraday_series:
                mid_prices = intraday_series.get('mid_prices', [])
                ema20_values = intraday_series.get('ema20_values', [])
                macd_values = intraday_series.get('macd_values', [])
                rsi7_values = intraday_series.get('rsi7_values', [])
                
                if mid_prices:
                    recent_prices = mid_prices[-10:] if len(mid_prices) > 10 else mid_prices
                    intraday_summary = (
                        f"        最近价格序列: {[f'{p:.2f}' for p in recent_prices]}\n"
                        f"        最近EMA20序列: {[f'{e:.2f}' if e and not (isinstance(e, float) and (e != e)) else 'N/A' for e in (ema20_values[-10:] if ema20_values else [])]}\n"
                        f"        最近MACD序列: {[f'{m:.2f}' if m and not (isinstance(m, float) and (m != m)) else 'N/A' for m in (macd_values[-10:] if macd_values else [])]}\n"
                        f"        最近RSI7序列: {[f'{r:.2f}' if r and not (isinstance(r, float) and (r != r)) else 'N/A' for r in (rsi7_values[-10:] if rsi7_values else [])]}"
                    )
            
            longer_term_summary = ""
            if longer_term_series:
                mid_prices_4h = longer_term_series.get('mid_prices', [])
                ema20_values_4h = longer_term_series.get('ema20_values', [])
                macd_values_4h = longer_term_series.get('macd_values', [])
                rsi7_values_4h = longer_term_series.get('rsi7_values', [])
                
                if mid_prices_4h:
                    recent_prices_4h = mid_prices_4h[-10:] if len(mid_prices_4h) > 10 else mid_prices_4h
                    longer_term_summary = (
                        f"        最近价格序列: {[f'{p:.2f}' for p in recent_prices_4h]}\n"
                        f"        最近EMA20序列: {[f'{e:.2f}' if e and not (isinstance(e, float) and (e != e)) else 'N/A' for e in (ema20_values_4h[-10:] if ema20_values_4h else [])]}\n"
                        f"        最近MACD序列: {[f'{m:.2f}' if m and not (isinstance(m, float) and (m != m)) else 'N/A' for m in (macd_values_4h[-10:] if macd_values_4h else [])]}\n"
                        f"        最近RSI7序列: {[f'{r:.2f}' if r and not (isinstance(r, float) and (r != r)) else 'N/A' for r in (rsi7_values_4h[-10:] if rsi7_values_4h else [])]}"
                    )
            
            formatted_lines.append(
                f"  {symbol}:\n"
                f"    【价格信息】\n"
                f"      - 当前价格: {current_price:.2f}\n"
                f"      - 1小时涨跌: {price_change_1h:+.2f}%\n"
                f"      - 4小时涨跌: {price_change_4h:+.2f}%\n"
                f"    【3分钟指标】\n"
                f"      - EMA20: {ema20_3m:.2f} (价格{price_vs_ema20_3m}EMA20)\n"
                f"      - MACD: {macd_3m:.2f} ({macd_signal_3m})\n"
                f"      - RSI7: {rsi7_3m:.2f}\n"
                f"      - RSI14: {rsi14_3m:.2f} ({rsi_status_3m})\n"
                f"    【4小时指标】\n"
                f"      - EMA20: {ema20_4h:.2f} (价格{price_vs_ema20_4h}EMA20)\n"
                f"      - EMA50: {ema50_4h:.2f}\n"
                f"      - MACD: {macd_4h:.2f} ({macd_signal_4h})\n"
                f"      - RSI7: {rsi7_4h:.2f}\n"
                f"      - RSI14: {rsi14_4h:.2f} ({rsi_status_4h})\n"
                f"      - ATR: {atr_4h:.2f} (波动率)\n"
                f"    【3分钟序列数据摘要】\n{intraday_summary if intraday_summary else '        无数据'}\n"
                f"    【4小时序列数据摘要】\n{longer_term_summary if longer_term_summary else '        无数据'}"
            )
        
        return "\n".join(formatted_lines) if formatted_lines else "无信号数据"

    def _format_positions(self, positions: list) -> str:
        """格式化持仓信息"""
        if not positions:
            return "无持仓"
        
        formatted_lines = []
        for pos in positions:
            symbol = pos.get('symbol', 'N/A')
            side = pos.get('side', 'N/A')
            size = pos.get('size', 0)
            entry_price = pos.get('entry_price', 0)
            mark_price = pos.get('mark_price', 0)
            unrealized_pnl = pos.get('unrealized_pnl', 0)
            leverage = pos.get('leverage', 1)
            
            pnl_percent = (unrealized_pnl / (entry_price * size)) * 100 if entry_price * size > 0 else 0
            pnl_status = "盈利" if unrealized_pnl > 0 else "亏损" if unrealized_pnl < 0 else "持平"
            
            formatted_lines.append(
                f"  {symbol}:\n"
                f"    - 方向: {side}\n"
                f"    - 数量: {size:.4f}\n"
                f"    - 杠杆: {leverage}x\n"
                f"    - 开仓价: {entry_price:.2f}\n"
                f"    - 标记价: {mark_price:.2f}\n"
                f"    - 未实现盈亏: {unrealized_pnl:+.2f} ({pnl_percent:+.2f}%) [{pnl_status}]"
            )
        
        return "\n".join(formatted_lines) if formatted_lines else "无持仓"

    def _build_user_prompt(self, state: DecisionState):
        """构建结构化的用户提示词，保留K线数据"""
        coins = state.get('candidate_symbols', [])
        market_data_map = state.get('market_data_map', {})
        signal_data_map = state.get('signal_data_map', {})
        account_balance = state.get('account_balance', 0.0)
        positions = state.get('positions', [])
        
        # 尝试从交易所获取实时余额（如果state中没有）
        if account_balance == 0.0 and self.exchange_service:
            try:
                account_balance = self.exchange_service.get_balance()
                logger.info(f"💰 从交易所获取实时余额: {account_balance}")
            except Exception as e:
                logger.warning(f"⚠️ 无法从交易所获取余额: {e}")
        
        # 格式化各部分信息
        market_info = self._format_market_data(market_data_map)
        signal_info = self._format_signal_data(signal_data_map)
        positions_info = self._format_positions(positions)
        
        user_prompt = f"""
# 交易决策分析请求

## 一、账户信息
- 账户余额: {account_balance:.2f} USDT
- 当前持仓数量: {len(positions)} 个

## 二、持仓详情
{positions_info}

## 三、候选币种
{', '.join(coins) if coins else '无候选币种'}

## 四、市场数据（包含K线数据）
{market_info}

## 五、技术信号分析（包含指标序列数据）
{signal_info}

## 六、决策要求
请根据以上信息，对每个候选币种进行综合分析，并给出交易决策：
1. 分析K线数据，识别价格趋势和形态
2. 结合3分钟和4小时指标，评估多时间框架信号
3. 观察序列数据的变化趋势
4. 考虑账户余额和现有持仓情况
5. 给出明确的交易建议：买入、卖出或持有
6. 如果建议交易，请说明理由和风险提示

请以结构化的JSON格式返回决策结果，包含：
- symbol: 币种符号
- action: 操作建议 (buy/sell/hold)
- confidence: 信心度 (0-100)
- reason: 决策理由（需引用具体的K线形态、指标信号等）
- risk_level: 风险等级 (low/medium/high)
"""
        
        logger.info(f"📝 构建用户提示词完成 (余额: {account_balance:.2f}, 持仓: {len(positions)}, 币种: {len(coins)})")
        return user_prompt

    def run(self, state: DecisionState):
        try:
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=self._build_user_prompt(state)),
            ]
            response = self.llm.invoke(messages)
            logger.info(f"AI Decision Response: {response}")
            return state
        except Exception as e:
            logger.error(f"AI Decision Error: {e}")
            return state