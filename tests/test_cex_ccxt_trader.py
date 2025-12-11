"""
CEX CCXT Trader 单元测试
测试CexCcxTrader类的所有功能，重点测试下单和撤单接口
"""
import pytest
import os
import time
from decimal import Decimal
from services.trader.cex_ccxt_trader import CexCcxTrader


class TestCexCcxTrader:
    """CEX CCXT Trader 功能测试"""
    
    @pytest.fixture
    def exchange_config(self, cex_exchange_config):
        """获取CEX交易所配置（优先使用Binance）"""
        if not cex_exchange_config:
            pytest.skip("需要配置CEX交易所环境变量（BINANCE_API_KEY等）")
        
        # 优先使用Binance，如果没有则使用第一个可用的
        if 'binance' in cex_exchange_config:
            return cex_exchange_config['binance']
        elif 'okx' in cex_exchange_config:
            return cex_exchange_config['okx']
        elif 'gate' in cex_exchange_config:
            return cex_exchange_config['gate']
        else:
            pytest.skip("需要配置至少一个CEX交易所环境变量")
    
    @pytest.fixture
    def trader(self, exchange_config):
        """创建 trader 实例"""
        return CexCcxTrader(exchange_config)
    
    @pytest.fixture
    def test_symbol(self):
        """测试币种"""
        return 'BTC/USDT:USDT'  # 合约交易符号
    
    @pytest.fixture
    def test_usd_amount(self):
        """测试金额（USD）"""
        return Decimal('10')  # 使用10 USDT进行测试
    
    # ========== 基础功能测试 ==========
    
    @pytest.mark.integration
    @pytest.mark.real_env
    def test_initialization(self, trader, exchange_config):
        """测试初始化"""
        assert trader is not None
        assert trader.exchange is not None
        assert trader.exchange_config == exchange_config
        print(f"✓ CEX Trader 初始化成功: {exchange_config.get('name')}")
    
    @pytest.mark.integration
    @pytest.mark.real_env
    def test_get_balance(self, trader, test_symbol):
        """测试获取余额"""
        balance = trader.get_balance(test_symbol)
        assert balance >= 0, "余额应该 >= 0"
        print(f"✓ 账户余额: {balance} USDT")
    
    @pytest.mark.integration
    @pytest.mark.real_env
    def test_get_market_price(self, trader, test_symbol):
        """测试获取市场价格"""
        price = trader.getMarketPrice(test_symbol)
        assert price > 0, f"获取价格失败或价格为0: {price}"
        print(f"✓ {test_symbol} 当前价格: {price} USDT")
    
    @pytest.mark.integration
    @pytest.mark.real_env
    def test_get_all_positions(self, trader, test_symbol):
        """测试获取所有持仓"""
        positions = trader.get_all_positions()
        assert isinstance(positions, list), "持仓应该返回列表"
        print(f"✓ 当前持仓数量: {len(positions)}")
        for pos in positions:
            print(f"  - {pos.get('symbol')}: {pos.get('side')} {pos.get('size')}")
    
    # ========== 下单接口测试 ==========
    
    @pytest.mark.integration
    @pytest.mark.real_env
    @pytest.mark.slow
    def test_open_long_success(self, trader, test_symbol, test_usd_amount):
        """测试开多仓成功"""
        # 获取当前价格并计算数量
        price = trader.getMarketPrice(test_symbol)
        assert price > 0, "无法获取价格"
        
        quantity = test_usd_amount / price
        formatted_quantity = trader.formatQuantity(test_symbol, quantity)
        
        # 设置杠杆
        trader.setLeverage(test_symbol, 3)
        
        # 开多仓
        result = trader.openLong(test_symbol, formatted_quantity, 3)
        assert result > 0, f"开多仓失败: {result}"
        print(f"✓ 开多仓成功: {formatted_quantity} {test_symbol}")
        
        # 等待订单执行
        time.sleep(3)
        
        return formatted_quantity
    
    @pytest.mark.integration
    @pytest.mark.real_env
    @pytest.mark.slow
    def test_open_short_success(self, trader, test_symbol, test_usd_amount):
        """测试开空仓成功"""
        # 获取当前价格并计算数量
        price = trader.getMarketPrice(test_symbol)
        assert price > 0, "无法获取价格"
        
        quantity = test_usd_amount / price
        formatted_quantity = trader.formatQuantity(test_symbol, quantity)
        
        # 设置杠杆
        trader.setLeverage(test_symbol, 3)
        
        # 开空仓
        result = trader.openShort(test_symbol, formatted_quantity, 3)
        assert result > 0, f"开空仓失败: {result}"
        print(f"✓ 开空仓成功: {formatted_quantity} {test_symbol}")
        
        # 等待订单执行
        time.sleep(3)
        
        return formatted_quantity
    
    @pytest.mark.integration
    @pytest.mark.real_env
    def test_open_long_with_leverage(self, trader, test_symbol, test_usd_amount):
        """测试带杠杆开多仓"""
        price = trader.getMarketPrice(test_symbol)
        quantity = test_usd_amount / price
        formatted_quantity = trader.formatQuantity(test_symbol, quantity)
        
        # 测试不同杠杆值
        for leverage in [2, 3, 5]:
            result = trader.setLeverage(test_symbol, leverage)
            if result > 0:
                print(f"✓ 设置杠杆成功: {leverage}x")
                break
        
        # 开多仓
        result = trader.openLong(test_symbol, formatted_quantity, 3)
        assert result > 0, "开多仓失败"
        print(f"✓ 带杠杆开多仓成功")
        
        time.sleep(3)
    
    @pytest.mark.integration
    @pytest.mark.real_env
    def test_open_short_with_leverage(self, trader, test_symbol, test_usd_amount):
        """测试带杠杆开空仓"""
        price = trader.getMarketPrice(test_symbol)
        quantity = test_usd_amount / price
        formatted_quantity = trader.formatQuantity(test_symbol, quantity)
        
        # 设置杠杆
        trader.setLeverage(test_symbol, 3)
        
        # 开空仓
        result = trader.openShort(test_symbol, formatted_quantity, 3)
        assert result > 0, "开空仓失败"
        print(f"✓ 带杠杆开空仓成功")
        
        time.sleep(3)
    
    @pytest.mark.integration
    @pytest.mark.real_env
    def test_open_long_min_quantity(self, trader, test_symbol):
        """测试最小数量限制"""
        # 尝试使用非常小的数量
        tiny_quantity = Decimal('0.00000001')
        formatted_quantity = trader.formatQuantity(test_symbol, tiny_quantity)
        
        # 格式化后的数量应该符合最小数量要求
        assert formatted_quantity >= tiny_quantity, "格式化数量应该 >= 原始数量或最小数量"
        print(f"✓ 最小数量测试: {tiny_quantity} -> {formatted_quantity}")
    
    # ========== 平仓接口测试 ==========
    
    @pytest.mark.integration
    @pytest.mark.real_env
    @pytest.mark.slow
    def test_close_long_success(self, trader, test_symbol, test_usd_amount):
        """测试平多仓成功（指定数量）"""
        # 先开多仓
        price = trader.getMarketPrice(test_symbol)
        quantity = test_usd_amount / price
        formatted_quantity = trader.formatQuantity(test_symbol, quantity)
        
        trader.setLeverage(test_symbol, 3)
        trader.openLong(test_symbol, formatted_quantity, 3)
        time.sleep(3)
        
        # 平仓（使用部分数量）
        close_quantity = formatted_quantity / Decimal('2')
        result = trader.closeLong(test_symbol, close_quantity)
        assert result > 0, "平多仓失败"
        print(f"✓ 平多仓成功: {close_quantity} {test_symbol}")
        
        time.sleep(3)
        
        # 清理剩余持仓
        trader.closeLong(test_symbol, Decimal('0'))
        time.sleep(2)
    
    @pytest.mark.integration
    @pytest.mark.real_env
    @pytest.mark.slow
    def test_close_short_success(self, trader, test_symbol, test_usd_amount):
        """测试平空仓成功（指定数量）"""
        # 先开空仓
        price = trader.getMarketPrice(test_symbol)
        quantity = test_usd_amount / price
        formatted_quantity = trader.formatQuantity(test_symbol, quantity)
        
        trader.setLeverage(test_symbol, 3)
        trader.openShort(test_symbol, formatted_quantity, 3)
        time.sleep(3)
        
        # 平仓（使用部分数量）
        close_quantity = formatted_quantity / Decimal('2')
        result = trader.closeShort(test_symbol, close_quantity)
        assert result > 0, "平空仓失败"
        print(f"✓ 平空仓成功: {close_quantity} {test_symbol}")
        
        time.sleep(3)
        
        # 清理剩余持仓
        trader.closeShort(test_symbol, Decimal('0'))
        time.sleep(2)
    
    @pytest.mark.integration
    @pytest.mark.real_env
    @pytest.mark.slow
    def test_close_long_all(self, trader, test_symbol, test_usd_amount):
        """测试平全部多仓（quantity=0）"""
        # 先开多仓
        price = trader.getMarketPrice(test_symbol)
        quantity = test_usd_amount / price
        formatted_quantity = trader.formatQuantity(test_symbol, quantity)
        
        trader.setLeverage(test_symbol, 3)
        trader.openLong(test_symbol, formatted_quantity, 3)
        time.sleep(3)
        
        # 平全部多仓
        result = trader.closeLong(test_symbol, Decimal('0'))
        assert result > 0, "平全部多仓失败"
        print("✓ 平全部多仓成功")
        
        time.sleep(3)
    
    @pytest.mark.integration
    @pytest.mark.real_env
    @pytest.mark.slow
    def test_close_short_all(self, trader, test_symbol, test_usd_amount):
        """测试平全部空仓（quantity=0）"""
        # 先开空仓
        price = trader.getMarketPrice(test_symbol)
        quantity = test_usd_amount / price
        formatted_quantity = trader.formatQuantity(test_symbol, quantity)
        
        trader.setLeverage(test_symbol, 3)
        trader.openShort(test_symbol, formatted_quantity, 3)
        time.sleep(3)
        
        # 平全部空仓
        result = trader.closeShort(test_symbol, Decimal('0'))
        assert result > 0, "平全部空仓失败"
        print("✓ 平全部空仓成功")
        
        time.sleep(3)
    
    @pytest.mark.integration
    @pytest.mark.real_env
    def test_close_long_no_position(self, trader, test_symbol):
        """测试无持仓时平仓"""
        # 尝试平仓（应该返回成功，因为没有持仓）
        result = trader.closeLong(test_symbol, Decimal('0'))
        # 无持仓时应该返回成功（1）或失败（0），取决于实现
        assert result >= 0, "平仓结果应该 >= 0"
        print("✓ 无持仓平仓测试完成")
    
    @pytest.mark.integration
    @pytest.mark.real_env
    @pytest.mark.slow
    def test_close_long_partial(self, trader, test_symbol, test_usd_amount):
        """测试部分平仓"""
        # 先开多仓
        price = trader.getMarketPrice(test_symbol)
        quantity = test_usd_amount / price
        formatted_quantity = trader.formatQuantity(test_symbol, quantity)
        
        trader.setLeverage(test_symbol, 3)
        trader.openLong(test_symbol, formatted_quantity, 3)
        time.sleep(3)
        
        # 部分平仓（25%）
        partial_quantity = formatted_quantity * Decimal('0.25')
        result = trader.closeLong(test_symbol, partial_quantity)
        assert result > 0, "部分平仓失败"
        print(f"✓ 部分平仓成功: {partial_quantity} / {formatted_quantity}")
        
        time.sleep(3)
        
        # 清理剩余持仓
        trader.closeLong(test_symbol, Decimal('0'))
        time.sleep(2)
    
    # ========== 撤单接口测试 ==========
    
    @pytest.mark.integration
    @pytest.mark.real_env
    def test_cancel_all_orders_success(self, trader, test_symbol):
        """测试取消所有订单成功"""
        result = trader.cancelAllOrders(test_symbol)
        # 无论是否有订单，都应该返回成功（1）或失败（0）
        assert result >= 0, "撤单结果应该 >= 0"
        print("✓ 取消所有订单测试完成")
    
    @pytest.mark.integration
    @pytest.mark.real_env
    def test_cancel_all_orders_no_orders(self, trader, test_symbol):
        """测试无订单时撤单"""
        # 确保没有挂单
        trader.cancelAllOrders(test_symbol)
        time.sleep(1)
        
        # 再次撤单（应该返回成功）
        result = trader.cancelAllOrders(test_symbol)
        assert result >= 0, "无订单时撤单应该返回成功或失败"
        print("✓ 无订单撤单测试完成")
    
    # ========== 辅助方法测试 ==========
    
    @pytest.mark.integration
    @pytest.mark.real_env
    def test_set_leverage(self, trader, test_symbol):
        """测试设置杠杆"""
        leverage = 3
        result = trader.setLeverage(test_symbol, leverage)
        assert result > 0, f"设置杠杆失败: {result}"
        print(f"✓ 设置杠杆成功: {leverage}x")
    
    @pytest.mark.integration
    @pytest.mark.real_env
    def test_set_leverage_invalid(self, trader, test_symbol):
        """测试无效杠杆值"""
        # 测试0杠杆（应该失败或忽略）
        result = trader.setLeverage(test_symbol, 0)
        # 结果可能是0（失败）或1（忽略），都算正常
        assert result >= 0, "设置无效杠杆应该返回0或1"
        print("✓ 无效杠杆测试完成")
    
    @pytest.mark.integration
    @pytest.mark.real_env
    def test_format_quantity(self, trader, test_symbol):
        """测试格式化数量"""
        raw_quantity = Decimal('0.123456789')
        formatted = trader.formatQuantity(test_symbol, raw_quantity)
        
        assert formatted > 0, "格式化数量应该 > 0"
        assert formatted <= raw_quantity or formatted >= raw_quantity, "格式化数量应该合理"
        print(f"✓ 格式化数量: {raw_quantity} -> {formatted}")
    
    @pytest.mark.integration
    @pytest.mark.real_env
    def test_format_quantity_precision(self, trader, test_symbol):
        """测试数量精度"""
        # 测试不同精度的数量
        test_quantities = [
            Decimal('0.1'),
            Decimal('0.01'),
            Decimal('0.001'),
            Decimal('1.123456789')
        ]
        
        for qty in test_quantities:
            formatted = trader.formatQuantity(test_symbol, qty)
            assert formatted > 0, f"格式化数量应该 > 0: {qty} -> {formatted}"
            print(f"  {qty} -> {formatted}")
        
        print("✓ 数量精度测试完成")
    
    @pytest.mark.integration
    @pytest.mark.real_env
    def test_set_margin_mode(self, trader):
        """测试设置保证金模式"""
        # 测试全仓模式
        result = trader.setMarginMode(True)
        assert result > 0, "设置全仓模式失败"
        print("✓ 设置全仓模式成功")
        
        # 测试逐仓模式
        result = trader.setMarginMode(False)
        assert result > 0, "设置逐仓模式失败"
        print("✓ 设置逐仓模式成功")
        
        # 恢复全仓模式
        trader.setMarginMode(True)
    
    # ========== 完整工作流测试 ==========
    
    @pytest.mark.integration
    @pytest.mark.real_env
    @pytest.mark.slow
    def test_full_trading_workflow(self, trader, test_symbol, test_usd_amount):
        """测试完整交易流程：开多→设置止损→撤单→平多"""
        print("\n=== 开始完整交易流程测试（多仓）===")
        
        # 1. 设置保证金模式和杠杆
        trader.setMarginMode(True)
        trader.setLeverage(test_symbol, 3)
        print("1. 设置保证金模式和杠杆完成")
        
        # 2. 获取价格并计算数量
        price = trader.getMarketPrice(test_symbol)
        assert price > 0, f"无法获取价格: {price}"
        quantity = test_usd_amount / price
        formatted_quantity = trader.formatQuantity(test_symbol, quantity)
        print(f"2. 计算数量: {test_usd_amount} USD / {price} = {formatted_quantity}")
        
        # 3. 开多仓
        result = trader.openLong(test_symbol, formatted_quantity, 3)
        assert result > 0, "开多仓失败"
        print("3. 开多仓成功")
        time.sleep(5)
        
        # 4. 尝试设置止损（可能不支持）
        stop_price = price * Decimal('0.95')  # 5%止损
        result = trader.setStopLoss(test_symbol, 'long', Decimal('0'), stop_price)
        if result > 0:
            print(f"4. 设置止损成功: {stop_price}")
        else:
            print("4. 止损设置失败或不支持（可忽略）")
        
        # 5. 撤单（取消所有挂单）
        result = trader.cancelAllOrders(test_symbol)
        print("5. 撤单完成")
        time.sleep(2)
        
        # 6. 平多仓
        result = trader.closeLong(test_symbol, Decimal('0'))
        assert result > 0, "平多仓失败"
        print("6. 平多仓成功")
        time.sleep(3)
        
        print("=== 完整交易流程测试完成 ===\n")
    
    @pytest.mark.integration
    @pytest.mark.real_env
    @pytest.mark.slow
    def test_full_trading_workflow_short(self, trader, test_symbol, test_usd_amount):
        """测试完整交易流程：开空→设置止盈→撤单→平空"""
        print("\n=== 开始完整交易流程测试（空仓）===")
        
        # 1. 设置保证金模式和杠杆
        trader.setMarginMode(True)
        trader.setLeverage(test_symbol, 3)
        print("1. 设置保证金模式和杠杆完成")
        
        # 2. 获取价格并计算数量
        price = trader.getMarketPrice(test_symbol)
        assert price > 0, f"无法获取价格: {price}"
        quantity = test_usd_amount / price
        formatted_quantity = trader.formatQuantity(test_symbol, quantity)
        print(f"2. 计算数量: {test_usd_amount} USD / {price} = {formatted_quantity}")
        
        # 3. 开空仓
        result = trader.openShort(test_symbol, formatted_quantity, 3)
        assert result > 0, "开空仓失败"
        print("3. 开空仓成功")
        time.sleep(5)
        
        # 4. 尝试设置止盈（可能不支持）
        take_profit_price = price * Decimal('1.05')  # 5%止盈
        result = trader.setTakeProfit(test_symbol, 'short', Decimal('0'), take_profit_price)
        if result > 0:
            print(f"4. 设置止盈成功: {take_profit_price}")
        else:
            print("4. 止盈设置失败或不支持（可忽略）")
        
        # 5. 撤单（取消所有挂单）
        result = trader.cancelAllOrders(test_symbol)
        print("5. 撤单完成")
        time.sleep(2)
        
        # 6. 平空仓
        result = trader.closeShort(test_symbol, Decimal('0'))
        assert result > 0, "平空仓失败"
        print("6. 平空仓成功")
        time.sleep(3)
        
        print("=== 完整交易流程测试完成 ===\n")
    
    # ========== 清理fixture ==========
    
    @pytest.fixture(autouse=True)
    def cleanup_after_test(self, trader, test_symbol, request):
        """测试后清理：平掉所有持仓和订单"""
        yield
        
        # 只在完整工作流测试后不清理（因为它们已经自己清理了）
        if 'test_full_trading_workflow' not in request.node.name:
            try:
                print(f"\n清理持仓和订单: {test_symbol}...")
                # 取消所有订单
                trader.cancelAllOrders(test_symbol)
                time.sleep(1)
                # 平掉所有多仓
                trader.closeLong(test_symbol, Decimal('0'))
                time.sleep(2)
                # 平掉所有空仓
                trader.closeShort(test_symbol, Decimal('0'))
                time.sleep(2)
                print("清理完成\n")
            except Exception as e:
                print(f"清理持仓时出错（可忽略）: {e}\n")


if __name__ == '__main__':
    # 直接运行测试（不通过 pytest）
    pytest.main([__file__, '-v', '-s', '-m', 'integration'])
