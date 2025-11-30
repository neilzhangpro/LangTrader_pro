"""
TraderManager 单元测试
测试核心流程：加载、启动、停止交易员
"""
import pytest
from services.trader_manager import TraderManager
from models.user import User
from models.trader import Trader
from models.ai_model import AIModel
from models.exchange import Exchange
from models.prompt_template import PromptTemplate
from models.signal_source import UserSignalSource
from decimal import Decimal


class TestTraderManager:
    """TraderManager 核心功能测试"""
    
    def test_initialization(self, settings):
        """测试 TraderManager 初始化"""
        manager = TraderManager(settings)
        
        assert manager.settings == settings
        assert manager.prompt_service is not None
        assert len(manager.traders) == 0
    
    def test_get_system_config(self, settings):
        """测试获取系统配置"""
        manager = TraderManager(settings)
        
        config = manager._get_system_config()
        
        assert 'max_daily_loss' in config
        assert 'max_drawdown' in config
        assert 'stop_trading_minutes' in config
        assert 'default_coins' in config
        assert isinstance(config['max_daily_loss'], float)
        assert isinstance(config['max_drawdown'], float)
        assert isinstance(config['stop_trading_minutes'], int)
    
    def test_parse_trading_coins_from_string(self, settings):
        """测试解析交易币种列表（字符串格式）"""
        manager = TraderManager(settings)
        
        # 测试逗号分隔的字符串
        result = manager._parse_trading_coins("BTC/USDT,ETH/USDT,SOL/USDT", "")
        assert result == ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
        
        # 测试空字符串
        result = manager._parse_trading_coins("", "")
        assert result == []
        
        # 测试带空格的字符串
        result = manager._parse_trading_coins("BTC/USDT, ETH/USDT , SOL/USDT", "")
        assert result == ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
    
    def test_parse_trading_coins_from_json(self, settings):
        """测试解析交易币种列表（JSON格式）"""
        manager = TraderManager(settings)
        
        # 测试 JSON 格式
        json_coins = '["BTC/USDT", "ETH/USDT"]'
        result = manager._parse_trading_coins("", json_coins)
        assert result == ["BTC/USDT", "ETH/USDT"]
    
    def test_load_traders_from_database(self, settings, db_session):
        """测试从数据库加载交易员（核心流程）"""
        manager = TraderManager(settings)
        
        # 创建测试数据
        user = User(
            email="test_manager@example.com",
            password_hash="test_hash"
        )
        db_session.add(user)
        db_session.flush()
        
        # 创建 AI 模型
        ai_model = AIModel(
            user_id=str(user.id),
            name="test_model",
            provider="openai",
            enabled=True,
            api_key="test-key"
        )
        db_session.add(ai_model)
        db_session.flush()
        
        # 创建交易所
        exchange = Exchange(
            user_id=str(user.id),
            name="test_exchange",
            type="cex",
            enabled=True
        )
        db_session.add(exchange)
        db_session.flush()
        
        # 创建提示词模板
        template = PromptTemplate(
            name="default",
            content="测试提示词内容",
            description="测试模板"
        )
        db_session.add(template)
        db_session.flush()
        
        # 创建交易员
        trader = Trader(
            user_id=str(user.id),
            name="Test Trader Manager",
            ai_model_id=str(ai_model.id),
            exchange_id=str(exchange.id),
            initial_balance=Decimal("10000"),
            scan_interval_minutes=3
        )
        db_session.add(trader)
        db_session.commit()
        
        # 测试加载
        success_count = manager.load_traders_from_database()
        
        # 应该至少加载了我们创建的测试交易员
        assert success_count >= 1
        assert len(manager.traders) >= 1
    
    def test_start_and_stop_trader(self, settings, db_session):
        """测试启动和停止交易员"""
        manager = TraderManager(settings)
        
        # 先加载交易员
        manager.load_traders_from_database()
        
        if len(manager.traders) == 0:
            pytest.skip("没有可用的交易员进行测试")
        
        # 获取第一个交易员
        trader_id = list(manager.traders.keys())[0]
        
        # 测试启动
        result = manager.start_trader(trader_id)
        assert result is True
        
        # 验证交易员正在运行
        trader = manager.get_trader(trader_id)
        assert trader is not None
        assert trader.is_running is True
        
        # 测试停止
        result = manager.stop_trader(trader_id)
        assert result is True
        
        # 验证交易员已停止
        trader = manager.get_trader(trader_id)
        assert trader.is_running is False
    
    def test_start_nonexistent_trader(self, settings):
        """测试启动不存在的交易员"""
        manager = TraderManager(settings)
        
        result = manager.start_trader("non_existent_trader_id")
        assert result is False
    
    def test_stop_nonexistent_trader(self, settings):
        """测试停止不存在的交易员"""
        manager = TraderManager(settings)
        
        result = manager.stop_trader("non_existent_trader_id")
        assert result is False
    
    def test_get_trader(self, settings):
        """测试获取交易员实例"""
        manager = TraderManager(settings)
        
        # 加载交易员
        manager.load_traders_from_database()
        
        if len(manager.traders) == 0:
            pytest.skip("没有可用的交易员进行测试")
        
        trader_id = list(manager.traders.keys())[0]
        trader = manager.get_trader(trader_id)
        
        assert trader is not None
        assert str(trader.trader_id) == trader_id
    
    def test_get_all_traders(self, settings):
        """测试获取所有交易员"""
        manager = TraderManager(settings)
        
        # 加载交易员
        manager.load_traders_from_database()
        
        all_traders = manager.get_all_traders()
        
        assert isinstance(all_traders, dict)
        assert len(all_traders) == len(manager.traders)
    
    def test_get_trader_status(self, settings):
        """测试获取交易员状态"""
        manager = TraderManager(settings)
        
        # 加载交易员
        manager.load_traders_from_database()
        
        if len(manager.traders) == 0:
            pytest.skip("没有可用的交易员进行测试")
        
        trader_id = list(manager.traders.keys())[0]
        status = manager.get_trader_status(trader_id)
        
        assert status is not None
        assert 'id' in status
        assert 'name' in status
        assert 'is_running' in status
    
    def test_get_trader_status_nonexistent(self, settings):
        """测试获取不存在的交易员状态"""
        manager = TraderManager(settings)
        
        status = manager.get_trader_status("non_existent_trader_id")
        assert status is None

