from decision_engine.state import DecisionState
from utils.logger import logger
from typing import List, Dict
import requests
import json

class CoinPool:
    """候选币种池节点 - 从信号源获取候选币种列表"""
    
    def __init__(self, trader_cfg: dict):
        self.trader_cfg = trader_cfg

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
        
        # 3. Inside Coins - 内置AI评分（未来实现）
        if self.trader_cfg.get('use_inside_coins'):
            # TODO: 实现内置AI评分逻辑
            logger.info("⚠️  Inside Coins 功能待实现")
        
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