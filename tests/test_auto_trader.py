"""
AutoTrader 单元测试
测试核心流程：启动、停止、扫描循环
"""
import pytest
import time
import threading
from services.Auto_trader import AutoTrader
from config.settings import Settings
from decimal import Decimal


class TestAutoTrader:
    """AutoTrader 核心功能测试"""
    
    @pytest.fixture
    def trader_config(self):
        """创建测试用的交易员配置"""
        return {
            'id': 'test-trader-id',
            'name': 'Test Trader',
            'user_id': 'test-user-id',
            'scan_interval_minutes': 1,  # 测试用1分钟
            'initial_balance': 10000.0,
            'ai_model': {
                'provider': 'openai',
                'api_key': 'test-key'
            },
            'exchange': {
                'name': 'test-exchange',
                'type': 'cex'
            }
        }
    
    def test_initialization(self, settings, trader_config):
        """测试 AutoTrader 初始化"""
        trader = AutoTrader(trader_config, settings)
        
        assert trader.trader_id == 'test-trader-id'
        assert trader.trader_name == 'Test Trader'
        assert trader.is_running is False
        assert trader._scan_thread is None
    
    def test_start_trader(self, settings, trader_config):
        """测试启动交易员"""
        trader = AutoTrader(trader_config, settings)
        
        trader.start()
        
        assert trader.is_running is True
        assert trader._scan_thread is not None
        assert trader._scan_thread.is_alive()
        
        # 清理
        trader.stop()
    
    def test_stop_trader(self, settings, trader_config):
        """测试停止交易员"""
        trader = AutoTrader(trader_config, settings)
        
        trader.start()
        assert trader.is_running is True
        
        trader.stop()
        
        assert trader.is_running is False
        assert trader._scan_thread is None
    
    def test_start_already_running(self, settings, trader_config):
        """测试重复启动（应该被忽略）"""
        trader = AutoTrader(trader_config, settings)
        
        trader.start()
        initial_thread = trader._scan_thread
        
        # 再次启动应该被忽略
        trader.start()
        
        # 线程应该还是原来的
        assert trader._scan_thread == initial_thread
        
        trader.stop()
    
    def test_stop_not_running(self, settings, trader_config):
        """测试停止未运行的交易员（应该被忽略）"""
        trader = AutoTrader(trader_config, settings)
        
        # 未启动就停止，应该不会报错
        trader.stop()
        
        assert trader.is_running is False
    
    def test_scan_loop_execution(self, settings, trader_config):
        """测试扫描循环执行"""
        trader = AutoTrader(trader_config, settings)
        
        # 设置很短的扫描间隔用于测试
        trader.trader_cfg['scan_interval_minutes'] = 0.01  # 0.6秒
        
        trader.start()
        
        # 等待一小段时间，确保扫描循环至少执行一次
        time.sleep(1)
        
        # 验证交易员仍在运行
        assert trader.is_running is True
        
        trader.stop()
    
    def test_get_status(self, settings, trader_config):
        """测试获取状态"""
        trader = AutoTrader(trader_config, settings)
        
        status = trader.get_status()
        
        assert status['id'] == 'test-trader-id'
        assert status['name'] == 'Test Trader'
        assert status['is_running'] is False
        assert status['scan_interval_minutes'] == 1
    
    def test_get_status_while_running(self, settings, trader_config):
        """测试运行中获取状态"""
        trader = AutoTrader(trader_config, settings)
        
        trader.start()
        status = trader.get_status()
        
        assert status['is_running'] is True
        
        trader.stop()




