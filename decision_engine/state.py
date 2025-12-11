from typing import Dict, List
from typing import TypedDict, Optional


class DecisionState(TypedDict, total=False):
    #处理的币种
    exchange_config: Dict #交易所配置
    candidate_symbols: List[str] #候选币种列表
    coin_sources: Dict[str, List[str]]  # 币种来源信息（ai500/oi_top/inside_ai）
    oi_top_data_map: Dict[str, Dict]  # OI Top 详细信息
    #账户信息:余额, 持仓
    account_balance: float
    positions: List[Dict]

    #市场信息
    market_data_map: Dict[str, Dict]
    #信号信息
    signal_data_map: Dict[str, Dict]
    #性能信息
    performance: Optional[Dict]  # 性能指标（夏普率等）
    #市场警报信息
    alerts: Optional[List[Dict]]  # 市场异常警报列表
    #AI决策信息:决策结果, 决策理由, 决策置信度,执行动作(买入,卖出,持有)
    ai_decision: Optional[Dict[str,Dict]]
    #风险检查结果,AI的决策是否通过了风险检查
    risk_approved: bool
    #交易执行结果
    execution_results: Optional[List[Dict]]  # 交易执行结果列表
    #运行状态（用于AI决策提示词）
    runtime_minutes: Optional[int]  # 运行时长（分钟）
    call_count: Optional[int]  # 调用次数