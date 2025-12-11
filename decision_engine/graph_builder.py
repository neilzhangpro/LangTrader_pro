from langgraph.graph import StateGraph, START, END
from decision_engine.state import DecisionState
from decision_engine.nodes.data_collector import DataCollector
from decision_engine.nodes.coin_pool import CoinPool
from utils.logger import logger
from typing import Optional
from services.market.monitor import MarketMonitor
from decision_engine.nodes.signal_analyzer import SignalAnalyzer
from decision_engine.nodes.AI_decision import AIDecision
from decision_engine.nodes.Risk_check import RiskCheck
from decision_engine.nodes.execution_trade import ExecutionTrade

# 前向引用，避免循环导入
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from services.market.symbol_filter import SymbolFilter
    from config.settings import Settings

class GraphBuilder:
    def __init__(
        self, 
        market_monitor: Optional[MarketMonitor] = None, 
        trader_cfg: Optional[dict] = None, 
        symbol_filter: Optional['SymbolFilter'] = None,
        trader_id: Optional[str] = None,
        settings: Optional['Settings'] = None
    ):
        """
        初始化图构建器
        
        Args:
            market_monitor: 市场数据监控器
            trader_cfg: 交易员配置
            symbol_filter: 币种筛选器
            trader_id: 交易员ID
            settings: 设置对象
        """
        self.graph = StateGraph(DecisionState)
        self.market_monitor = market_monitor
        self.trader_cfg = trader_cfg or {}
        # 创建节点实例（不再传递exchange_config，节点从state读取）
        self.data_collector = DataCollector(market_monitor=market_monitor)
        self.coin_pool = CoinPool(trader_cfg, symbol_filter=symbol_filter)
        self.signal_analyzer = SignalAnalyzer(
            trader_id=trader_id, 
            settings=settings
        )
        self.AI_decision = AIDecision(
            trader_cfg, 
            settings=settings,
            trader_id=trader_id
        )
        self.risk_check = RiskCheck(
            trader_cfg, 
            settings=settings,
            trader_id=trader_id
        )
        self.execution_trade = ExecutionTrade(
            trader_cfg=trader_cfg,
            trader_id=trader_id
        )


    def build_graph(self):
        """构建决策引擎图（批量模式）"""
        # 节点顺序：START -> coin_pool -> data_collector -> signal_analyzer -> AI_decision -> risk_check -> execution_trade -> END
        self.graph.add_node("coin_pool", self.coin_pool.get_candidate_coins)
        self.graph.add_node("data_collector", self.data_collector.run)
        self.graph.add_node("signal_analyzer", self.signal_analyzer.run)
        self.graph.add_node("AI_decision", self.AI_decision.run)
        self.graph.add_node("risk_check", self.risk_check.run)
        self.graph.add_node("execution_trade", self.execution_trade.run)
        
        # 边的连接
        self.graph.add_edge(START, "coin_pool")
        self.graph.add_edge("coin_pool", "data_collector")
        self.graph.add_edge("data_collector", "signal_analyzer")
        self.graph.add_edge("signal_analyzer", "AI_decision")
        self.graph.add_edge("AI_decision", "risk_check")
        self.graph.add_edge("risk_check", "execution_trade")
        self.graph.add_edge("execution_trade", END)
        
        compiled_graph = self.graph.compile()
        return compiled_graph