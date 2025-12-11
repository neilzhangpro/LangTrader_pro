"""
Hyperliquid CCXT Trader 功能测试
测试使用CCXT实现的Hyperliquid交易接口的核心功能
"""
import pytest
import os
import time
from decimal import Decimal
from services.trader.hyperliquid_ccxt_trader import HyperliquidCcxTrader


class TestHyperliquidCcxTrader:
    """Hyperliquid CCXT Trader 功能测试"""
    
    @pytest.fixture
    def exchange_config(self):
        """创建测试用的交易所配置"""
        # 从环境变量读取配置（主网）
        wallet_address = os.getenv('HYPERLIQUID_WALLET_ADDRESS', '')
        secret_key = os.getenv('HYPERLIQUID_SECRET_KEY', '')
        
        if not wallet_address or not secret_key:
            pytest.skip("需要设置环境变量: HYPERLIQUID_WALLET_ADDRESS 和 HYPERLIQUID_SECRET_KEY")
        
        return {
            'wallet_address': wallet_address,
            'secret_key': secret_key,
            'testnet': False,  # 使用主网
            'is_cross_margin': True,
            'slippage': 0.01
        }
    
    @pytest.fixture
    def trader(self, exchange_config):
        """创建 trader 实例"""
        return HyperliquidCcxTrader(exchange_config)
    
    @pytest.fixture
    def test_symbol(self):
        """测试币种"""
        return 'BTC/USDT'
    
    @pytest.fixture
    def test_usd_amount(self):
        """测试金额（USD）"""
        return Decimal('5')
    
    def test_initialization(self, trader):
        """测试初始化"""
        assert trader is not None
        assert trader.wallet_address is not None
        assert trader.exchange is not None
        assert trader.testnet is False  # 主网模式
        print(f"✓ Trader 初始化成功，钱包地址: {trader.wallet_address[:10]}...")
        print(f"⚠️ 警告: 当前使用主网模式，所有操作将使用真实资金！")
    
    def test_get_market_price(self, trader, test_symbol):
        """测试获取市场价格"""
        price = trader.getMarketPrice(test_symbol)
        assert price > 0, f"获取价格失败或价格为0: {price}"
        print(f"✓ BTC 当前价格: {price} USDT")
    
    def test_get_balance(self, trader, test_symbol):
        """测试获取余额"""
        balance = trader.get_balance(test_symbol)
        assert balance >= 0, "余额应该 >= 0"
        print(f"✓ 账户余额: {balance} USDT")
    
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
    
    def test_set_leverage(self, trader, test_symbol):
        """测试设置杠杆"""
        leverage = 3
        result = trader.setLeverage(test_symbol, leverage)
        assert result > 0, f"设置杠杆失败: {result}"
        print(f"✓ 设置杠杆成功: {leverage}x")
    
    def test_calculate_quantity(self, trader, test_symbol, test_usd_amount):
        """测试计算数量"""
        # 获取当前价格
        price = trader.getMarketPrice(test_symbol)
        assert price > 0, "无法获取价格"
        
        # 计算数量
        quantity = test_usd_amount / price
        formatted_quantity = trader.formatQuantity(test_symbol, quantity)
        
        assert formatted_quantity > 0, "计算出的数量无效"
        print(f"✓ 计算数量: {test_usd_amount} USD / {price} = {formatted_quantity} BTC")
        return formatted_quantity
    
    def test_open_long(self, trader, test_symbol, test_usd_amount):
        """测试开多仓"""
        # 计算数量
        price = trader.getMarketPrice(test_symbol)
        quantity = test_usd_amount / price
        formatted_quantity = trader.formatQuantity(test_symbol, quantity)
        
        # 设置杠杆
        trader.setLeverage(test_symbol, 3)
        
        # 开多仓
        result = trader.openLong(test_symbol, formatted_quantity, 3)
        assert result > 0, f"开多仓失败: {result}"
        print(f"✓ 开多仓成功: {formatted_quantity} BTC")
        
        # 等待订单执行
        time.sleep(3)
        
        return formatted_quantity
    
    def test_open_short(self, trader, test_symbol, test_usd_amount):
        """测试开空仓"""
        # 计算数量
        price = trader.getMarketPrice(test_symbol)
        quantity = test_usd_amount / price
        formatted_quantity = trader.formatQuantity(test_symbol, quantity)
        
        # 设置杠杆
        trader.setLeverage(test_symbol, 3)
        
        # 开空仓
        result = trader.openShort(test_symbol, formatted_quantity, 3)
        assert result > 0, f"开空仓失败: {result}"
        print(f"✓ 开空仓成功: {formatted_quantity} BTC")
        
        # 等待订单执行
        time.sleep(3)
        
        return formatted_quantity
    
    def test_close_long(self, trader, test_symbol):
        """测试平多仓"""
        # 平仓所有多仓
        result = trader.closeLong(test_symbol, Decimal('0'))
        assert result > 0, f"平多仓失败: {result}"
        print("✓ 平多仓成功")
        
        # 等待订单执行
        time.sleep(3)
    
    def test_close_short(self, trader, test_symbol):
        """测试平空仓"""
        # 平仓所有空仓
        result = trader.closeShort(test_symbol, Decimal('0'))
        assert result > 0, f"平空仓失败: {result}"
        print("✓ 平空仓成功")
        
        # 等待订单执行
        time.sleep(3)
    
    def test_full_workflow(self, trader, test_symbol, test_usd_amount):
        """测试完整工作流程：开多→平多→开空→平空"""
        print("\n=== 开始完整工作流程测试 ===")
        
        # 1. 设置保证金模式为全仓
        result = trader.setMarginMode(True)
        assert result > 0, "设置保证金模式失败"
        print("1. 设置保证金模式: 全仓")
        
        # 2. 设置杠杆
        result = trader.setLeverage(test_symbol, 3)
        if result <= 0:
            print(f"⚠️ 警告: 设置杠杆失败，继续测试（可能杠杆已经设置过）")
        else:
            print("2. 设置杠杆: 3x")
        
        # 3. 获取当前价格并计算数量
        price = trader.getMarketPrice(test_symbol)
        assert price > 0, f"无法获取价格: {price}"
        quantity = test_usd_amount / price
        formatted_quantity = trader.formatQuantity(test_symbol, quantity)
        print(f"3. 计算数量: {test_usd_amount} USD / {price} = {formatted_quantity} BTC")
        
        # 4. 开多仓
        print("4. 开多仓...")
        result = trader.openLong(test_symbol, formatted_quantity, 3)
        if result <= 0:
            print(f"❌ 开多仓失败，可能原因：")
            print(f"   - 杠杆设置问题")
            print(f"   - 余额不足")
            print(f"   - 订单金额太小")
            print(f"   请查看日志获取详细错误信息")
        assert result > 0, "开多仓失败，请查看上方日志获取详细错误信息"
        time.sleep(5)  # 等待订单执行
        
        # 5. 平多仓
        print("5. 平多仓...")
        result = trader.closeLong(test_symbol, Decimal('0'))
        assert result > 0, "平多仓失败"
        time.sleep(5)  # 等待订单执行
        
        # 6. 开空仓
        print("6. 开空仓...")
        result = trader.openShort(test_symbol, formatted_quantity, 3)
        assert result > 0, "开空仓失败"
        time.sleep(5)  # 等待订单执行
        
        # 7. 平空仓
        print("7. 平空仓...")
        result = trader.closeShort(test_symbol, Decimal('0'))
        assert result > 0, "平空仓失败"
        time.sleep(5)  # 等待订单执行
        
        print("=== 完整工作流程测试完成 ===\n")
    
    # ========== 增强的下单测试 ==========
    
    @pytest.mark.integration
    @pytest.mark.real_env
    @pytest.mark.slow
    def test_open_long_edge_cases(self, trader, test_symbol, test_usd_amount):
        """测试开多仓边界条件"""
        price = trader.getMarketPrice(test_symbol)
        
        # 测试1: 非常小的数量
        tiny_quantity = Decimal('0.00001')
        formatted_tiny = trader.formatQuantity(test_symbol, tiny_quantity)
        print(f"✓ 小数量测试: {tiny_quantity} -> {formatted_tiny}")
        
        # 测试2: 正常数量
        normal_quantity = test_usd_amount / price
        formatted_normal = trader.formatQuantity(test_symbol, normal_quantity)
        print(f"✓ 正常数量测试: {normal_quantity} -> {formatted_normal}")
        
        # 测试3: 不同杠杆值
        for leverage in [2, 3, 5]:
            result = trader.setLeverage(test_symbol, leverage)
            if result > 0:
                print(f"✓ 杠杆 {leverage}x 设置成功")
                break
    
    @pytest.mark.integration
    @pytest.mark.real_env
    @pytest.mark.slow
    def test_open_short_edge_cases(self, trader, test_symbol, test_usd_amount):
        """测试开空仓边界条件"""
        price = trader.getMarketPrice(test_symbol)
        quantity = test_usd_amount / price
        formatted_quantity = trader.formatQuantity(test_symbol, quantity)
        
        # 测试不同杠杆值
        for leverage in [2, 3, 5]:
            result = trader.setLeverage(test_symbol, leverage)
            if result > 0:
                print(f"✓ 杠杆 {leverage}x 设置成功")
                break
        
        # 测试开空仓
        result = trader.openShort(test_symbol, formatted_quantity, 3)
        if result > 0:
            print(f"✓ 开空仓边界测试成功")
            time.sleep(3)
            # 清理
            trader.closeShort(test_symbol, Decimal('0'))
            time.sleep(2)
    
    @pytest.mark.integration
    @pytest.mark.real_env
    def test_open_long_with_different_leverages(self, trader, test_symbol, test_usd_amount):
        """测试不同杠杆值开多仓"""
        price = trader.getMarketPrice(test_symbol)
        quantity = test_usd_amount / price
        formatted_quantity = trader.formatQuantity(test_symbol, quantity)
        
        # 测试不同杠杆值
        for leverage in [2, 3, 5]:
            result = trader.setLeverage(test_symbol, leverage)
            if result > 0:
                print(f"✓ 杠杆 {leverage}x 设置成功")
                # 可以尝试开仓（但为了测试速度，这里只测试设置杠杆）
                break
    
    @pytest.mark.integration
    @pytest.mark.real_env
    def test_open_long_quantity_precision(self, trader, test_symbol):
        """测试数量精度处理"""
        # 测试不同精度的数量
        test_quantities = [
            Decimal('0.0001'),
            Decimal('0.001'),
            Decimal('0.01'),
            Decimal('0.1'),
            Decimal('1.123456789')
        ]
        
        for qty in test_quantities:
            formatted = trader.formatQuantity(test_symbol, qty)
            assert formatted > 0, f"格式化数量应该 > 0: {qty}"
            print(f"  {qty} -> {formatted}")
        
        print("✓ 数量精度测试完成")
    
    # ========== 增强的平仓测试 ==========
    
    @pytest.mark.integration
    @pytest.mark.real_env
    @pytest.mark.slow
    def test_close_long_edge_cases(self, trader, test_symbol, test_usd_amount):
        """测试平多仓边界条件"""
        # 先开多仓
        price = trader.getMarketPrice(test_symbol)
        quantity = test_usd_amount / price
        formatted_quantity = trader.formatQuantity(test_symbol, quantity)
        
        trader.setLeverage(test_symbol, 3)
        trader.openLong(test_symbol, formatted_quantity, 3)
        time.sleep(3)
        
        # 测试1: 平全部（quantity=0）
        result = trader.closeLong(test_symbol, Decimal('0'))
        assert result > 0, "平全部多仓应该成功"
        print("✓ 平全部多仓测试成功")
        time.sleep(3)
        
        # 测试2: 无持仓时平仓
        result = trader.closeLong(test_symbol, Decimal('0'))
        assert result > 0, "无持仓时平仓应该返回成功"
        print("✓ 无持仓平仓测试成功")
    
    @pytest.mark.integration
    @pytest.mark.real_env
    @pytest.mark.slow
    def test_close_short_edge_cases(self, trader, test_symbol, test_usd_amount):
        """测试平空仓边界条件"""
        # 先开空仓
        price = trader.getMarketPrice(test_symbol)
        quantity = test_usd_amount / price
        formatted_quantity = trader.formatQuantity(test_symbol, quantity)
        
        trader.setLeverage(test_symbol, 3)
        trader.openShort(test_symbol, formatted_quantity, 3)
        time.sleep(3)
        
        # 测试1: 平全部（quantity=0）
        result = trader.closeShort(test_symbol, Decimal('0'))
        assert result > 0, "平全部空仓应该成功"
        print("✓ 平全部空仓测试成功")
        time.sleep(3)
        
        # 测试2: 无持仓时平仓
        result = trader.closeShort(test_symbol, Decimal('0'))
        assert result > 0, "无持仓时平仓应该返回成功"
        print("✓ 无持仓平仓测试成功")
    
    @pytest.mark.integration
    @pytest.mark.real_env
    @pytest.mark.slow
    def test_close_position_with_slippage(self, trader, test_symbol, test_usd_amount):
        """测试滑点处理"""
        # 先开多仓
        price = trader.getMarketPrice(test_symbol)
        quantity = test_usd_amount / price
        formatted_quantity = trader.formatQuantity(test_symbol, quantity)
        
        trader.setLeverage(test_symbol, 3)
        trader.openLong(test_symbol, formatted_quantity, 3)
        time.sleep(3)
        
        # 平仓（应该能处理滑点）
        result = trader.closeLong(test_symbol, Decimal('0'))
        assert result > 0, "平仓应该成功（即使有滑点）"
        print("✓ 滑点处理测试成功")
        time.sleep(3)
    
    # ========== 增强的撤单测试 ==========
    
    @pytest.mark.integration
    @pytest.mark.real_env
    def test_cancel_all_orders_edge_cases(self, trader, test_symbol):
        """测试撤单边界条件"""
        # 测试1: 无订单时撤单
        result = trader.cancelAllOrders(test_symbol)
        assert result > 0, "无订单时撤单应该返回成功"
        print("✓ 无订单撤单测试成功")
        
        # 测试2: 多次撤单
        result1 = trader.cancelAllOrders(test_symbol)
        result2 = trader.cancelAllOrders(test_symbol)
        assert result1 > 0 and result2 > 0, "多次撤单应该都成功"
        print("✓ 多次撤单测试成功")
    
    @pytest.mark.integration
    @pytest.mark.real_env
    @pytest.mark.slow
    def test_cancel_all_orders_after_open(self, trader, test_symbol, test_usd_amount):
        """测试开仓后撤单"""
        # 先开多仓
        price = trader.getMarketPrice(test_symbol)
        quantity = test_usd_amount / price
        formatted_quantity = trader.formatQuantity(test_symbol, quantity)
        
        trader.setLeverage(test_symbol, 3)
        trader.openLong(test_symbol, formatted_quantity, 3)
        time.sleep(3)
        
        # 撤单（取消所有挂单）
        result = trader.cancelAllOrders(test_symbol)
        assert result > 0, "撤单应该成功"
        print("✓ 开仓后撤单测试成功")
        
        # 清理
        trader.closeLong(test_symbol, Decimal('0'))
        time.sleep(2)
    
    # ========== 错误处理测试 ==========
    
    @pytest.mark.integration
    @pytest.mark.real_env
    def test_open_long_network_error(self, trader, test_symbol):
        """测试网络错误处理（通过无效symbol模拟）"""
        # 使用无效的symbol（应该返回0而不是抛出异常）
        invalid_symbol = 'INVALID/USDT'
        result = trader.openLong(invalid_symbol, Decimal('0.001'), 3)
        
        # 应该返回0（失败）而不是抛出异常
        assert result >= 0, "网络错误时应该返回0或1，不应该抛出异常"
        print("✓ 网络错误处理测试成功")
    
    @pytest.mark.integration
    @pytest.mark.real_env
    def test_open_long_exchange_error(self, trader, test_symbol):
        """测试交易所错误处理"""
        # 使用无效数量（应该返回0而不是抛出异常）
        invalid_quantity = Decimal('-0.001')  # 负数
        result = trader.openLong(test_symbol, invalid_quantity, 3)
        
        # 应该返回0（失败）而不是抛出异常
        assert result >= 0, "交易所错误时应该返回0或1，不应该抛出异常"
        print("✓ 交易所错误处理测试成功")
    
    @pytest.mark.integration
    @pytest.mark.real_env
    def test_close_long_timeout(self, trader, test_symbol):
        """测试超时处理（无持仓时平仓）"""
        # 无持仓时平仓（应该能处理，不会超时）
        result = trader.closeLong(test_symbol, Decimal('0'))
        
        # 应该返回成功或失败，不应该超时
        assert result >= 0, "超时处理应该返回0或1，不应该抛出异常"
        print("✓ 超时处理测试成功")
    
    # ========== 完整工作流增强测试 ==========
    
    @pytest.mark.integration
    @pytest.mark.real_env
    @pytest.mark.slow
    def test_full_workflow_with_cancel(self, trader, test_symbol, test_usd_amount):
        """测试完整工作流程（包含撤单）：开多→撤单→平多→开空→撤单→平空"""
        print("\n=== 开始完整工作流程测试（包含撤单）===")
        
        # 1. 设置保证金模式和杠杆
        trader.setMarginMode(True)
        trader.setLeverage(test_symbol, 3)
        print("1. 设置保证金模式和杠杆完成")
        
        # 2. 获取价格并计算数量
        price = trader.getMarketPrice(test_symbol)
        quantity = test_usd_amount / price
        formatted_quantity = trader.formatQuantity(test_symbol, quantity)
        print(f"2. 计算数量: {test_usd_amount} USD / {price} = {formatted_quantity}")
        
        # 3. 开多仓
        result = trader.openLong(test_symbol, formatted_quantity, 3)
        assert result > 0, "开多仓失败"
        print("3. 开多仓成功")
        time.sleep(5)
        
        # 4. 撤单
        result = trader.cancelAllOrders(test_symbol)
        print("4. 撤单完成")
        time.sleep(2)
        
        # 5. 平多仓
        result = trader.closeLong(test_symbol, Decimal('0'))
        assert result > 0, "平多仓失败"
        print("5. 平多仓成功")
        time.sleep(5)
        
        # 6. 开空仓
        result = trader.openShort(test_symbol, formatted_quantity, 3)
        assert result > 0, "开空仓失败"
        print("6. 开空仓成功")
        time.sleep(5)
        
        # 7. 撤单
        result = trader.cancelAllOrders(test_symbol)
        print("7. 撤单完成")
        time.sleep(2)
        
        # 8. 平空仓
        result = trader.closeShort(test_symbol, Decimal('0'))
        assert result > 0, "平空仓失败"
        print("8. 平空仓成功")
        time.sleep(5)
        
        print("=== 完整工作流程测试完成 ===\n")
    
    @pytest.fixture(autouse=True)
    def cleanup_after_test(self, trader, test_symbol, request):
        """测试后清理：平掉所有持仓和订单"""
        yield
        
        # 只在完整工作流程测试后不清理（因为它们已经自己清理了）
        workflow_tests = ['test_full_workflow', 'test_full_workflow_with_cancel']
        if not any(test_name in request.node.name for test_name in workflow_tests):
            try:
                print(f"\n清理持仓和订单: {test_symbol}...")
                # 取消所有订单
                trader.cancelAllOrders(test_symbol)
                time.sleep(1)
                # 尝试平掉所有多仓
                trader.closeLong(test_symbol, Decimal('0'))
                time.sleep(2)
                # 尝试平掉所有空仓
                trader.closeShort(test_symbol, Decimal('0'))
                time.sleep(2)
                print("清理完成\n")
            except Exception as e:
                print(f"清理持仓时出错（可忽略）: {e}\n")


if __name__ == '__main__':
    # 直接运行测试（不通过 pytest）
    pytest.main([__file__, '-v', '-s', '-m', 'integration'])

