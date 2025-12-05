from models.trader import Trader
from utils.logger import logger
from config.settings import Settings
import threading
from typing import Optional
from datetime import datetime, timedelta
from services.ExchangeService import ExchangeService
from decision_engine.graph_builder import GraphBuilder
from decision_engine.state import DecisionState
from services.market.monitor import MarketMonitor
import asyncio
from services.ExchangeService import ExchangeService

class AutoTrader:
    """
    AutoTrader class
    """

    def __init__(self, trader_cfg: dict, settings: Settings):
        self.trader_cfg = trader_cfg
        self.settings = settings
        self.trader_id = trader_cfg.get('id')
        self.trader_name = trader_cfg.get('name')
        self.exchange_service = ExchangeService(
            exchange_config=trader_cfg.get('exchange', {}),
            settings=settings
        )
        

         # 创建市场数据监控器（后台运行WebSocket）
        self.market_monitor = MarketMonitor(self.exchange_service.exchange_config)

        #运行状态
        self.is_running = False
        self._stop_event = threading.Event()
        self._scan_thread: Optional[threading.Thread] = None
        
        logger.info(f"Trader {self.trader_name} initialized")
    
    def start(self):
        #启动交易员
        if self.is_running:
            logger.warning(f"Trader {self.trader_name} is already running")
            return
        
        self.is_running = True
        self._stop_event.clear()
        
        # 启动市场数据监控器
        self.market_monitor.start()
        logger.info(f"✅ 市场数据监控器已启动")
        
        # 注意：不再在这里预加载币种
        # 币种会在每次扫描时从信号源动态获取
        # 如果需要预加载常用币种，可以在这里添加
        
        #启动扫描线程
        self._scan_thread = threading.Thread(
            target=self._scan_loop,
            daemon=True,
            name=f"Trader-{self.trader_name}"
        )
        self._scan_thread.start()
        logger.info(f"Trader {self.trader_name} started")
    
    def stop(self):
        #停止交易员
        if not self.is_running:
            logger.warning(f"Trader {self.trader_name} is not running")
            return
        
        self.is_running = False
        self._stop_event.set()
        
        # 停止市场数据监控器
        self.market_monitor.stop()
        
        if self._scan_thread:
            self._scan_thread.join()
            self._scan_thread = None
        logger.info(f"Trader {self.trader_name} stopped")
    
    def _scan_loop(self):
        """扫描循环（在独立线程中运行）"""
        scan_interval = timedelta(minutes=self.trader_cfg['scan_interval_minutes'])
        next_scan_time = datetime.now()

        while self.is_running and not self._stop_event.is_set():
            try:
                # 等待到下次扫描时间
                wait_time = (next_scan_time - datetime.now()).total_seconds()
                if wait_time > 0:
                    self._stop_event.wait(timeout=wait_time)
                
                if self._stop_event.is_set():
                    break
                
                # 执行扫描
                self._scan_once()
                
                # 计算下次扫描时间
                next_scan_time = datetime.now() + scan_interval
                
            except Exception as e:
                logger.error(f"❌ 交易员 {self.trader_name} 扫描循环错误: {e}", exc_info=True)
                # 出错后等待一段时间再继续
                self._stop_event.wait(timeout=60)
    
    def _scan_once(self):
        """执行单次扫描（批量模式：一次处理所有候选币种）"""
        logger.info(f"🔍 [{self.trader_name}] 执行扫描...")
        try:
            logger.info(f"📊 [{self.trader_name}] LangGraph 决策引擎运行中...")
            
            # 构建图（只需要构建一次）
            graph_builder = GraphBuilder(
                self.exchange_service.exchange_config,
                trader_cfg=self.trader_cfg,
                market_monitor=self.market_monitor,
                exchange_service=self.exchange_service
            )
            graph = graph_builder.build_graph()
            
            # 初始化状态（批量模式）
            # candidate_symbols 会在 coin_pool 节点中填充
            decision_state = DecisionState(
                candidate_symbols=[],  # 初始为空，coin_pool 节点会填充
                account_balance=0.0,  # TODO: 从交易所获取实际余额
                positions=[],  # TODO: 从交易所获取实际持仓
                market_data_map={},  # data_collector 节点会填充
                signal_data_map={},  # signal_analyzer 节点会填充
                ai_decision=None,  # ai_decision 节点会填充
                risk_approved=False,  # risk_manager 节点会填充
            )
            
            # 一次调用处理所有候选币种
            final_state = graph.invoke(decision_state)
            
            # 处理结果
            if final_state.get('ai_decision'):
                decisions = final_state['ai_decision'].get('decisions', [])
                logger.info(f"✅ AI 决策完成，共 {len(decisions)} 个币种的决策")
                for decision in decisions:
                    logger.info(f"  - {decision.get('symbol')}: {decision.get('action')} (信心度: {decision.get('confidence', 0)})")
            else:
                logger.info("⚠️  未生成 AI 决策")
            
            logger.info(f"📊 [{self.trader_name}] LangGraph 决策引擎运行完成")
        except Exception as e:
            logger.error(f"❌ 交易员 {self.trader_name} 扫描错误: {e}", exc_info=True)
    
    def get_status(self):
        """获取交易员状态"""    
        return {
            'id': self.trader_id,
            'name': self.trader_name,
            'is_running': self.is_running,
            'scan_interval_minutes': self.trader_cfg.get('scan_interval_minutes', 3),
        }