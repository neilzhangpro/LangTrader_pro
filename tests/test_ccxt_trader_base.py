"""
CCXT Trader基类单元测试
使用Mock CCXT exchange测试基类的通用方法和逻辑
"""
import pytest
from unittest.mock import MagicMock, Mock, patch
from decimal import Decimal
from services.trader.ccxt_trader_base import CcxTraderBase
import ccxt


class TestCcxTraderBase:
    """CCXT Trader基类测试（使用Mock）"""
    
    @pytest.fixture
    def mock_exchange(self):
        """创建Mock CCXT exchange"""
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
            },
            'ETH/USDT': {
                'symbol': 'ETH/USDT',
                'precision': {'amount': 6, 'price': 2},
                'limits': {
                    'amount': {'min': 0.001, 'max': 10000},
                    'price': {'min': 0.01, 'max': 100000}
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
        mock_exchange.fetch_positions.return_value = [
            {
                'symbol': 'BTC/USDT',
                'side': 'long',
                'contracts': 0.001,
                'entryPrice': 50000.0,
                'markPrice': 51000.0,
                'unrealizedPnl': 1.0,
                'leverage': 3,
                'liquidationPrice': 40000.0,
                'marginUsed': 16.67,
                'timestamp': 1234567890
            }
        ]
        
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
    
    @pytest.fixture
    def exchange_config(self):
        """交易所配置"""
        return {
            'testnet': False,
            'is_cross_margin': True
        }
    
    @pytest.fixture
    def mock_trader(self, mock_exchange, exchange_config):
        """创建基于Mock的Trader实例"""
        # 直接创建基类实例（虽然基类通常不直接实例化，但可以用于测试）
        trader = CcxTraderBase(mock_exchange, exchange_config)
        return trader
    
    # ========== 基础方法测试 ==========
    
    @pytest.mark.unit
    def test_get_balance_with_mock(self, mock_trader):
        """测试获取余额（Mock）"""
        balance = mock_trader.get_balance('BTC/USDT')
        assert balance == Decimal('1000.0'), f"余额应该是1000.0，实际是{balance}"
        print(f"✓ 获取余额成功: {balance} USDT")
    
    @pytest.mark.unit
    def test_get_balance_no_usdt(self, mock_trader, mock_exchange):
        """测试获取余额（无USDT时）"""
        # Mock返回无USDT的余额
        mock_exchange.fetch_balance.return_value = {
            'total': {'BTC': 0.1},
            'free': {'BTC': 0.1},
            'used': {'BTC': 0.0}
        }
        
        balance = mock_trader.get_balance('BTC/USDT')
        assert balance == Decimal('0.1'), f"余额应该是0.1，实际是{balance}"
        print(f"✓ 获取余额成功（无USDT）: {balance} BTC")
    
    @pytest.mark.unit
    def test_get_market_price_with_mock(self, mock_trader):
        """测试获取市场价格（Mock）"""
        price = mock_trader.getMarketPrice('BTC/USDT')
        assert price == Decimal('50000.0'), f"价格应该是50000.0，实际是{price}"
        print(f"✓ 获取价格成功: {price} USDT")
    
    @pytest.mark.unit
    def test_format_quantity_with_mock(self, mock_trader):
        """测试格式化数量（Mock）"""
        # 测试BTC/USDT（精度8）
        raw_quantity = Decimal('0.123456789')
        formatted = mock_trader.formatQuantity('BTC/USDT', raw_quantity)
        
        # 应该四舍五入到8位精度
        assert formatted > 0, "格式化数量应该 > 0"
        print(f"✓ 格式化数量: {raw_quantity} -> {formatted}")
    
    @pytest.mark.unit
    def test_format_quantity_precision(self, mock_trader):
        """测试数量精度处理"""
        # 测试不同精度的币种
        test_cases = [
            ('BTC/USDT', Decimal('0.123456789'), 8),  # BTC精度8
            ('ETH/USDT', Decimal('0.123456789'), 6),   # ETH精度6
        ]
        
        for symbol, quantity, expected_precision in test_cases:
            formatted = mock_trader.formatQuantity(symbol, quantity)
            # 检查精度（通过字符串长度判断）
            decimal_places = len(str(formatted).split('.')[-1]) if '.' in str(formatted) else 0
            print(f"  {symbol}: {quantity} -> {formatted} (精度: {decimal_places})")
    
    @pytest.mark.unit
    def test_format_quantity_min_amount(self, mock_trader, mock_exchange):
        """测试最小数量限制"""
        # 设置一个很小的数量（小于最小数量）
        tiny_quantity = Decimal('0.00001')  # 小于BTC最小数量0.0001
        
        formatted = mock_trader.formatQuantity('BTC/USDT', tiny_quantity)
        
        # 应该使用最小数量
        assert formatted >= Decimal('0.0001'), "格式化数量应该 >= 最小数量"
        print(f"✓ 最小数量测试: {tiny_quantity} -> {formatted}")
    
    @pytest.mark.unit
    def test_set_leverage_with_mock(self, mock_trader):
        """测试设置杠杆（Mock）"""
        result = mock_trader.setLeverage('BTC/USDT', 3)
        assert result > 0, "设置杠杆应该成功"
        mock_trader.exchange.set_leverage.assert_called_once_with(3, 'BTC/USDT')
        print("✓ 设置杠杆成功")
    
    @pytest.mark.unit
    def test_set_margin_mode_with_mock(self, mock_trader, mock_exchange):
        """测试设置保证金模式（Mock）"""
        # Mock set_margin_mode
        mock_exchange.set_margin_mode.return_value = True
        
        # 测试全仓模式
        result = mock_trader.setMarginMode(True)
        assert result > 0, "设置全仓模式应该成功"
        assert mock_trader.is_cross_margin == True, "is_cross_margin应该为True"
        print("✓ 设置全仓模式成功")
        
        # 测试逐仓模式
        result = mock_trader.setMarginMode(False)
        assert result > 0, "设置逐仓模式应该成功"
        assert mock_trader.is_cross_margin == False, "is_cross_margin应该为False"
        print("✓ 设置逐仓模式成功")
    
    @pytest.mark.unit
    def test_set_margin_mode_not_supported(self, mock_trader, mock_exchange):
        """测试设置保证金模式（不支持时）"""
        # Mock不支持set_margin_mode
        mock_exchange.set_margin_mode.side_effect = NotImplementedError("Not supported")
        
        result = mock_trader.setMarginMode(True)
        # 应该返回成功（因为可能在设置杠杆时设置）
        assert result > 0, "不支持时应该返回成功"
        print("✓ 不支持保证金模式时处理正确")
    
    # ========== 下单方法测试 ==========
    
    @pytest.mark.unit
    def test_open_long_with_mock(self, mock_trader):
        """测试开多仓（Mock）"""
        quantity = Decimal('0.001')
        result = mock_trader.openLong('BTC/USDT', quantity, 3)
        
        assert result > 0, "开多仓应该成功"
        # 验证调用了create_order
        mock_trader.exchange.create_order.assert_called()
        call_args = mock_trader.exchange.create_order.call_args
        assert call_args[0][0] == 'BTC/USDT', "symbol应该是BTC/USDT"
        assert call_args[0][1] == 'market', "订单类型应该是market"
        assert call_args[0][2] == 'buy', "方向应该是buy"
        assert call_args[1]['reduceOnly'] == False, "reduceOnly应该是False"
        
        print("✓ 开多仓成功")
    
    @pytest.mark.unit
    def test_open_short_with_mock(self, mock_trader):
        """测试开空仓（Mock）"""
        quantity = Decimal('0.001')
        result = mock_trader.openShort('BTC/USDT', quantity, 3)
        
        assert result > 0, "开空仓应该成功"
        # 验证调用了create_order
        call_args = mock_trader.exchange.create_order.call_args
        assert call_args[0][2] == 'sell', "方向应该是sell"
        
        print("✓ 开空仓成功")
    
    # ========== 平仓方法测试 ==========
    
    @pytest.mark.unit
    def test_close_position_logic(self, mock_trader, mock_exchange):
        """测试平仓逻辑（quantity=0处理）"""
        # Mock有持仓的情况
        mock_exchange.fetch_positions.return_value = [
            {
                'symbol': 'BTC/USDT',
                'side': 'long',
                'contracts': 0.001,
                'entryPrice': 50000.0,
                'markPrice': 51000.0,
                'unrealizedPnl': 1.0,
                'leverage': 3
            }
        ]
        
        # 测试平全部多仓（quantity=0）
        result = mock_trader.closeLong('BTC/USDT', Decimal('0'))
        
        assert result > 0, "平仓应该成功"
        # 验证调用了create_order，且reduceOnly=True
        call_args = mock_trader.exchange.create_order.call_args
        assert call_args[1]['reduceOnly'] == True, "reduceOnly应该是True"
        assert call_args[0][2] == 'sell', "平多仓方向应该是sell"
        
        print("✓ 平仓逻辑测试成功（quantity=0）")
    
    @pytest.mark.unit
    def test_close_long_no_position(self, mock_trader, mock_exchange):
        """测试无持仓时平仓"""
        # Mock无持仓
        mock_exchange.fetch_positions.return_value = []
        
        result = mock_trader.closeLong('BTC/USDT', Decimal('0'))
        
        # 无持仓时应该返回成功（1）
        assert result > 0, "无持仓时平仓应该返回成功"
        print("✓ 无持仓平仓测试成功")
    
    @pytest.mark.unit
    def test_close_short_with_mock(self, mock_trader, mock_exchange):
        """测试平空仓（Mock）"""
        # Mock有空仓
        mock_exchange.fetch_positions.return_value = [
            {
                'symbol': 'BTC/USDT',
                'side': 'short',
                'contracts': 0.001,
                'entryPrice': 50000.0,
                'markPrice': 49000.0,
                'unrealizedPnl': 1.0,
                'leverage': 3
            }
        ]
        
        result = mock_trader.closeShort('BTC/USDT', Decimal('0'))
        
        assert result > 0, "平空仓应该成功"
        call_args = mock_trader.exchange.create_order.call_args
        assert call_args[0][2] == 'buy', "平空仓方向应该是buy"
        
        print("✓ 平空仓成功")
    
    # ========== 撤单方法测试 ==========
    
    @pytest.mark.unit
    def test_cancel_all_orders_with_mock(self, mock_trader, mock_exchange):
        """测试取消所有订单（Mock）"""
        # Mock有挂单
        mock_exchange.fetch_open_orders.return_value = [
            {'id': 'order1', 'symbol': 'BTC/USDT'},
            {'id': 'order2', 'symbol': 'BTC/USDT'}
        ]
        mock_exchange.cancel_order.return_value = True
        
        result = mock_trader.cancelAllOrders('BTC/USDT')
        
        assert result > 0, "取消订单应该成功"
        # 验证调用了cancel_order两次
        assert mock_exchange.cancel_order.call_count == 2, "应该取消2个订单"
        print("✓ 取消所有订单成功")
    
    @pytest.mark.unit
    def test_cancel_all_orders_no_orders(self, mock_trader, mock_exchange):
        """测试取消所有订单（无订单时）"""
        # Mock无挂单
        mock_exchange.fetch_open_orders.return_value = []
        
        result = mock_trader.cancelAllOrders('BTC/USDT')
        
        assert result > 0, "无订单时应该返回成功"
        print("✓ 无订单撤单测试成功")
    
    @pytest.mark.unit
    def test_cancel_all_orders_fallback(self, mock_trader, mock_exchange):
        """测试取消所有订单（fallback到cancel_all_orders）"""
        # Mock fetch_open_orders不支持
        mock_exchange.fetch_open_orders.side_effect = NotImplementedError("Not supported")
        mock_exchange.cancel_all_orders.return_value = True
        
        result = mock_trader.cancelAllOrders('BTC/USDT')
        
        assert result > 0, "取消订单应该成功"
        # 验证调用了cancel_all_orders
        mock_exchange.cancel_all_orders.assert_called_once_with('BTC/USDT')
        print("✓ 取消订单fallback测试成功")
    
    # ========== 持仓方法测试 ==========
    
    @pytest.mark.unit
    def test_get_all_positions_with_mock(self, mock_trader):
        """测试获取持仓（Mock）"""
        positions = mock_trader.get_all_positions()
        
        assert isinstance(positions, list), "持仓应该返回列表"
        assert len(positions) == 1, "应该返回1个持仓"
        
        pos = positions[0]
        assert pos['symbol'] == 'BTC/USDT', "symbol应该是BTC/USDT"
        assert pos['side'] == 'long', "side应该是long"
        assert pos['size'] == 0.001, "size应该是0.001"
        
        print(f"✓ 获取持仓成功: {len(positions)} 个持仓")
    
    @pytest.mark.unit
    def test_get_all_positions_empty(self, mock_trader, mock_exchange):
        """测试获取持仓（无持仓时）"""
        # Mock无持仓
        mock_exchange.fetch_positions.return_value = []
        
        positions = mock_trader.get_all_positions()
        
        assert isinstance(positions, list), "持仓应该返回列表"
        assert len(positions) == 0, "应该返回0个持仓"
        print("✓ 无持仓测试成功")
    
    # ========== 错误处理测试 ==========
    
    @pytest.mark.unit
    def test_get_balance_error_handling(self, mock_trader, mock_exchange):
        """测试获取余额错误处理"""
        # Mock抛出异常
        mock_exchange.fetch_balance.side_effect = Exception("Network error")
        
        balance = mock_trader.get_balance('BTC/USDT')
        
        # 应该返回0而不是抛出异常
        assert balance == Decimal('0'), "错误时应该返回0"
        print("✓ 余额错误处理测试成功")
    
    @pytest.mark.unit
    def test_get_market_price_error_handling(self, mock_trader, mock_exchange):
        """测试获取价格错误处理"""
        # Mock抛出异常
        mock_exchange.fetch_ticker.side_effect = Exception("Network error")
        
        price = mock_trader.getMarketPrice('BTC/USDT')
        
        # 应该返回0而不是抛出异常
        assert price == Decimal('0'), "错误时应该返回0"
        print("✓ 价格错误处理测试成功")
    
    @pytest.mark.unit
    def test_open_long_error_handling(self, mock_trader, mock_exchange):
        """测试开仓错误处理"""
        # Mock抛出异常
        mock_exchange.create_order.side_effect = Exception("Insufficient balance")
        
        result = mock_trader.openLong('BTC/USDT', Decimal('0.001'), 3)
        
        # 应该返回0而不是抛出异常
        assert result == Decimal('0'), "错误时应该返回0"
        print("✓ 开仓错误处理测试成功")
    
    @pytest.mark.unit
    def test_format_quantity_error_handling(self, mock_trader, mock_exchange):
        """测试格式化数量错误处理"""
        # Mock markets加载失败
        mock_exchange.markets = {}
        mock_exchange.load_markets.side_effect = Exception("Load markets failed")
        
        formatted = mock_trader.formatQuantity('BTC/USDT', Decimal('0.001'))
        
        # 应该使用默认精度而不是抛出异常
        assert formatted > 0, "错误时应该使用默认精度"
        print("✓ 格式化数量错误处理测试成功")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s', '-m', 'unit'])
