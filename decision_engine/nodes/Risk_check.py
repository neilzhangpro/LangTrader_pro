from decision_engine.state import DecisionState
from typing import Optional, List, Dict, Tuple, TYPE_CHECKING
from utils.logger import logger
from decimal import Decimal

if TYPE_CHECKING:
    from config.settings import Settings
    from services.decision_log_service import DecisionLogService


class RiskCheck:
    """检查风险，包括AI决策是否安全"""
    
    # 风险阈值常量（参考NOFX和系统配置）
    MAX_MARGIN_USED_PCT = 80.0  # 最大保证金使用率（%）
    MIN_RISK_REWARD_RATIO = 3.0  # 最小风险回报比（参考NOFX）
    MAX_POSITION_VALUE_BTC_ETH_MULTIPLIER = 10.0  # BTC/ETH最多10倍账户净值
    MAX_POSITION_VALUE_ALTCOIN_MULTIPLIER = 1.5  # 山寨币最多1.5倍账户净值
    
    # 有效action列表
    VALID_ACTIONS = {"open_long", "open_short", "close_long", "close_short", "hold", "wait"}
    
    def __init__(
        self, 
        trader_cfg: dict, 
        settings: Optional['Settings'] = None,
        trader_id: Optional[str] = None
    ):
        """
        初始化风险检查节点
        
        Args:
            trader_cfg: 交易员配置
            settings: 设置对象
            trader_id: 交易员ID
        """
        self.trader_cfg = trader_cfg
        self.settings = settings
        self.trader_id = trader_id
        
        # 从trader_cfg获取杠杆配置（来自traders表）
        self.btc_eth_leverage = trader_cfg.get('btc_eth_leverage', 5)
        self.altcoin_leverage = trader_cfg.get('altcoin_leverage', 5)
        
        # 从trader_cfg获取系统级风险配置（来自system_config表，已在trader_manager中加载）
        self.max_daily_loss = trader_cfg.get('max_daily_loss', 10.0)
        self.max_drawdown = trader_cfg.get('max_drawdown', 20.0)
        
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
        
        logger.info(
            f"RiskCheck 节点初始化完成 - "
            f"BTC/ETH杠杆: {self.btc_eth_leverage}x, "
            f"山寨币杠杆: {self.altcoin_leverage}x"
        )

    def run(self, state: DecisionState) -> DecisionState:
        """执行风险检查"""
        logger.info("🔍 执行风险检查节点...")
        
        # 初始化风险检查结果
        state['risk_approved'] = False
        
        # 1. 获取AI决策
        ai_decision = state.get('ai_decision')
        if not ai_decision or not ai_decision.get('decisions'):
            logger.warning("⚠️ AI决策为空或无具体决策，跳过风险检查")
            return state
        
        decisions_raw = ai_decision.get('decisions', [])
        if not isinstance(decisions_raw, list):
            logger.warning("⚠️ AI决策格式错误，跳过风险检查")
            return state
        
        # 2. 获取账户信息
        account_info = self._get_account_info(state)
        if not account_info or account_info.get('total_equity', 0) <= 0:
            logger.error("❌ 账户净值无效，无法进行风险检查")
            return state
        
        total_equity = account_info['total_equity']
        
        # 3. 获取持仓和市场数据
        positions = state.get('positions', [])
        market_data_map = state.get('market_data_map', {})
        
        # 4. 验证每个决策
        validated_decisions: List[Dict] = []
        validation_errors: List[Dict] = []
        
        for i, decision_dict in enumerate(decisions_raw):
            if not isinstance(decision_dict, dict):
                logger.warning(f"⚠️ 决策 {i+1} 格式错误，跳过")
                continue
            
            symbol = decision_dict.get('symbol', '')
            action = decision_dict.get('action', '')
            
            # 验证决策
            is_valid, error_message = self._validate_decision(
                decision_dict, 
                total_equity,
                positions,
                market_data_map
            )
            
            if is_valid:
                validated_decisions.append(decision_dict)
                logger.debug(f"✅ {symbol} {action} 验证通过")
            else:
                validation_errors.append({
                    'symbol': symbol,
                    'action': action,
                    'error': error_message
                })
                logger.warning(f"❌ {symbol} {action} 验证失败: {error_message}")
        
        # 5. 账户风险检查（如果有关注开仓操作）
        has_open_actions = any(
            d.get('action') in {'open_long', 'open_short'} 
            for d in validated_decisions
        )
        
        if has_open_actions:
            account_risk_ok, account_risk_msg = self._check_account_risk(account_info)
            if not account_risk_ok:
                logger.warning(f"⚠️ 账户风险检查失败: {account_risk_msg}")
                # 拒绝所有开仓操作
                validated_decisions = [
                    d for d in validated_decisions 
                    if d.get('action') not in {'open_long', 'open_short'}
                ]
                validation_errors.append({
                    'symbol': 'ALL',
                    'action': 'open_*',
                    'error': account_risk_msg
                })
        
        # 6. 更新状态
        if validated_decisions:
            state['ai_decision']['decisions'] = validated_decisions
            state['ai_decision']['validation_errors'] = validation_errors
            state['risk_approved'] = True
            logger.info(f"✅ 风险检查通过，{len(validated_decisions)}个AI决策被批准")
            
            # 保存通过风险检查的决策日志
            self._save_validated_decision_logs(validated_decisions, decisions_raw, state)
        else:
            state['ai_decision']['decisions'] = []
            state['ai_decision']['validation_errors'] = validation_errors
            state['risk_approved'] = False
            logger.warning(f"⚠️ 所有AI决策均未通过风险检查（共{len(validation_errors)}个错误）")
        
        return state
    
    def _get_account_info(self, state: DecisionState) -> Optional[Dict]:
        """获取账户信息（从state获取）"""
        # 从state获取account_balance
        account_balance = state.get('account_balance', 0.0)
        
        # 使用account_balance构建账户信息
        if account_balance > 0:
            return {
                'total_equity': account_balance,
                'available_balance': account_balance,
                'margin_used': 0.0,
                'margin_used_pct': 0.0
            }
        
        return None
    
    def _validate_decision(
        self, 
        decision: Dict, 
        account_equity: float,
        positions: List[Dict],
        market_data_map: Dict[str, Dict]
    ) -> Tuple[bool, str]:
        """验证单个决策的合法性
        
        Returns:
            (is_valid, error_message)
        """
        # 1. 验证action
        action = decision.get('action', '')
        if action not in self.VALID_ACTIONS:
            return False, f"无效的action: {action}"
        
        # 2. 开仓操作验证
        if action in {"open_long", "open_short"}:
            return self._validate_open_position(decision, account_equity, market_data_map)
        
        # 3. 平仓操作验证
        elif action in {"close_long", "close_short"}:
            return self._validate_close_position(decision, positions)
        
        # 4. hold/wait 操作不需要验证
        elif action in {"hold", "wait"}:
            return True, ""
        
        return False, f"未知的action: {action}"
    
    def _validate_open_position(
        self, 
        decision: Dict, 
        account_equity: float,
        market_data_map: Dict[str, Dict]
    ) -> Tuple[bool, str]:
        """验证开仓操作"""
        symbol = decision.get('symbol', '')
        action = decision.get('action', '')
        leverage = decision.get('leverage')
        position_size_usd = decision.get('position_size_usd')
        stop_loss = decision.get('stop_loss')
        take_profit = decision.get('take_profit')
        risk_usd = decision.get('risk_usd')
        
        # 验证杠杆
        if leverage is None or leverage <= 0:
            return False, "开仓操作必须提供有效的杠杆倍数"
        
        is_btc_eth = self._is_btc_eth(symbol)
        max_leverage = self.btc_eth_leverage if is_btc_eth else self.altcoin_leverage
        
        if leverage > max_leverage:
            return False, f"杠杆 ({leverage}x) 超过上限 ({max_leverage}x)"
        
        # 验证仓位大小
        if position_size_usd is None or position_size_usd <= 0:
            return False, "开仓操作必须提供有效的仓位大小（USD）"
        
        # 验证仓位价值上限
        max_position_multiplier = (
            self.MAX_POSITION_VALUE_BTC_ETH_MULTIPLIER if is_btc_eth 
            else self.MAX_POSITION_VALUE_ALTCOIN_MULTIPLIER
        )
        max_position_value = account_equity * max_position_multiplier
        
        if position_size_usd > max_position_value:
            return False, (
                f"仓位价值 ({position_size_usd:.2f} USD) 过大，"
                f"超过账户净值 ({account_equity:.2f} USD) 的{max_position_multiplier}倍限制"
            )
        
        # 验证止损止盈
        if stop_loss is None or stop_loss <= 0:
            return False, "开仓操作必须提供有效的止损价格"
        
        if take_profit is None or take_profit <= 0:
            return False, "开仓操作必须提供有效的止盈价格"
        
        # 验证止损止盈合理性
        if action == "open_long":
            if stop_loss >= take_profit:
                return False, "做多时止损价必须小于止盈价"
        else:  # open_short
            if stop_loss <= take_profit:
                return False, "做空时止损价必须大于止盈价"
        
        # 验证风险回报比（需要当前价格）
        current_price = self._get_current_price(symbol, market_data_map)
        if current_price is None:
            return False, f"无法获取 {symbol} 的当前价格"
        
        rrr_valid, rrr_ratio = self._check_risk_reward_ratio(
            decision, current_price, action
        )
        if not rrr_valid:
            return False, f"风险回报比 ({rrr_ratio:.2f}) 低于最低要求 ({self.MIN_RISK_REWARD_RATIO}:1)"
        
        # 验证risk_usd（如果提供）
        if risk_usd is not None and risk_usd <= 0:
            return False, "最大美元风险（risk_usd）必须大于0"
        
        return True, ""
    
    def _validate_close_position(
        self, 
        decision: Dict, 
        positions: List[Dict]
    ) -> Tuple[bool, str]:
        """验证平仓操作"""
        symbol = decision.get('symbol', '')
        action = decision.get('action', '')
        
        # 查找持仓
        position = None
        for pos in positions:
            if pos.get('symbol') == symbol:
                position = pos
                break
        
        if not position:
            return False, f"未找到 {symbol} 的持仓"
        
        # 验证持仓方向匹配
        position_side = position.get('side', '').lower()
        expected_side = 'long' if action == 'close_long' else 'short'
        
        if position_side != expected_side:
            return False, (
                f"持仓方向不匹配：持仓为 {position_side}，"
                f"但操作是 {action}（期望 {expected_side}）"
            )
        
        return True, ""
    
    def _check_risk_reward_ratio(
        self, 
        decision: Dict, 
        current_price: float,
        action: str
    ) -> Tuple[bool, float]:
        """检查风险回报比（参考NOFX逻辑）
        
        Returns:
            (is_valid, ratio)
        """
        stop_loss = decision.get('stop_loss')
        take_profit = decision.get('take_profit')
        
        if stop_loss is None or take_profit is None:
            return False, 0.0
        
        if action == "open_long":
            # 做多：风险 = 当前价 - 止损，收益 = 止盈 - 当前价
            risk = current_price - stop_loss
            reward = take_profit - current_price
        else:  # open_short
            # 做空：风险 = 止损 - 当前价，收益 = 当前价 - 止盈
            risk = stop_loss - current_price
            reward = current_price - take_profit
        
        if risk <= 0:
            return False, 0.0
        
        ratio = reward / risk
        is_valid = ratio >= self.MIN_RISK_REWARD_RATIO
        
        # 详细日志
        logger.debug(
            f"风险回报比检查: {decision.get('symbol')} {action} | "
            f"当前价={current_price:.2f} 止损={stop_loss:.2f} 止盈={take_profit:.2f} | "
            f"风险={risk:.2f} 收益={reward:.2f} | "
            f"风险回报比={ratio:.2f}:1 {'✓' if is_valid else '✗ (要求≥' + str(self.MIN_RISK_REWARD_RATIO) + ':1)'}"
        )
        
        return is_valid, ratio
    
    def _is_btc_eth(self, symbol: str) -> bool:
        """判断是否为BTC或ETH"""
        normalized = symbol.upper().replace('/', '').replace('USDT', '').replace(':', '')
        return normalized in ['BTC', 'ETH']
    
    def _get_current_price(self, symbol: str, market_data_map: Dict[str, Dict]) -> Optional[float]:
        """从market_data_map获取当前价格"""
        market_data = market_data_map.get(symbol, {})
        # 尝试多种可能的字段名
        current_price = (
            market_data.get('current_price') or
            market_data.get('price') or
            market_data.get('last_price') or
            market_data.get('close')
        )
        
        if current_price is not None:
            try:
                return float(current_price)
            except (ValueError, TypeError):
                pass
        
        return None
    
    def _check_account_risk(self, account_info: Dict) -> Tuple[bool, str]:
        """检查账户风险"""
        total_equity = account_info.get('total_equity', 0)
        margin_used_pct = account_info.get('margin_used_pct', 0)
        
        # 检查账户净值
        if total_equity <= 0:
            return False, "账户净值无效或为0"
        
        # 检查保证金使用率
        if margin_used_pct is not None and margin_used_pct >= self.MAX_MARGIN_USED_PCT:
            return False, (
                f"保证金使用率 ({margin_used_pct:.2f}%) "
                f"超过上限 ({self.MAX_MARGIN_USED_PCT}%)"
            )
        
        return True, ""
    
    def _save_validated_decision_logs(
        self, 
        validated_decisions: List[Dict], 
        original_decisions: List[Dict],
        state: DecisionState
    ):
        """保存通过风险检查的决策日志到数据库"""
        if not self.decision_log_service or not self.trader_id:
            logger.debug("决策日志服务未初始化或 trader_id 不存在，跳过保存")
            return
        
        # 创建原始决策的映射（用于获取完整的决策信息如reasoning, confidence）
        original_decision_map = {}
        for orig_decision in original_decisions:
            symbol = orig_decision.get('symbol', '')
            if symbol:
                original_decision_map[symbol] = orig_decision
        
        # 准备状态快照（只保存关键信息，避免数据过大）
        state_snapshot = {
            'candidate_symbols': state.get('candidate_symbols', []),
            'positions': state.get('positions', []),
            'account_balance': state.get('account_balance'),
            'market_data_map_keys': list(state.get('market_data_map', {}).keys()),
            'signal_data_map_keys': list(state.get('signal_data_map', {}).keys()),
            'call_count': state.get('call_count'),
            'runtime_minutes': state.get('runtime_minutes'),
            'risk_approved': state.get('risk_approved', False),
            'validation_errors': state.get('ai_decision', {}).get('validation_errors', []),
        }
        
        # 为每个通过验证的决策保存日志
        for validated_decision in validated_decisions:
            try:
                symbol = validated_decision.get('symbol', '')
                action = validated_decision.get('action', '')
                
                if not symbol:
                    logger.warning("⚠️ 决策缺少 symbol，跳过保存")
                    continue
                
                # 从原始决策中获取完整信息（reasoning, confidence等）
                original_decision = original_decision_map.get(symbol, validated_decision)
                reasoning = original_decision.get('reasoning', '')
                confidence = original_decision.get('confidence')
                
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
