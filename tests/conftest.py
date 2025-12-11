"""
Pytest 配置和共享 fixtures
"""
import pytest
import os
from unittest.mock import MagicMock, Mock
from config.settings import Settings
from sqlmodel import SQLModel, Session, create_engine, text
from dotenv import load_dotenv

load_dotenv()


@pytest.fixture(scope="session")
def settings():
    """创建 Settings 实例（整个测试会话共享）"""
    return Settings()


@pytest.fixture(scope="function")
def db_session(settings):
    """为每个测试函数提供数据库会话"""
    with settings.get_session() as session:
        yield session


@pytest.fixture(scope="function", autouse=True)
def cleanup_test_data(db_session):
    """每个测试后自动清理测试数据"""
    yield
    # 测试后的清理逻辑（如果需要）
    pass


# ========== Trader测试相关fixtures ==========

@pytest.fixture
def cex_exchange_config():
    """CEX交易所配置fixture（从环境变量读取）"""
    # 支持多个CEX交易所
    exchange_configs = {}
    
    # Binance配置
    binance_api_key = os.getenv('BINANCE_API_KEY', '')
    binance_secret = os.getenv('BINANCE_SECRET_KEY', '')
    if binance_api_key and binance_secret:
        exchange_configs['binance'] = {
            'name': 'binance',
            'api_key': binance_api_key,
            'secret_key': binance_secret,
            'testnet': os.getenv('BINANCE_TESTNET', 'false').lower() == 'true',
            'is_cross_margin': True,
        }
    
    # OKX配置
    okx_api_key = os.getenv('OKX_API_KEY', '')
    okx_secret = os.getenv('OKX_SECRET_KEY', '')
    if okx_api_key and okx_secret:
        exchange_configs['okx'] = {
            'name': 'okx',
            'api_key': okx_api_key,
            'secret_key': okx_secret,
            'testnet': os.getenv('OKX_TESTNET', 'false').lower() == 'true',
            'is_cross_margin': True,
        }
    
    # Gate.io配置
    gate_api_key = os.getenv('GATE_API_KEY', '')
    gate_secret = os.getenv('GATE_SECRET_KEY', '')
    if gate_api_key and gate_secret:
        exchange_configs['gate'] = {
            'name': 'gate.io',
            'api_key': gate_api_key,
            'secret_key': gate_secret,
            'testnet': os.getenv('GATE_TESTNET', 'false').lower() == 'true',
            'is_cross_margin': True,
        }
    
    return exchange_configs


@pytest.fixture
def dex_exchange_config():
    """DEX交易所配置fixture（从环境变量读取）"""
    wallet_address = os.getenv('HYPERLIQUID_WALLET_ADDRESS', '')
    secret_key = os.getenv('HYPERLIQUID_SECRET_KEY', '')
    
    if not wallet_address or not secret_key:
        return None
    
    return {
        'wallet_address': wallet_address,
        'secret_key': secret_key,
        'testnet': os.getenv('HYPERLIQUID_TESTNET', 'false').lower() == 'true',
        'is_cross_margin': True,
        'slippage': 0.01
    }


@pytest.fixture
def mock_ccxt_exchange():
    """Mock CCXT exchange fixture用于测试基类"""
    mock_exchange = MagicMock()
    
    # Mock markets数据
    mock_exchange.markets = {
        'BTC/USDT': {
            'symbol': 'BTC/USDT',
            'precision': {'amount': 8, 'price': 2},
            'limits': {
                'amount': {'min': 0.0001, 'max': 1000},
                'price': {'min': 0.01, 'max': 1000000}
            }
        }
    }
    
    # Mock fetch_balance
    mock_exchange.fetch_balance.return_value = {
        'total': {'USDT': 1000.0},
        'free': {'USDT': 1000.0},
        'used': {'USDT': 0.0}
    }
    
    # Mock fetch_ticker
    mock_exchange.fetch_ticker.return_value = {
        'symbol': 'BTC/USDT',
        'last': 50000.0,
        'close': 50000.0
    }
    
    # Mock fetch_positions
    mock_exchange.fetch_positions.return_value = []
    
    # Mock create_order
    mock_exchange.create_order.return_value = {
        'id': 'test_order_123',
        'orderId': 'test_order_123',
        'symbol': 'BTC/USDT',
        'status': 'closed'
    }
    
    # Mock fetch_open_orders
    mock_exchange.fetch_open_orders.return_value = []
    
    # Mock set_leverage
    mock_exchange.set_leverage.return_value = True
    
    # Mock load_markets
    mock_exchange.load_markets.return_value = mock_exchange.markets
    
    return mock_exchange

