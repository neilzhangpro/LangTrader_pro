from decision_engine.state import DecisionState
from utils.logger import logger
from utils.llm_factory import LLMFactory
from langchain_core.messages import HumanMessage, SystemMessage
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal

if TYPE_CHECKING:
    from config.settings import Settings
    from services.decision_log_service import DecisionLogService


class DecisionItem(BaseModel):
    """单个交易决策项"""
    symbol: str = Field(description="币种符号（如BTC/USDT）")
    action: str = Field(description="操作类型：open_long/open_short/close_long/close_short/hold/wait")
    leverage: Optional[int] = Field(None, description="杠杆倍数（开仓时必填）")
    position_size_usd: Optional[float] = Field(None, description="仓位大小（USD，开仓时必填）")
    stop_loss: Optional[float] = Field(None, description="止损价格（开仓时必填，必须>0）")
    take_profit: Optional[float] = Field(None, description="止盈价格（开仓时必填，必须>0）")
    confidence: int = Field(description="信心度（0-100）")
    risk_usd: Optional[float] = Field(None, description="最大美元风险（开仓时必填）")
    reasoning: str = Field(description="决策理由（需引用具体的K线形态、指标信号、OI Top数据等）")


class DecisionOutput(BaseModel):
    """AI决策输出（包含决策列表）"""
    decisions: List[DecisionItem] = Field(description="交易决策列表")


class AIDecision:
    def __init__(
        self, 
        trader_cfg: dict, 
        settings: Optional['Settings'] = None,
        trader_id: Optional[str] = None
    ):
        """
        初始化AI决策节点
        
        Args:
            trader_cfg: 交易员配置
            settings: 设置对象
            trader_id: 交易员ID
        """
        self.trader_cfg = trader_cfg
        self.settings = settings
        self.trader_id = trader_id
        self.llm = None  # 初始化为 None
        self.system_prompt = None
        
        # 初始化决策日志服务
        if settings:
            try:
                from services.decision_log_service import DecisionLogService
                self.decision_log_service = DecisionLogService(settings)
            except Exception as e:
                logger.warning(f"⚠️ 初始化决策日志服务失败: {e}")
                self.decision_log_service = None
        else:
            self.decision_log_service = None
        
        if not self.trader_cfg.get('ai_model', {}).get('enabled', False):
            logger.debug("AI模型未启用，跳过AI决策")
            return
        
        # 初始化 LLM
        try:
            provider = self.trader_cfg.get('ai_model', {}).get('provider', 'openai')
            logger.debug(f"初始化LLM，Provider: {provider}")
            
            base_llm = self._get_llm(provider)
            if not base_llm:
                logger.error("LLM创建失败")
                self.llm = None
                return
            
            # 使用结构化输出
            try:
                self.llm = base_llm.with_structured_output(DecisionOutput)
                logger.debug("已启用结构化输出")
            except Exception as e:
                logger.warning(f"启用结构化输出失败，将使用普通模式: {e}")
                self.llm = base_llm
            
            self.system_prompt = self.trader_cfg.get('prompt', '')
            logger.info(f"AI Decision节点初始化完成 (prompt长度: {len(self.system_prompt)}字符)")
        except KeyError as e:
            logger.error(f"初始化LLM失败 - KeyError: {e}", exc_info=True)
            self.llm = None
        except Exception as e:
            logger.error(f"初始化LLM失败: {e}", exc_info=True)
            self.llm = None


    def _get_llm(self, llm_provider: str) -> Optional[object]:
        """获取LLM实例（使用工厂类）"""
        ai_model_config = self.trader_cfg.get('ai_model', {})
        return LLMFactory.create_llm(ai_model_config)
       
    def _format_market_data(self, market_data_map: dict) -> str:
        """格式化市场数据（仅显示关键信息，与NOFX维度一致）"""
        if not market_data_map:
            return "无市场数据"
        
        formatted_lines = []
        for symbol, data in market_data_map.items():
            current_price = data.get('current_price')
            price_str = f"{current_price:.2f}" if current_price is not None else "N/A"
            
            # 只显示当前价格，不包含完整K线原始数据
            # 序列数据已在 _format_signal_data() 中通过 _format_series_summary() 提供
            formatted_lines.append(f"  {symbol}: 当前价格 {price_str}")
        
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
            atr3_4h = signals.get('atr3_4h', 0)
            
            # 成交量统计（4小时）
            current_volume_4h = signals.get('current_volume_4h', 0)
            average_volume_4h = signals.get('average_volume_4h', 0)
            
            # OpenInterest 和 FundingRate
            open_interest = signals.get('open_interest')
            open_interest_average = signals.get('open_interest_average')
            funding_rate = signals.get('funding_rate')
            
            # 格式化持仓量和资金费率（先判断再格式化，避免f-string格式错误）
            oi_str = f"{open_interest:.2f}" if open_interest is not None else "N/A"
            oi_avg_str = f"{open_interest_average:.2f}" if open_interest_average is not None else "N/A"
            funding_rate_str = f"{funding_rate:.2e}" if funding_rate is not None else "N/A"
            
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
            
            intraday_summary = self._format_series_summary(intraday_series, "3分钟")
            longer_term_summary = self._format_series_summary(longer_term_series, "4小时")
            
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
                f"      - ATR14: {atr_4h:.2f} (波动率)\n"
                f"      - ATR3: {atr3_4h:.2f} (短期波动率)\n"
                f"    【成交量统计（4小时）】\n"
                f"      - 当前成交量: {current_volume_4h:.2f}\n"
                f"      - 平均成交量: {average_volume_4h:.2f}\n"
                f"    【持仓量与资金费率】\n"
                f"      - 持仓量 (Latest): {oi_str}\n"
                f"      - 持仓量 (Average): {oi_avg_str}\n"
                f"      - 资金费率: {funding_rate_str}\n"
                f"    【3分钟序列数据摘要】\n{intraday_summary if intraday_summary else '        无数据'}\n"
                f"    【4小时序列数据摘要】\n{longer_term_summary if longer_term_summary else '        无数据'}"
            )
        
        return "\n".join(formatted_lines) if formatted_lines else "无信号数据"

    def _format_series_summary(self, series_data: dict, label: str) -> str:
        """格式化序列数据摘要"""
        if not series_data:
            return ""
        
        mid_prices = series_data.get('mid_prices', [])
        ema20_values = series_data.get('ema20_values', [])
        macd_values = series_data.get('macd_values', [])
        rsi7_values = series_data.get('rsi7_values', [])
        rsi14_values = series_data.get('rsi14_values', [])
        
        if not mid_prices:
            return ""
        
        recent_prices = mid_prices[-10:] if len(mid_prices) > 10 else mid_prices
        
        def format_value(val: Any) -> str:
            """格式化单个值，处理NaN和None"""
            if val is None:
                return 'N/A'
            if isinstance(val, float) and (val != val):  # NaN check
                return 'N/A'
            return f'{val:.2f}'
        
        ema20_recent = [format_value(e) for e in (ema20_values[-10:] if ema20_values else [])]
        macd_recent = [format_value(m) for m in (macd_values[-10:] if macd_values else [])]
        rsi7_recent = [format_value(r) for r in (rsi7_values[-10:] if rsi7_values else [])]
        rsi14_recent = [format_value(r) for r in (rsi14_values[-10:] if rsi14_values else [])]
        
        return (
            f"        最近价格序列: {[f'{p:.2f}' for p in recent_prices]}\n"
            f"        最近EMA20序列: {ema20_recent}\n"
            f"        最近MACD序列: {macd_recent}\n"
            f"        最近RSI7序列: {rsi7_recent}\n"
            f"        最近RSI14序列: {rsi14_recent}"
        )

    def _format_account_info(self, account_info: dict) -> str:
        """格式化账户信息"""
        if not account_info:
            return "无账户信息"
        
        total_equity = account_info.get('total_equity')
        available_balance = account_info.get('available_balance')
        total_pnl = account_info.get('total_pnl')
        total_pnl_pct = account_info.get('total_pnl_pct')
        margin_used = account_info.get('margin_used')
        margin_used_pct = account_info.get('margin_used_pct')
        
        lines = []
        if total_equity is not None:
            lines.append(f"- 账户净值: {total_equity:.2f} USDT")
        if available_balance is not None:
            lines.append(f"- 可用余额: {available_balance:.2f} USDT")
        if total_pnl is not None:
            pnl_str = f"{total_pnl:+.2f} USDT"
            if total_pnl_pct is not None:
                pnl_str += f" ({total_pnl_pct:+.2f}%)"
            lines.append(f"- 总盈亏: {pnl_str}")
        if margin_used is not None:
            margin_str = f"{margin_used:.2f} USDT"
            if margin_used_pct is not None:
                margin_str += f" ({margin_used_pct:.2f}%)"
            lines.append(f"- 已用保证金: {margin_str}")
        
        return "\n".join(lines) if lines else "无账户信息"

    def _format_positions(self, positions: list) -> str:
        """格式化持仓信息（包含完整信息）"""
        if not positions:
            return "无持仓"
        
        formatted_lines = []
        for pos in positions:
            logger.debug(f"持仓信息-------------->: {pos}")
            symbol = pos.get('symbol', 'N/A')
            side = pos.get('side', 'N/A')
            
            # 安全获取数值字段，如果值为 None 则使用默认值
            size = pos.get('size')
            if size is None:
                size = 0.0
            else:
                try:
                    size = float(size)
                except (ValueError, TypeError):
                    size = 0.0
            
            entry_price = pos.get('entry_price')
            if entry_price is None:
                entry_price = 0.0
            else:
                try:
                    entry_price = float(entry_price)
                except (ValueError, TypeError):
                    entry_price = 0.0
            
            mark_price = pos.get('mark_price')
            if mark_price is None:
                mark_price = 0.0
            else:
                try:
                    mark_price = float(mark_price)
                except (ValueError, TypeError):
                    mark_price = 0.0
            
            unrealized_pnl = pos.get('unrealized_pnl')
            if unrealized_pnl is None:
                unrealized_pnl = 0.0
            else:
                try:
                    unrealized_pnl = float(unrealized_pnl)
                except (ValueError, TypeError):
                    unrealized_pnl = 0.0
            
            leverage = pos.get('leverage')
            if leverage is None:
                leverage = 1
            else:
                try:
                    leverage = int(leverage)
                except (ValueError, TypeError):
                    leverage = 1
            
            liquidation_price = pos.get('liquidation_price')
            margin_used = pos.get('margin_used')
            update_time = pos.get('update_time')
            
            # 处理 liquidation_price 和 margin_used，确保它们要么是数字要么是 'N/A'
            liquidation_price_str = "N/A"
            if liquidation_price is not None:
                try:
                    liquidation_price_float = float(liquidation_price)
                    liquidation_price_str = f"{liquidation_price_float:.2f}"
                except (ValueError, TypeError):
                    liquidation_price_str = "N/A"
            
            margin_used_str = "N/A"
            if margin_used is not None:
                try:
                    margin_used_float = float(margin_used)
                    margin_used_str = f"{margin_used_float:.2f}"
                except (ValueError, TypeError):
                    margin_used_str = "N/A"
            
            # 计算盈亏百分比（避免除以0）
            if entry_price and size and entry_price * size > 0:
                pnl_percent = (unrealized_pnl / (entry_price * size)) * 100
            else:
                pnl_percent = 0.0
            
            pnl_status = "盈利" if unrealized_pnl > 0 else "亏损" if unrealized_pnl < 0 else "持平"
            
            # 格式化更新时间
            update_time_str = "N/A"
            if update_time:
                try:
                    dt = datetime.fromtimestamp(update_time / 1000)  # 毫秒转秒
                    update_time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    update_time_str = str(update_time)
            
            formatted_lines.append(
                f"  {symbol}:\n"
                f"    - 方向: {side}\n"
                f"    - 数量: {size:.4f}\n"
                f"    - 杠杆: {leverage}x\n"
                f"    - 开仓价: {entry_price:.2f}\n"
                f"    - 标记价: {mark_price:.2f}\n"
                f"    - 未实现盈亏: {unrealized_pnl:+.2f} ({pnl_percent:+.2f}%) [{pnl_status}]\n"
                f"    - 清算价格: {liquidation_price_str}\n"
                f"    - 已用保证金: {margin_used_str} USDT\n"
                f"    - 更新时间: {update_time_str}"
            )
        logger.debug(f"formatted_lines-------------->: {formatted_lines}")
        return "\n".join(formatted_lines) if formatted_lines else "无持仓"
    
    def _format_candidate_coins(self, coins: list, coin_sources: dict) -> str:
        """格式化候选币种及其来源"""
        if not coins:
            return "无候选币种"
        
        formatted_lines = []
        for coin in coins:
            sources = coin_sources.get(coin, [])
            sources_str = ", ".join(sources) if sources else "配置币种"
            formatted_lines.append(f"  - {coin} (来源: {sources_str})")
        
        return "\n".join(formatted_lines) if formatted_lines else "无候选币种"
    
    def _format_oi_top_data(self, oi_top_data_map: dict) -> str:
        """格式化 OI Top 数据"""
        if not oi_top_data_map:
            return "无 OI Top 数据"
        
        formatted_lines = []
        for symbol, data in oi_top_data_map.items():
            oi_change = data.get('oi_change', 0)
            oi_change_percent = data.get('oi_change_percent', 0)
            time_range = data.get('time_range', '')
            
            formatted_lines.append(
                f"  {symbol}:\n"
                f"    - 持仓量变化: {oi_change:+.2f} ({oi_change_percent:+.2f}%)\n"
                f"    - 时间范围: {time_range if time_range else 'N/A'}"
            )
        
        return "\n".join(formatted_lines) if formatted_lines else "无 OI Top 数据"
    
    def _format_performance(self, performance: Optional[dict]) -> str:
        """格式化性能数据（夏普率等）"""
        if not performance:
            return "无性能数据"
        
        sharpe_ratio = performance.get('sharpe_ratio')
        win_rate = performance.get('win_rate', 0.0)
        total_trades = performance.get('total_trades', 0)
        avg_return = performance.get('avg_return', 0.0)
        total_pnl = performance.get('total_pnl', 0.0)
        
        lines = []
        
        # 夏普率
        if sharpe_ratio is not None:
            sharpe_str = f"{sharpe_ratio:.4f}"
            # 添加状态说明
            if sharpe_ratio < -0.5:
                status = "持续亏损 - 建议停止交易，连续观望至少6个周期"
            elif sharpe_ratio < 0:
                status = "轻微亏损 - 严格控制，只做信心度>80的交易"
            elif sharpe_ratio < 0.7:
                status = "正收益 - 维持当前策略"
            else:
                status = "优异表现 - 可适度扩大仓位"
            lines.append(f"- 夏普比率: {sharpe_str} ({status})")
        else:
            lines.append("- 夏普比率: N/A (数据不足)")
        
        # 其他指标
        if total_trades > 0:
            lines.append(f"- 总交易次数: {total_trades}")
            lines.append(f"- 胜率: {win_rate:.2f}%")
            lines.append(f"- 平均收益: {avg_return:.2f} USDT")
            lines.append(f"- 总盈亏: {total_pnl:+.2f} USDT")
        else:
            lines.append("- 暂无交易记录")
        
        return "\n".join(lines) if lines else "无性能数据"

    def _format_alerts(self, alerts: Optional[List[dict]]) -> str:
        """格式化警报信息"""
        if not alerts:
            return "无市场警报"
        
        # 按严重程度分组
        high_alerts = [a for a in alerts if a.get('severity') == 'high']
        medium_alerts = [a for a in alerts if a.get('severity') == 'medium']
        low_alerts = [a for a in alerts if a.get('severity') == 'low']
        
        lines = []
        
        if high_alerts:
            lines.append("【高优先级警报】")
            for alert in high_alerts:
                lines.append(f"  ⚠️ {alert.get('message', 'N/A')}")
        
        if medium_alerts:
            if lines:
                lines.append("")
            lines.append("【中等优先级警报】")
            for alert in medium_alerts:
                lines.append(f"  ⚠️ {alert.get('message', 'N/A')}")
        
        if low_alerts:
            if lines:
                lines.append("")
            lines.append("【低优先级警报】")
            for alert in low_alerts:
                lines.append(f"  ℹ️ {alert.get('message', 'N/A')}")
        
        return "\n".join(lines) if lines else "无市场警报"

    def _build_user_prompt(self, state: DecisionState):
        """构建结构化的用户提示词，保留K线数据"""
        coins = state.get('candidate_symbols', [])
        market_data_map = state.get('market_data_map', {})
        signal_data_map = state.get('signal_data_map', {})
        account_balance = state.get('account_balance', 0.0)
        positions = state.get('positions', [])
        coin_sources = state.get('coin_sources', {})
        oi_top_data_map = state.get('oi_top_data_map', {})
        performance = state.get('performance')
        alerts = state.get('alerts')
        
        # 获取账户信息（从state获取）
        account_info = {
            'total_equity': account_balance,
            'available_balance': account_balance,
            'margin_used': 0.0,
            'margin_used_pct': 0.0
        }
        
        # 获取当前持仓（从state获取）
        positions = state.get('positions', [])
        if positions:
            logger.info(f"当前持仓: {len(positions)}个")

        # 获取杠杆配置
        btc_eth_leverage = self.trader_cfg.get('btc_eth_leverage', 5)
        altcoin_leverage = self.trader_cfg.get('altcoin_leverage', 5)
        
        # 获取运行状态信息
        runtime_minutes = state.get('runtime_minutes', 0)
        call_count = state.get('call_count', 0)
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 格式化各部分信息
        account_info_str = self._format_account_info(account_info)
        performance_info = self._format_performance(performance)
        alerts_info = self._format_alerts(alerts)
        market_info = self._format_market_data(market_data_map)
        signal_info = self._format_signal_data(signal_data_map)
        positions_info = self._format_positions(positions)
        candidate_coins_info = self._format_candidate_coins(coins, coin_sources)
        oi_top_info = self._format_oi_top_data(oi_top_data_map)
        
        user_prompt = f"""
# 交易决策分析请求

## 一、运行状态
- 当前时间: {current_time}
- 运行时长: {runtime_minutes} 分钟
- 调用次数: {call_count}

## 二、账户信息
{account_info_str}
- 当前持仓数量: {len(positions)} 个

## 三、性能分析
{performance_info}

## 四、持仓详情
{positions_info}

## 五、候选币种及来源
{candidate_coins_info}

## 六、OI Top 数据（持仓量增长Top币种）
{oi_top_info}

## 七、市场警报
{alerts_info}

## 八、市场数据与技术指标
{market_info}

{signal_info}

## 九、交易配置
- BTC/ETH 杠杆上限: {btc_eth_leverage}x
- 山寨币杠杆上限: {altcoin_leverage}x

## 十、决策要求
请根据以上信息，对每个候选币种和现有持仓进行综合分析，并给出交易决策：

### 对于候选币种（开仓决策）：
1. 分析K线数据，识别价格趋势和形态
2. 结合3分钟和4小时指标，评估多时间框架信号
3. 观察序列数据的变化趋势
4. 参考 OI Top 数据（如果可用），评估持仓量变化
5. 考虑账户余额和现有持仓情况
6. 给出明确的交易建议：开多、开空或等待

### 对于现有持仓（平仓决策）：
1. 评估持仓的盈亏情况
2. 分析当前市场信号是否支持继续持有
3. 考虑清算价格风险
4. 给出明确的交易建议：平多、平空或持有

### 决策格式要求：
请以结构化的JSON数组格式返回决策结果，每个决策包含：
- symbol: 币种符号（如 "BTC/USDT"）
- action: 操作类型，必须是以下之一：
  - "open_long": 开多仓
  - "open_short": 开空仓
  - "close_long": 平多仓
  - "close_short": 平空仓
  - "hold": 持有（对现有持仓）
  - "wait": 等待（对候选币种，暂不开仓）
- leverage: 杠杆倍数（开仓时必填，1-{altcoin_leverage}，BTC/ETH最高{btc_eth_leverage}）
- position_size_usd: 仓位大小（USD，开仓时必填）
- stop_loss: 止损价格（开仓时必填，必须>0）
- take_profit: 止盈价格（开仓时必填，必须>0）
- confidence: 信心度 (0-100)
- risk_usd: 最大美元风险（开仓时必填）
- reasoning: 决策理由（需引用具体的K线形态、指标信号、OI Top数据等）

### 重要约束：
1. **风险回报比必须≥3:1（收益/风险 ≥ 3）**
   - 这是硬性要求，所有开仓决策必须满足此条件
   - 计算方法：
     * 做多：风险 = 当前价格 - 止损价格，收益 = 止盈价格 - 当前价格，风险回报比 = 收益 / 风险
     * 做空：风险 = 止损价格 - 当前价格，收益 = 当前价格 - 止盈价格，风险回报比 = 收益 / 风险
   - 示例（做多）：
     * 当前价格：100 USDT
     * 止损价格：95 USDT（风险 = 5 USDT）
     * 止盈价格：115 USDT（收益 = 15 USDT）
     * 风险回报比 = 15 / 5 = 3.0:1 ✓ 满足要求
   - 示例（做空）：
     * 当前价格：100 USDT
     * 止损价格：105 USDT（风险 = 5 USDT）
     * 止盈价格：85 USDT（收益 = 15 USDT）
     * 风险回报比 = 15 / 5 = 3.0:1 ✓ 满足要求
   - **重要**：设置止损和止盈时，必须确保风险回报比≥3.0，否则决策将被拒绝

2. BTC/ETH 单币种仓位价值不能超过账户净值的10倍
3. 山寨币单币种仓位价值不能超过账户净值的1.5倍
4. 开仓操作必须提供完整的杠杆、仓位大小、止损、止盈参数
5. 止损和止盈价格必须合理（做多时止损<止盈，做空时止损>止盈）

请返回JSON数组格式的决策列表。
"""
        logger.debug(f"构建用户提示词完成 (持仓: {len(positions)}, 币种: {len(coins)})")
        return user_prompt

    def run(self, state: DecisionState) -> DecisionState:
        """执行AI决策"""
        logger.info(f"AI决策节点执行，LLM: {self.llm}")
        if not hasattr(self, 'llm') or self.llm is None:
            logger.error("LLM未初始化，AI模型可能未启用或初始化失败")
            return state
        
        try:
            user_prompt = self._build_user_prompt(state)
            logger.debug(f"用户提示词构建完成，长度: {len(user_prompt)}字符")
            
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=user_prompt),
            ]
            
            logger.info("调用LLM进行决策...")
            logger.debug(f"用户提示词: {user_prompt}")
            response = self.llm.invoke(messages)
            
            # 使用结构化输出，直接获取DecisionOutput对象
            if isinstance(response, DecisionOutput):
                # 使用model_dump()（Pydantic v2）或dict()（Pydantic v1）
                try:
                    decisions = [item.model_dump() for item in response.decisions]
                except AttributeError:
                    # 回退到dict()方法（Pydantic v1）
                    decisions = [item.dict() for item in response.decisions]
                
                decision_count = len(decisions)
                logger.info(f"AI决策完成，共{decision_count}个决策")
                state['ai_decision'] = {
                    'decisions': decisions,
                    'raw_response': None  # 结构化输出不包含原始响应
                }
                
                # 注意：决策日志保存已移至 Risk_check 节点之后
            else:
                # 回退到手动解析（如果结构化输出未启用）
                logger.warning("收到非结构化响应，尝试手动解析")
                if hasattr(response, 'content'):
                    import json
                    response_text = response.content
                    # 提取JSON（如果被代码块包裹）
                    if '```json' in response_text:
                        json_start = response_text.find('```json') + 7
                        json_end = response_text.find('```', json_start)
                        response_text = response_text[json_start:json_end].strip()
                    elif '```' in response_text:
                        json_start = response_text.find('```') + 3
                        json_end = response_text.find('```', json_start)
                        response_text = response_text[json_start:json_end].strip()
                    
                    try:
                        decisions = json.loads(response_text)
                        decision_count = len(decisions) if isinstance(decisions, list) else 1
                        logger.info(f"AI决策完成，共{decision_count}个决策")
                        decisions_list = decisions if isinstance(decisions, list) else [decisions]
                        state['ai_decision'] = {
                            'decisions': decisions_list,
                            'raw_response': response.content
                        }
                        
                        # 注意：决策日志保存已移至 Risk_check 节点之后
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON解析失败: {e}")
                        state['ai_decision'] = {
                            'error': f"JSON解析失败: {str(e)}",
                            'raw_response': response.content
                        }
                else:
                    logger.error("无法解析响应格式")
                    state['ai_decision'] = {
                        'error': "无法解析响应格式",
                        'raw_response': str(response)
                    }
            
            return state
        except Exception as e:
            logger.error(f"AI决策执行失败: {e}", exc_info=True)
            return state
    
    def _save_decision_logs(self, decisions: List[Dict], state: DecisionState):
        """保存决策日志到数据库"""
        if not self.decision_log_service or not self.trader_id:
            logger.debug("决策日志服务未初始化或 trader_id 不存在，跳过保存")
            return
        
        # 准备状态快照（只保存关键信息，避免数据过大）
        state_snapshot = {
            'candidate_symbols': state.get('candidate_symbols', []),
            'positions': state.get('positions', []),
            'account_balance': state.get('account_balance'),
            'market_data_map_keys': list(state.get('market_data_map', {}).keys()),
            'signal_data_map_keys': list(state.get('signal_data_map', {}).keys()),
            'call_count': state.get('call_count'),
            'runtime_minutes': state.get('runtime_minutes'),
        }
        
        # 为每个决策保存日志
        for decision in decisions:
            try:
                symbol = decision.get('symbol', '')
                action = decision.get('action', '')
                reasoning = decision.get('reasoning', '')
                confidence = decision.get('confidence')
                
                if not symbol:
                    logger.warning("⚠️ 决策缺少 symbol，跳过保存")
                    continue
                
                # 转换置信度
                confidence_decimal = None
                if confidence is not None:
                    try:
                        confidence_decimal = Decimal(str(confidence))
                    except Exception as e:
                        logger.warning(f"⚠️ 转换置信度失败: {e}")
                
                # 保存决策日志
                self.decision_log_service.record_decision(
                    trader_id=self.trader_id,
                    symbol=symbol,
                    decision_state=state_snapshot,
                    decision_result=action,
                    reasoning=reasoning,
                    confidence=confidence_decimal
                )
            except Exception as e:
                logger.warning(f"⚠️ 保存决策日志失败: {symbol} - {e}", exc_info=True)
                # 继续处理其他决策，不中断流程