"""
交易员管理器
负责启动、停止、监控交易员
"""
from config.settings import Settings
from models import AIModel
from models.trader import Trader
from typing import Dict
from sqlmodel import select
from services.prompt_service import PromptService
import threading
from models.user import User
from typing import List
import json
from utils.logger import logger
from models.system_config import SystemConfig
from models.exchange import Exchange
from models.signal_source import UserSignalSource
from services.Auto_trader import AutoTrader


class TraderManager:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.prompt_service = PromptService(settings)
        self.traders: Dict[str, AutoTrader] = {}
        self._lock = threading.Lock()

    def load_traders_from_database(self):
    #从数据库加载交易员

        with self._lock:
            # 获取所有用户，并在会话关闭前提取 user_ids
            with self.settings.get_session() as session:
                users = session.exec(select(User)).all()
                # 在会话关闭前提取所有 user.id，避免 DetachedInstanceError
                user_ids = [user.id for user in users]
                logger.info(f"📋 发现 {len(users)} 个用户，开始加载所有交易员配置...")
            
            all_trader_ids: List[str] = []  # 改为存储 ID 列表
            trader_id_to_user_id: Dict[str, str] = {}  # 存储 trader_id -> user_id 映射
            
            for user_id in user_ids:
                # 获取每个用户的交易员
                with self.settings.get_session() as session:
                    traders = session.exec(
                        select(Trader).where(Trader.user_id == user_id)
                    ).all()
                    logger.info(f"📋 用户 {user_id}: {len(traders)} 个交易员")
                    # 在会话关闭前提取所有 trader.id
                    for trader in traders:
                        trader_id = str(trader.id)  # 在会话内提取 ID
                        all_trader_ids.append(trader_id)
                        trader_id_to_user_id[trader_id] = user_id
            
            logger.info(f"📋 总共加载 {len(all_trader_ids)} 个交易员配置")
            
            #获取系统配置
            config = self._get_system_config()
            #success
            success_count_traders = 0
            for trader_id in all_trader_ids:
                if self._load_single_trader(trader_id, trader_id_to_user_id[trader_id], config):
                    success_count_traders += 1
            
            logger.info(f"📋 成功加载 {success_count_traders} 个交易员配置")
            logger.info(f"📋 失败加载 {len(all_trader_ids) - success_count_traders} 个交易员配置")
            
            return success_count_traders

    def _get_system_config(self) -> dict:
        """获取系统配置"""
        config = {
            'max_daily_loss': 10.0,
            'max_drawdown': 20.0,
            'stop_trading_minutes': 60,
            'default_coins': []
        }
        
        with self.settings.get_session() as session:
            # 获取系统配置
            max_daily_loss = session.exec(
                select(SystemConfig).where(SystemConfig.key == "max_daily_loss")
            ).first()
            if max_daily_loss:
                try:
                    config['max_daily_loss'] = float(max_daily_loss.value)
                except ValueError:
                    pass
            
            max_drawdown = session.exec(
                select(SystemConfig).where(SystemConfig.key == "max_drawdown")
            ).first()
            if max_drawdown:
                try:
                    config['max_drawdown'] = float(max_drawdown.value)
                except ValueError:
                    pass
            
            stop_trading_minutes = session.exec(
                select(SystemConfig).where(SystemConfig.key == "stop_trading_minutes")
            ).first()
            if stop_trading_minutes:
                try:
                    config['stop_trading_minutes'] = int(stop_trading_minutes.value)
                except ValueError:
                    pass
            
            default_coins = session.exec(
                select(SystemConfig).where(SystemConfig.key == "default_coins")
            ).first()
            if default_coins and default_coins.value:
                try:
                    config['default_coins'] = json.loads(default_coins.value)
                except json.JSONDecodeError:
                    logger.warning("⚠️ 解析默认币种配置失败，使用空列表")
                    config['default_coins'] = []
        
        return config

    def _build_trader_config(
        self,
        trader_cfg_dict: dict,  # 改为字典
        ai_model_dict: dict,     # 改为字典
        exchange_dict: dict,     # 改为字典
        coin_pool_url: str,
        oi_top_url: str,
        system_config: dict,
        trading_coins: List[str],
        prompt: str
    ) -> dict:
        """构建 trader 配置字典"""
        config = {
            'id': trader_cfg_dict['id'],
            'name': trader_cfg_dict['name'],
            'user_id': trader_cfg_dict['user_id'],
            'ai_model': {
                'id': ai_model_dict['id'],
                'enabled': ai_model_dict['enabled'],
                'provider': ai_model_dict['provider'],
                'api_key': ai_model_dict['api_key'],
                'base_url': ai_model_dict['base_url'],
                'model_name': ai_model_dict['model_name'],
            },
            'exchange': {
                'id': exchange_dict['id'],
                'name': exchange_dict['name'],
                'type': exchange_dict['type'],
                'api_key': exchange_dict['api_key'],
                'secret_key': exchange_dict['secret_key'],
                'testnet': exchange_dict['testnet'],
                'wallet_address': exchange_dict['wallet_address'],
            },
            'initial_balance': float(trader_cfg_dict['initial_balance']),
            'scan_interval_minutes': trader_cfg_dict['scan_interval_minutes'],
            'btc_eth_leverage': trader_cfg_dict['btc_eth_leverage'],
            'altcoin_leverage': trader_cfg_dict['altcoin_leverage'],
            'trading_coins': trading_coins,
            'use_coin_pool': trader_cfg_dict['use_coin_pool'],
            'use_oi_top': trader_cfg_dict['use_oi_top'],
            'use_inside_coins': trader_cfg_dict['use_inside_coins'],
            'coin_pool_url': coin_pool_url,
            'oi_top_url': oi_top_url,
            'prompt': prompt,
            'is_cross_margin': trader_cfg_dict['is_cross_margin'],
            'decision_graph_config': trader_cfg_dict.get('decision_graph_config'),
            'max_daily_loss': system_config.get('max_daily_loss', 10.0),
            'max_drawdown': system_config.get('max_drawdown', 20.0),
            'stop_trading_minutes': system_config.get('stop_trading_minutes', 60),
        }
        return config

    def _load_single_trader(self, trader_id: str, user_id: str, system_config):
        """加载单个交易员（使用 trader_id 重新查询）"""
        #check if have loaded this trader
        if trader_id in self.traders:
            logger.warning(f"📋 交易员 {trader_id} 已加载")
            return False
        
        # 重新查询 trader 配置（在新会话中）
        with self.settings.get_session() as session:
            trader_cfg = session.exec(
                select(Trader).where(Trader.id == trader_id)
            ).first()
            
            if not trader_cfg:
                logger.warning(f"⚠️ 交易员 {trader_id} 不存在")
                return False
            
            # 在会话内提取 trader_cfg 的所有属性值
            trader_cfg_dict = {
                'id': trader_cfg.id,
                'name': trader_cfg.name,
                'user_id': trader_cfg.user_id,
                'ai_model_id': trader_cfg.ai_model_id,
                'exchange_id': trader_cfg.exchange_id,
                'initial_balance': trader_cfg.initial_balance,
                'scan_interval_minutes': trader_cfg.scan_interval_minutes,
                'btc_eth_leverage': trader_cfg.btc_eth_leverage,
                'altcoin_leverage': trader_cfg.altcoin_leverage,
                'use_coin_pool': trader_cfg.use_coin_pool,
                'use_oi_top': trader_cfg.use_oi_top,
                'use_inside_coins': trader_cfg.use_inside_coins,
                'is_cross_margin': trader_cfg.is_cross_margin,
                'decision_graph_config': trader_cfg.decision_graph_config,
            }
            
            trader_name = trader_cfg.name
            ai_model_id = trader_cfg.ai_model_id
            exchange_id = trader_cfg.exchange_id
            use_coin_pool = trader_cfg.use_coin_pool
            use_oi_top = trader_cfg.use_oi_top
            trading_symbols = trader_cfg.trading_symbols
            custom_coins = trader_cfg.custom_coins
            
            #获取AI模型配置
            ai_model = session.exec(
                select(AIModel).where(
                    AIModel.id == ai_model_id,
                    AIModel.user_id == user_id
                )
            ).first()
            
            if not ai_model:
                logger.warning(f"📋 交易员 {trader_id} 的AI模型 {ai_model_id} 不存在")
                return False
            
            if not ai_model.enabled:
                logger.warning(f"📋 交易员 {trader_id} 的AI模型 {ai_model_id} 未启用")
                return False
            
            # 在会话内提取 ai_model 的所有属性值
            ai_model_dict = {
                'id': ai_model.id,
                'enabled': ai_model.enabled,
                'provider': ai_model.provider,
                'api_key': ai_model.api_key,
                'base_url': ai_model.base_url,
                'model_name': ai_model.model_name,
            }
            
            # 获取交易所配置
            exchange = session.exec(
                select(Exchange).where(
                    Exchange.id == exchange_id,
                    Exchange.user_id == user_id
                )
            ).first()
            
            if not exchange:
                logger.warning(f"⚠️ 交易员 {trader_name} 的交易所 {exchange_id} 不存在，跳过")
                return False
            
            if not exchange.enabled:
                logger.warning(f"⚠️ 交易员 {trader_name} 的交易所 {exchange.name} 未启用，跳过")
                return False
            
            # 在会话内提取 exchange 的所有属性值
            exchange_dict = {
                'id': exchange.id,
                'name': exchange.name,
                'type': exchange.type,
                'api_key': exchange.api_key,
                'secret_key': exchange.secret_key,
                'testnet': exchange.testnet,
                'wallet_address': exchange.wallet_address,
            }
            
            # 获取用户信号源配置
            signal_source = session.exec(
                select(UserSignalSource).where(
                    UserSignalSource.user_id == user_id
                )
            ).first()
            
            coin_pool_url = signal_source.coin_pool_url if signal_source else ""
            oi_top_url = signal_source.oi_top_url if signal_source else ""
            
            if not signal_source:
                logger.info(f"🔍 用户 {user_id} 暂未配置信号源")
        
        # 会话已关闭，现在使用提取的值
        # 处理交易币种列表
        trading_coins = self._parse_trading_coins(trading_symbols, custom_coins)
        if not trading_coins:
            trading_coins = system_config.get('default_coins', [])
        
        # 根据交易员配置决定是否使用信号源
        effective_coin_pool_url = ""
        if use_coin_pool and coin_pool_url:
            effective_coin_pool_url = coin_pool_url
            logger.info(f"✓ 交易员 {trader_name} 启用 COIN POOL 信号源: {coin_pool_url}")
        
        effective_oi_top_url = ""
        if use_oi_top and oi_top_url:
            effective_oi_top_url = oi_top_url
            logger.info(f"✓ 交易员 {trader_name} 启用 OI TOP 信号源: {oi_top_url}")
        
        # 获取提示词
        prompt = self.prompt_service.get_prompt_by_trader(trader_id)
        if not prompt:
            logger.warning(f"⚠️ 交易员 {trader_name} 无法获取提示词，跳过")
            return False
        
        # 构建 trader 配置（使用字典，不依赖会话）
        trader_config = self._build_trader_config(
            trader_cfg_dict=trader_cfg_dict,
            ai_model_dict=ai_model_dict,
            exchange_dict=exchange_dict,
            coin_pool_url=effective_coin_pool_url,
            oi_top_url=effective_oi_top_url,
            system_config=system_config,
            trading_coins=trading_coins,
            prompt=prompt
        )
        
        # 创建 trader 实例（这里需要实现 AutoTrader 类）
        try:
            auto_trader = AutoTrader(trader_config, self.settings)
            # 修复：确保 key 是字符串
            trader_id_str = str(trader_id) if trader_id else None
            if not trader_id_str:
                logger.error(f"❌ 交易员 ID 无效")
                return False
            self.traders[trader_id_str] = auto_trader  # 使用字符串作为 key
            logger.info(f"✓ 交易员 {trader_id_str} 已加载")
            return True
        except Exception as e:
            logger.error(f"❌ 创建 trader 实例失败: {e}", exc_info=True)
            return False

    
    def _parse_trading_coins(self, trading_symbols: str, custom_coins: str) -> List[str]:
        """解析交易币种列表（从字符串）"""
        trading_coins = []
        
        # 优先使用 trading_symbols（逗号分隔）
        if trading_symbols:
            symbols = [s.strip() for s in trading_symbols.split(",")]
            trading_coins = [s for s in symbols if s]
        
        # 如果没有，尝试使用 custom_coins（JSON格式）
        if not trading_coins and custom_coins:
            try:
                trading_coins = json.loads(custom_coins)
            except json.JSONDecodeError:
                logger.warning(f"⚠️ 解析自定义币种失败")
        
        return trading_coins

    

    def start_trader(self, trader_id: str) -> bool:
        """启动指定交易员"""
        with self._lock:
            if trader_id not in self.traders:
                logger.error(f"❌ 交易员 {trader_id} 不存在")
                return False
            
            trader = self.traders[trader_id]
            try:
                trader.start()
                # 更新数据库状态
                self._update_trader_running_status(trader_id, True)
                logger.info(f"✓ 交易员 {trader_id} 已启动")
                return True
            except Exception as e:
                logger.error(f"❌ 启动交易员 {trader_id} 失败: {e}", exc_info=True)
                return False
    
    def stop_trader(self, trader_id: str) -> bool:
        """停止指定交易员"""
        with self._lock:
            if trader_id not in self.traders:
                logger.error(f"❌ 交易员 {trader_id} 不存在")
                return False
            
            trader = self.traders[trader_id]
            try:
                trader.stop()
                # 更新数据库状态
                self._update_trader_running_status(trader_id, False)
                logger.info(f"✓ 交易员 {trader_id} 已停止")
                return True
            except Exception as e:
                logger.error(f"❌ 停止交易员 {trader_id} 失败: {e}", exc_info=True)
                return False
    
    def start_all_traders(self) -> int:
        """启动所有交易员"""
        with self._lock:
            success_count = 0
            for trader_id in list(self.traders.keys()):
                if self.start_trader(trader_id):
                    success_count += 1
            return success_count
    
    def stop_all_traders(self) -> int:
        """停止所有交易员"""
        with self._lock:
            success_count = 0
            for trader_id in list(self.traders.keys()):
                if self.stop_trader(trader_id):
                    success_count += 1
            return success_count
    
    def get_trader(self, trader_id: str):
        """获取指定交易员实例"""
        with self._lock:
            return self.traders.get(trader_id)
    
    def get_all_traders(self):
        """获取所有交易员实例（返回副本）"""
        with self._lock:
            return self.traders.copy()
    
    def reload_trader(self, trader_id: str):
        """重新加载指定交易员（从数据库）"""
        with self._lock:
            # 先停止并移除
            if trader_id in self.traders:
                self.stop_trader(trader_id)
                del self.traders[trader_id]
            
            # 从数据库重新加载
            with self.settings.get_session() as session:
                trader_cfg = session.exec(
                    select(Trader).where(Trader.id == trader_id)
                ).first()
                
                if not trader_cfg:
                    logger.error(f"❌ 交易员 {trader_id} 在数据库中不存在")
                    return False
                
                system_config = self._get_system_config()
                return self._load_single_trader(trader_cfg, system_config)
    
    def _update_trader_running_status(self, trader_id: str, is_running: bool):
        """更新数据库中的交易员运行状态"""
        try:
            with self.settings.get_session() as session:
                trader = session.exec(
                    select(Trader).where(Trader.id == trader_id)
                ).first()
                if trader:
                    trader.is_running = is_running
                    session.add(trader)
                    session.commit()
        except Exception as e:
            logger.error(f"❌ 更新交易员 {trader_id} 运行状态失败: {e}", exc_info=True)
    
    def get_trader_status(self, trader_id: str):
        """获取交易员状态信息"""
        with self._lock:
            if trader_id not in self.traders:
                return None
            
            trader = self.traders[trader_id]
            # 这里需要 AutoTrader 实现 get_status() 方法
            try:
                return trader.get_status()
            except AttributeError:
                return {
                    'id': trader_id,
                    'running': hasattr(trader, 'is_running') and trader.is_running,
                }