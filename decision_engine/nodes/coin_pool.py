from decision_engine.state import DecisionState
from utils.logger import logger
from typing import List, Dict, Optional
from services.market.coin_pool_service import CoinPoolService

# 前向引用，避免循环导入
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from services.market.symbol_filter import SymbolFilter

class CoinPool:
    """候选币种池节点 - 从信号源获取候选币种列表"""
    
    # 等待筛选完成的配置常量
    MAX_WAIT_TIME_SECONDS = 120  # 最多等待2分钟
    CHECK_INTERVAL_SECONDS = 2  # 每2秒检查一次
    LOG_INTERVAL_SECONDS = 10  # 每10秒输出一次等待日志
    
    def __init__(self, trader_cfg: dict, symbol_filter: Optional['SymbolFilter'] = None):
        self.trader_cfg = trader_cfg
        self.symbol_filter = symbol_filter  # 接收 SymbolFilter 引用（对应 Nofx 的 FilterSymbol）
        
        # 创建币种池服务
        self.coin_pool_service = CoinPoolService(
            coin_pool_url=trader_cfg.get('coin_pool_url'),
            oi_top_url=trader_cfg.get('oi_top_url'),
            use_default_coins=trader_cfg.get('use_default_coins', False),
            timeout=30,
            max_retries=3
        )

    def get_candidate_coins(self, state: DecisionState) -> DecisionState:
        """获取候选币种列表"""
        logger.info("开始获取候选币种...")
        
        candidate_coins = []
        coin_sources = {}  # 记录每个币种的来源
        
        # 1. Coin Pool (AI500) - 算法评分Top币种
        if self.trader_cfg.get('use_coin_pool'):
            try:
                coins = self.coin_pool_service.get_coin_pool()
                for coin in coins:
                    if coin and coin.symbol:
                        candidate_coins.append(coin.symbol)
                        coin_sources[coin.symbol] = coin_sources.get(coin.symbol, []) + ['ai500']
                logger.info(f"从Coin Pool获取{len(coins)}个币种")
            except Exception as e:
                logger.error(f"获取Coin Pool失败: {e}", exc_info=True)
        
        # 2. OI Top - 持仓量增长Top币种
        if self.trader_cfg.get('use_oi_top'):
            try:
                coins = self.coin_pool_service.get_oi_top()
                for coin in coins:
                    if coin and coin.symbol:
                        candidate_coins.append(coin.symbol)
                        coin_sources[coin.symbol] = coin_sources.get(coin.symbol, []) + ['oi_top']
                logger.info(f"从OI Top获取{len(coins)}个币种")
            except Exception as e:
                logger.error(f"获取OI Top失败: {e}", exc_info=True)
        
        # 3. Inside Coins - 内置AI评分（从 SymbolFilter 获取筛选后的币种）
        if self.trader_cfg.get('use_inside_coins'):
            logger.info("开启了内置AI评分")
            if self.symbol_filter:
                logger.info("symbol_filter is not None")
                # 从 SymbolFilter 获取筛选后的币种（对应 Nofx 的 FilterSymbol）
                filtered_symbols = self.symbol_filter.get_filtered_symbols()
                logger.info(f"filtered_symbols: {filtered_symbols}")
                logger.info(f"is running: {self.symbol_filter._running}")
                # 如果筛选结果为空，且筛选任务正在运行，等待筛选完成
                if not filtered_symbols:
                    if hasattr(self.symbol_filter, '_running') and self.symbol_filter._running:
                        logger.info("⏳ 内置AI评分正在运行中，等待筛选结果完成...")
                        import time
                        
                        # 等待筛选完成
                        elapsed = 0
                        
                        while elapsed < self.MAX_WAIT_TIME_SECONDS:
                            time.sleep(self.CHECK_INTERVAL_SECONDS)
                            elapsed += self.CHECK_INTERVAL_SECONDS
                            
                            filtered_symbols = self.symbol_filter.get_filtered_symbols()
                            if filtered_symbols:
                                logger.info(f"等待{elapsed}秒后，获取到{len(filtered_symbols)}个筛选币种")
                                break
                            
                            # 定期输出等待日志
                            if elapsed % self.LOG_INTERVAL_SECONDS == 0:
                                logger.info(f"继续等待筛选结果... ({elapsed}/{self.MAX_WAIT_TIME_SECONDS}秒)")
                        
                        if not filtered_symbols:
                            logger.warning(f"等待{self.MAX_WAIT_TIME_SECONDS}秒后筛选结果仍未准备好，将使用配置币种")
                    else:
                        logger.warning("⚠️ 内置AI评分筛选任务未运行，使用配置币种")
                
                # 如果获取到筛选结果，添加到候选列表
                if filtered_symbols:
                    candidate_coins.extend(filtered_symbols)
                    coin_sources.update({symbol: coin_sources.get(symbol, []) + ['inside_ai'] for symbol in filtered_symbols})
                    logger.info(f"从内置AI评分获取{len(filtered_symbols)}个币种")
            else:
                logger.debug("SymbolFilter未提供，无法使用内置AI评分")
        
        # 4. 如果没有从信号源获取到，使用配置的币种
        if not candidate_coins:
            trading_coins = self.trader_cfg.get('trading_coins', ["BTC/USDT"])
            if trading_coins:
                candidate_coins = trading_coins if isinstance(trading_coins, list) else trading_coins.split(',')
                logger.info(f"使用配置的币种: {candidate_coins}")
            else:
                candidate_coins = ["BTC/USDT"]
                logger.info(f"使用默认币种: {candidate_coins}")
        
        # 去重，保持顺序
        seen = set()
        unique_coins = []
        unique_coin_sources = {}  # 去重后的币种来源
        for coin in candidate_coins:
            if coin not in seen:
                seen.add(coin)
                unique_coins.append(coin)
                # 保留去重后的来源信息
                if coin in coin_sources:
                    unique_coin_sources[coin] = coin_sources[coin]
        
        # 获取 OI Top 详细信息（如果启用）
        oi_top_data_map = {}
        if self.trader_cfg.get('use_oi_top'):
            try:
                oi_top_details = self.coin_pool_service.get_oi_top_details()
                # 转换为字典格式，key 为 symbol
                for symbol, position in oi_top_details.items():
                    oi_top_data_map[symbol] = {
                        'symbol': position.symbol,
                        'oi_change': position.oi_change,
                        'oi_change_percent': position.oi_change_percent,
                        'time_range': position.time_range
                    }
                if oi_top_data_map:
                    logger.debug(f"获取OI Top详细信息: {len(oi_top_data_map)}个币种")
            except Exception as e:
                logger.warning(f"获取OI Top详细信息失败: {e}")
        logger.info("开始更新状态...")
        # 更新状态
        updated_state = {
            'candidate_symbols': unique_coins,
            'coin_sources': unique_coin_sources,
            'oi_top_data_map': oi_top_data_map,
            'account_balance': state.get('account_balance', 0.0),
            'positions': state.get('positions', []),
            'market_data_map': state.get('market_data_map', {}),
            'signal_data_map': state.get('signal_data_map', {}),
            'ai_decision': state.get('ai_decision'),
            'risk_approved': state.get('risk_approved', False),
        }
        
        logger.info(f"最终候选币种列表({len(unique_coins)}个): {unique_coins[:10]}{'...' if len(unique_coins) > 10 else ''}")
        return updated_state
    