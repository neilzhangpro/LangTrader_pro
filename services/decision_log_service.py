"""
决策日志服务
用于将AI决策结果保存到数据库
"""
from models.decision_log import DecisionLog
from config.settings import Settings
from utils.logger import logger
from typing import Optional, Dict, Any
from decimal import Decimal
import json


class DecisionLogService:
    """决策日志服务"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
    
    def record_decision(
        self,
        trader_id: str,
        symbol: str,
        decision_state: Dict[str, Any],
        decision_result: Optional[str] = None,  # 'open_long', 'open_short', 'close_long', 'close_short', 'hold', 'wait'
        reasoning: Optional[str] = None,
        confidence: Optional[Decimal] = None
    ) -> Optional[DecisionLog]:
        """记录决策到数据库
        
        Args:
            trader_id: 交易员ID
            symbol: 币种符号（如 'BTC/USDT'）
            decision_state: 决策状态字典（LangGraph state 的快照或部分状态）
            decision_result: 决策结果，如 'open_long', 'open_short', 'close_long', 'close_short', 'hold', 'wait'
            reasoning: AI决策理由
            confidence: 决策置信度 (0-100，需要转换为 0-1)
            
        Returns:
            DecisionLog对象，如果保存失败则返回None
        """
        try:
            # 决策状态直接作为字典传递，SQLModel 会自动处理 JSONB
            # 如果传入的是字符串，尝试解析
            if isinstance(decision_state, str):
                try:
                    decision_state = json.loads(decision_state)
                except Exception as e:
                    logger.warning(f"⚠️ 解析决策状态JSON失败: {e}，使用简化状态")
                    decision_state = {"error": "解析失败", "symbol": symbol}
            
            # 转换置信度：如果 confidence 是 0-100 范围，转换为 0-1
            confidence_decimal = None
            if confidence is not None:
                try:
                    if isinstance(confidence, (int, float)):
                        # 如果 confidence > 1，假设是 0-100 范围，转换为 0-1
                        if confidence > 1:
                            confidence_decimal = Decimal(str(confidence / 100))
                        else:
                            confidence_decimal = Decimal(str(confidence))
                    elif isinstance(confidence, Decimal):
                        if confidence > 1:
                            confidence_decimal = confidence / Decimal('100')
                        else:
                            confidence_decimal = confidence
                except Exception as e:
                    logger.warning(f"⚠️ 转换置信度失败: {e}")
            
            decision_log = DecisionLog(
                trader_id=trader_id,
                symbol=symbol,
                decision_state=decision_state,  # 直接存储为字典，SQLModel 会自动处理 JSONB
                decision_result=decision_result,
                reasoning=reasoning,
                confidence=confidence_decimal
            )
            
            with self.settings.get_session() as session:
                session.add(decision_log)
                try:
                    session.commit()
                    # 只在成功提交后才 refresh
                    try:
                        session.refresh(decision_log)
                        logger.info(
                            f"✅ 决策日志已保存: {symbol} "
                            f"决策={decision_result or 'N/A'} "
                            f"置信度={confidence_decimal or 'N/A'}"
                        )
                        return decision_log
                    except Exception as refresh_error:
                        # refresh 失败不影响记录已保存的事实
                        logger.warning(f"⚠️ 刷新决策日志失败，但记录已保存: {refresh_error}")
                        logger.info(
                            f"✅ 决策日志已保存: {symbol} "
                            f"决策={decision_result or 'N/A'} "
                            f"置信度={confidence_decimal or 'N/A'}"
                        )
                        return decision_log
                except Exception as commit_error:
                    session.rollback()
                    logger.error(f"❌ 提交决策日志失败: {commit_error}", exc_info=True)
                    # 检查是否是外键约束错误
                    error_str = str(commit_error).lower()
                    if 'trader' in error_str or 'foreign key' in error_str or 'constraint' in error_str:
                        logger.error(f"❌ trader_id={trader_id} 可能不存在于 traders 表中")
                    raise
                
        except Exception as e:
            logger.error(f"❌ 保存决策日志失败: {e}", exc_info=True)
            return None

