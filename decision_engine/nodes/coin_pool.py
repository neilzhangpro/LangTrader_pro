from decision_engine.state import DecisionState
from utils.logger import logger
from typing import List, Dict, Optional
import requests
import json

# 前向引用，避免循环导入
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from services.market.symbol_filter import SymbolFilter

class CoinPool:
    """候选币种池节点 - 从信号源获取候选币种列表"""
    
    def __init__(self, trader_cfg: dict, symbol_filter: Optional['SymbolFilter'] = None):
        self.trader_cfg = trader_cfg
        self.symbol_filter = symbol_filter  # 接收 SymbolFilter 引用（对应 Nofx 的 FilterSymbol）

    def get_candidate_coins(self, state: DecisionState) -> DecisionState:
        """获取候选币种列表"""
        logger.info("🔍 开始获取候选币种...")
        
        candidate_coins = []
        coin_sources = {}  # 记录每个币种的来源
        
        # 1. Coin Pool (AI500) - 算法评分Top币种
        if self.trader_cfg.get('use_coin_pool'):
            coin_pool_url = self.trader_cfg.get('coin_pool_url', '')
            if coin_pool_url:
                try:
                    coins = self._fetch_coin_pool(coin_pool_url)
                    for coin in coins:
                        symbol = coin.get('symbol', coin) if isinstance(coin, dict) else coin
                        candidate_coins.append(symbol)
                        coin_sources[symbol] = coin_sources.get(symbol, []) + ['ai500']
                    logger.info(f"✅ 从 Coin Pool 获取 {len(coins)} 个币种")
                except Exception as e:
                    logger.error(f"❌ 获取 Coin Pool 失败: {e}")
        
        # 2. OI Top - 持仓量增长Top币种
        if self.trader_cfg.get('use_oi_top'):
            oi_top_url = self.trader_cfg.get('oi_top_url', '')
            if oi_top_url:
                try:
                    coins = self._fetch_oi_top(oi_top_url)
                    for coin in coins:
                        symbol = coin.get('symbol', coin) if isinstance(coin, dict) else coin
                        candidate_coins.append(symbol)
                        coin_sources[symbol] = coin_sources.get(symbol, []) + ['oi_top']
                    logger.info(f"✅ 从 OI Top 获取 {len(coins)} 个币种")
                except Exception as e:
                    logger.error(f"❌ 获取 OI Top 失败: {e}")
        
        # 3. Inside Coins - 内置AI评分（从 SymbolFilter 获取筛选后的币种）
        if self.trader_cfg.get('use_inside_coins'):
            if self.symbol_filter:
                # 从 SymbolFilter 获取筛选后的币种（对应 Nofx 的 FilterSymbol）
                filtered_symbols = self.symbol_filter.get_filtered_symbols()
                
                # 如果筛选结果为空，且筛选任务正在运行，必须等待筛选完成
                if not filtered_symbols:
                    if hasattr(self.symbol_filter, '_running') and self.symbol_filter._running:
                        logger.info("⏳ 内置AI评分正在运行中，等待筛选结果完成...")
                        import time
                        
                        # 等待筛选完成（最多等待10分钟，每2秒检查一次）
                        max_wait_time = 600  # 10分钟
                        check_interval = 2  # 每2秒检查一次
                        elapsed = 0
                        
                        while elapsed < max_wait_time:
                            time.sleep(check_interval)
                            elapsed += check_interval
                            
                            filtered_symbols = self.symbol_filter.get_filtered_symbols()
                            if filtered_symbols:
                                logger.info(f"✅ 等待 {elapsed} 秒后，获取到 {len(filtered_symbols)} 个筛选币种")
                                break
                            
                            # 每10秒输出一次等待日志
                            if elapsed % 10 == 0:
                                logger.info(f"⏳ 继续等待筛选结果... ({elapsed}/{max_wait_time}秒)")
                        
                        if not filtered_symbols:
                            logger.error(f"❌ 等待 {max_wait_time} 秒后筛选结果仍未准备好，使用配置币种")
                    else:
                        logger.warning("⚠️ 内置AI评分筛选任务未运行，使用配置币种")
                
                # 如果获取到筛选结果，添加到候选列表
                if filtered_symbols:
                    candidate_coins.extend(filtered_symbols)
                    coin_sources.update({symbol: coin_sources.get(symbol, []) + ['inside_ai'] for symbol in filtered_symbols})
                    logger.info(f"✅ 从内置AI评分获取 {len(filtered_symbols)} 个币种: {filtered_symbols[:5]}...")
            else:
                logger.warning("⚠️ SymbolFilter 未提供，无法使用内置AI评分")
        
        # 4. 如果没有从信号源获取到，使用配置的币种
        if not candidate_coins:
            #从数据库读取配置的币种
            trading_coins = self.trader_cfg.get('trading_coins', ["BTC/USDT"])
            if trading_coins:
                candidate_coins = trading_coins if isinstance(trading_coins, list) else trading_coins.split(',')
                logger.info(f"✅ 使用配置的币种: {candidate_coins}")
            else:
                # 最后回退到默认币种
                candidate_coins = ["BTC/USDT"]
                logger.info(f"✅ 使用默认币种: {candidate_coins}")
        
        # 去重，保持顺序
        seen = set()
        unique_coins = []
        for coin in candidate_coins:
            if coin not in seen:
                seen.add(coin)
                unique_coins.append(coin)
        
        # 更新状态 - 确保返回包含 candidate_symbols 的字典
        # LangGraph 需要返回包含更新字段的字典
        updated_state = {
            'candidate_symbols': unique_coins,
            # 保留其他字段，确保状态完整
            'account_balance': state.get('account_balance', 0.0),
            'positions': state.get('positions', []),
            'market_data_map': state.get('market_data_map', {}),
            'signal_data_map': state.get('signal_data_map', {}),
            'ai_decision': state.get('ai_decision'),
            'risk_approved': state.get('risk_approved', False),
        }
        
        logger.info(f"✅ 最终候选币种列表 ({len(unique_coins)} 个): {unique_coins}")
        logger.debug(f"📝 返回状态 keys: {list(updated_state.keys())}")
        logger.debug(f"📝 candidate_symbols 值: {updated_state.get('candidate_symbols')}")
        
        # 返回更新后的 state
        return updated_state
    
    def _fetch_coin_pool(self, url: str) -> List:
        """从 Coin Pool API 获取币种列表"""
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            # 根据实际API格式解析
            # 假设返回格式: {"coins": ["BTCUSDT", "ETHUSDT", ...]} 或 [{"symbol": "BTCUSDT"}, ...]
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return data.get('coins', data.get('data', []))
            return []
        except Exception as e:
            logger.error(f"获取 Coin Pool 失败: {e}")
            return []
    
    def _fetch_oi_top(self, url: str) -> List:
        """从 OI Top API 获取币种列表"""
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            # 根据实际API格式解析
            # 假设返回格式: {"positions": [{"symbol": "BTCUSDT", ...}, ...]} 或 [{"symbol": "BTCUSDT"}, ...]
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return data.get('positions', data.get('data', data.get('coins', [])))
            return []
        except Exception as e:
            logger.error(f"获取 OI Top 失败: {e}")
            return []