# Trader模块单元测试说明

## 测试文件概览

本次为Trader模块创建了全面的单元测试，重点测试下单和撤单接口：

### 1. `test_cex_ccxt_trader.py` (26个测试)
- **目标**：测试CexCcxTrader类（CEX交易所）
- **支持交易所**：Binance、OKX、Gate.io
- **测试类型**：真实环境测试（需要配置API密钥）

### 2. `test_ccxt_trader_base.py` (23个测试)
- **目标**：测试CcxTraderBase基类的通用方法
- **测试类型**：Mock测试（不需要真实环境）
- **优势**：快速、安全、可重复

### 3. `test_hyperliquid_trader.py` (26个测试，已增强)
- **目标**：测试HyperliquidCcxTrader类（DEX交易所）
- **测试类型**：真实环境测试（需要配置钱包地址和私钥）
- **增强内容**：新增边界条件测试、错误处理测试、完整工作流测试

## 测试覆盖范围

### 下单接口测试
- ✅ `openLong` - 开多仓（正常流程、边界条件、错误处理）
- ✅ `openShort` - 开空仓（正常流程、边界条件、错误处理）
- ✅ 不同杠杆值测试
- ✅ 数量精度处理测试
- ✅ 最小数量限制测试

### 平仓接口测试
- ✅ `closeLong` - 平多仓（指定数量、平全部、无持仓情况）
- ✅ `closeShort` - 平空仓（指定数量、平全部、无持仓情况）
- ✅ 部分平仓测试
- ✅ 滑点处理测试

### 撤单接口测试
- ✅ `cancelAllOrders` - 取消所有订单（有订单、无订单、错误处理）
- ✅ 开仓后撤单测试
- ✅ 多次撤单测试

### 辅助方法测试
- ✅ `setLeverage` - 设置杠杆
- ✅ `formatQuantity` - 格式化数量
- ✅ `setMarginMode` - 设置保证金模式
- ✅ `getMarketPrice` - 获取市场价格
- ✅ `get_balance` - 获取余额
- ✅ `get_all_positions` - 获取所有持仓

### 完整工作流测试
- ✅ 开多→设置止损→撤单→平多
- ✅ 开空→设置止盈→撤单→平空
- ✅ 开多→撤单→平多→开空→撤单→平空

## 环境变量配置

### CEX交易所（Binance示例）
```bash
export BINANCE_API_KEY=your_api_key
export BINANCE_SECRET_KEY=your_secret_key
export BINANCE_TESTNET=false
```

### DEX交易所（Hyperliquid）
```bash
export HYPERLIQUID_WALLET_ADDRESS=0x...
export HYPERLIQUID_SECRET_KEY=0x...
export HYPERLIQUID_TESTNET=false
```

## 运行测试

### 运行所有Trader测试
```bash
pytest tests/test_*trader*.py -v
```

### 运行特定测试文件
```bash
# CEX测试
pytest tests/test_cex_ccxt_trader.py -v

# 基类测试（Mock，快速）
pytest tests/test_ccxt_trader_base.py -v

# DEX测试
pytest tests/test_hyperliquid_trader.py -v
```

### 运行特定类型的测试
```bash
# 仅下单测试
pytest tests/test_*trader*.py -k "open" -v

# 仅撤单测试
pytest tests/test_*trader*.py -k "cancel" -v

# 仅平仓测试
pytest tests/test_*trader*.py -k "close" -v
```

### 使用测试标记
```bash
# 仅集成测试（真实环境）
pytest tests/test_*trader*.py -m integration -v

# 仅单元测试（Mock）
pytest tests/test_*trader*.py -m unit -v

# 排除慢速测试
pytest tests/test_*trader*.py -m "not slow" -v
```

## 测试安全措施

1. **小额测试**：所有真实环境测试使用小额资金（5-10 USDT）
2. **自动清理**：测试后自动平掉所有持仓和订单
3. **错误恢复**：测试失败时尝试清理持仓
4. **环境检查**：未配置环境变量时跳过测试
5. **测试隔离**：每个测试独立运行，不依赖其他测试状态

## 测试统计

- **总测试方法数**：75个
- **CEX测试**：26个
- **基类测试（Mock）**：23个
- **DEX测试**：26个
- **代码覆盖率目标**：80%以上
- **接口覆盖率**：100%（所有ExchangeInterface方法）

## 注意事项

1. **真实环境测试风险**：使用真实交易所，需要小心处理
2. **测试数据清理**：确保测试后清理所有持仓和订单
3. **环境变量管理**：不要将密钥提交到代码仓库
4. **测试隔离**：每个测试应该独立，不依赖其他测试的状态
5. **错误处理**：测试验证了错误情况的处理
6. **性能考虑**：真实环境测试可能较慢，需要合理设置超时

## 测试标记说明

- `@pytest.mark.integration` - 集成测试（需要真实环境）
- `@pytest.mark.unit` - 单元测试（使用Mock）
- `@pytest.mark.real_env` - 真实环境测试
- `@pytest.mark.slow` - 慢速测试（可能需要较长时间）
- `@pytest.mark.cex` - CEX交易所测试
- `@pytest.mark.dex` - DEX交易所测试

## 故障排查

### 测试失败常见原因

1. **环境变量未配置**：检查是否设置了必要的API密钥或钱包地址
2. **余额不足**：确保账户有足够的测试资金（5-10 USDT）
3. **网络问题**：检查网络连接和交易所API状态
4. **订单执行失败**：可能是订单金额太小或市场波动
5. **持仓清理失败**：可能是订单仍在执行中，等待更长时间

### 调试技巧

1. 使用 `-v` 参数查看详细输出
2. 使用 `-s` 参数查看print输出
3. 使用 `--pdb` 在失败时进入调试器
4. 查看日志文件获取详细错误信息
