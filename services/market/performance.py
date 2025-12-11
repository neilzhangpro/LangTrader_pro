"""
性能分析服务 - 计算夏普率等性能指标
"""
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from sqlalchemy import func, and_
from sqlmodel import Session, select
from sqlalchemy.orm import Query
from models.trade_record import TradeRecord
from utils.logger import logger
from config.settings import Settings
import statistics


class PerformanceAnalyzer:
    """性能分析器 - 计算交易性能指标"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
    
    def calculate_sharpe_ratio(
        self, 
        trader_id: str, 
        lookback_periods: int = 20,
        period_minutes: int = 3
    ) -> Optional[float]:
        """
        计算夏普率
        
        Args:
            trader_id: 交易员ID
            lookback_periods: 回看周期数（默认20个周期，即60分钟）
            period_minutes: 每个周期的分钟数（默认3分钟）
        
        Returns:
            夏普率，如果数据不足或表为空则返回 None
        """
        try:
            # 计算时间范围
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=lookback_periods * period_minutes)
            
            with self.settings.get_session() as session:
                # 查询最近N个周期的交易记录（已成交的）
                try:
                    statement = select(TradeRecord).where(
                        and_(
                            TradeRecord.trader_id == trader_id,
                            TradeRecord.status == 'filled',
                            TradeRecord.created_at >= start_time,
                            TradeRecord.created_at <= end_time
                        )
                    ).order_by(TradeRecord.created_at)
                    records = session.exec(statement).all()
                except Exception:
                    # 如果查询失败（包括表为空、表结构问题等），直接返回 None
                    logger.debug(f"查询trade_record表失败或表为空，无法计算夏普率")
                    return None

                # 如果数据为空或不足，直接返回 None
                if not records or len(records) < 2:
                    logger.debug(f"交易记录表为空或数据不足（{len(records)}条），无法计算夏普率")
                    return None

                # 按周期分组计算收益率
                period_returns = []
                current_period_pnl = 0.0
                current_period_num = None

                for record in records:
                    record_time = record.created_at
                    minutes_diff = (record_time - start_time).total_seconds() / 60
                    period_num = int(minutes_diff / period_minutes)
                    
                    if current_period_num is None:
                        current_period_num = period_num
                    
                    # 如果进入了下一个周期，则保存上周期收益，并重置当期pnl
                    if period_num != current_period_num:
                        period_returns.append(current_period_pnl)
                        current_period_pnl = 0.0
                        current_period_num = period_num

                    # 计算该交易的盈亏（简化：买入为负，卖出为正）
                    try:
                        trade_value = float(record.amount) * float(record.price)
                        if record.side == 'buy':
                            current_period_pnl -= trade_value
                        else:  # sell
                            current_period_pnl += trade_value
                    except Exception as e:
                        logger.warning(f"trade_record数据有误，跳过一条记录: {e}")
                        continue

                # 最后一个周期的数据加入列表
                if current_period_num is not None:
                    period_returns.append(current_period_pnl)
                
                # 筛选非零收益期数，提升鲁棒性
                valid_period_returns = [x for x in period_returns if x != 0]
                if len(valid_period_returns) < 2:
                    logger.debug(f"有效周期数不足（{len(valid_period_returns)}个），无法计算夏普率")
                    return None

                # 计算平均收益率和标准差
                mean_return = statistics.mean(valid_period_returns)
                std_return = statistics.stdev(valid_period_returns) if len(valid_period_returns) > 1 else 0.0

                if std_return == 0:
                    logger.debug("收益率标准差为0，无法计算夏普率")
                    return None

                # 夏普率 = (平均收益率 - 无风险利率) / 收益率标准差
                sharpe_ratio = mean_return / std_return if std_return > 0 else 0.0

                logger.debug(f"夏普率计算完成: {sharpe_ratio:.4f} (基于{len(valid_period_returns)}个有效周期)")
                return sharpe_ratio

        except Exception:
            # 捕获所有异常（包括KeyError、数据库连接错误等），直接返回 None
            logger.debug(f"计算夏普率失败，可能是表为空或查询异常，返回 None")
            return None
    
    def get_performance_summary(self, trader_id: str) -> Dict:
        """
        获取性能摘要
        
        Args:
            trader_id: 交易员ID
        
        Returns:
            包含性能指标的字典
        """
        # 输入验证
        if not trader_id:
            logger.warning("trader_id 为空，无法获取性能摘要")
            return {
                'sharpe_ratio': None,
                'win_rate': 0.0,
                'total_trades': 0,
                'avg_return': 0.0,
                'total_pnl': 0.0
            }
        
        try:
            sharpe_ratio = self.calculate_sharpe_ratio(trader_id)
            
            # 获取其他性能指标
            try:
                with self.settings.get_session() as session:
                    end_time = datetime.now()
                    start_time = end_time - timedelta(minutes=60)  # 最近60分钟
                    
                    try:
                        statement = select(TradeRecord).where(
                            and_(
                                TradeRecord.trader_id == trader_id,
                                TradeRecord.status == 'filled',
                                TradeRecord.created_at >= start_time
                            )
                        )
                        records = session.exec(statement).all()
                    except Exception:
                        # 如果查询失败，返回空列表
                        logger.debug(f"查询trade_record表失败或表为空")
                        records = []

                    total_trades = len(records)

                    # 数据表为空的处理
                    if not records or total_trades == 0:
                        return {
                            'sharpe_ratio': sharpe_ratio,
                            'win_rate': 0.0,
                            'total_trades': 0,
                            'avg_return': 0.0,
                            'total_pnl': 0.0
                        }
                    
                    # 计算胜率（简化：基于交易方向判断）
                    win_count = 0
                    total_pnl = 0.0
                    
                    for record in records:
                        try:
                            trade_value = float(record.amount) * float(record.price)
                            if record.side == 'sell':  # 卖出视为盈利（简化）
                                win_count += 1
                                total_pnl += trade_value
                            else:
                                total_pnl -= trade_value
                        except Exception as e:
                            logger.warning(f"trade_record数据有误，跳过一条记录: {e}")
                            continue
                    
                    win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0.0
                    avg_return = (total_pnl / total_trades) if total_trades > 0 else 0.0
                    
                    return {
                        'sharpe_ratio': sharpe_ratio,
                        'win_rate': win_rate,
                        'total_trades': total_trades,
                        'avg_return': avg_return,
                        'total_pnl': total_pnl
                    }
            except Exception:
                # 如果查询失败，返回默认值
                logger.debug(f"性能指标查询失败，返回默认值")
                return {
                    'sharpe_ratio': sharpe_ratio,
                    'win_rate': 0.0,
                    'total_trades': 0,
                    'avg_return': 0.0,
                    'total_pnl': 0.0
                }
                
        except Exception:
            # 捕获所有异常，返回默认值
            logger.debug(f"获取性能摘要失败，返回默认值")
            return {
                'sharpe_ratio': None,
                'win_rate': 0.0,
                'total_trades': 0,
                'avg_return': 0.0,
                'total_pnl': 0.0
            }

