-- Active: 1749699811985@@127.0.0.1@5432@langtraders
-- 1. 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    otp_secret VARCHAR(32), -- 2FA secret key
    otp_verified BOOLEAN DEFAULT FALSE, -- 2FA是否验证
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. AI模型配置表
CREATE TABLE ai_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    provider VARCHAR(50) NOT NULL, -- 'openai', 'anthropic', 'custom' 等
    enabled BOOLEAN DEFAULT FALSE,
    api_key TEXT DEFAULT '',
    base_url TEXT DEFAULT '', -- 自定义API地址
    model_name TEXT DEFAULT '', -- 自定义模型名称
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. 交易所配置表
CREATE TABLE exchanges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(10) NOT NULL, -- 'cex' or 'dex'
    enabled BOOLEAN DEFAULT FALSE,
    api_key TEXT DEFAULT '',
    secret_key TEXT DEFAULT '',
    testnet BOOLEAN DEFAULT FALSE,
    -- Hyperliquid 特定字段
    hyperliquid_wallet_addr VARCHAR(255) DEFAULT '',
    -- Aster 特定字段
    aster_user VARCHAR(255) DEFAULT '',
    aster_signer VARCHAR(255) DEFAULT '',
    aster_private_key TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. 系统提示词模板表
CREATE TABLE prompt_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL DEFAULT 'default', -- 模板名称，如 'default', 'aggressive', 'conservative'
    content TEXT NOT NULL DEFAULT '你是专业的加密货币交易AI，在合约市场进行自主交易。

# 核心目标

最大化夏普比率（Sharpe Ratio）

夏普比率 = 平均收益 / 收益波动率

这意味着：
- 高质量交易（高胜率、大盈亏比）→ 提升夏普
- 稳定收益、控制回撤 → 提升夏普
- 耐心持仓、让利润奔跑 → 提升夏普
- 频繁交易、小盈小亏 → 增加波动，严重降低夏普
- 过度交易、手续费损耗 → 直接亏损
- 过早平仓、频繁进出 → 错失大行情

关键认知: 系统每3分钟扫描一次，但不意味着每次都要交易！
大多数时候应该是 `wait` 或 `hold`，只在极佳机会时才开仓。

# 交易哲学 & 最佳实践

## 核心原则：

资金保全第一：保护资本比追求收益更重要

纪律胜于情绪：执行你的退出方案，不随意移动止损或目标

质量优于数量：少量高信念交易胜过大量低信念交易

适应波动性：根据市场条件调整仓位

尊重趋势：不要与强趋势作对

## 常见误区避免：

过度交易：频繁交易导致费用侵蚀利润

复仇式交易：亏损后立即加码试图"翻本"

分析瘫痪：过度等待完美信号，导致失机

忽视相关性：BTC常引领山寨币，须优先观察BTC

过度杠杆：放大收益同时放大亏损

#交易频率认知

量化标准:
- 优秀交易员：每天2-4笔 = 每小时0.1-0.2笔
- 过度交易：每小时>2笔 = 严重问题
- 最佳节奏：开仓后持有至少30-60分钟

自查:
如果你发现自己每个周期都在交易 → 说明标准太低
如果你发现持仓<30分钟就平仓 → 说明太急躁

# 开仓标准（严格）

只在强信号时开仓，不确定就观望。

你拥有的完整数据：
- 原始序列：3分钟价格序列(MidPrices数组) + 4小时K线序列
- 技术序列：EMA20序列、MACD序列、RSI7序列、RSI14序列
- 资金序列：成交量序列、持仓量(OI)序列、资金费率
- 筛选标记：AI500评分 / OI_Top排名（如果有标注）

分析方法（完全由你自主决定）：
- 自由运用序列数据，你可以做但不限于趋势分析、形态识别、支撑阻力、技术阻力位、斐波那契、波动带计算
- 多维度交叉验证（价格+量+OI+指标+序列形态）
- 用你认为最有效的方法发现高确定性机会
- 综合信心度 ≥ 75 才开仓

避免低质量信号：
- 单一维度（只看一个指标）
- 相互矛盾（涨但量萎缩）
- 横盘震荡
- 刚平仓不久（<15分钟）

# 夏普比率自我进化

每次你会收到夏普比率作为绩效反馈（周期级别）：

夏普比率 < -0.5 (持续亏损):
  → 停止交易，连续观望至少6个周期（18分钟）
  → 深度反思：
     • 交易频率过高？（每小时>2次就是过度）
     • 持仓时间过短？（<30分钟就是过早平仓）
     • 信号强度不足？（信心度<75）
夏普比率 -0.5 ~ 0 (轻微亏损):
  → 严格控制：只做信心度>80的交易
  → 减少交易频率：每小时最多1笔新开仓
  → 耐心持仓：至少持有30分钟以上

夏普比率 0 ~ 0.7 (正收益):
  → 维持当前策略

夏普比率 > 0.7 (优异表现):
  → 可适度扩大仓位

关键: 夏普比率是唯一指标，它会自然惩罚频繁交易和过度进出。

#决策流程

1. 分析夏普比率: 当前策略是否有效？需要调整吗？
2. 评估持仓: 趋势是否改变？是否该止盈/止损？
3. 寻找新机会: 有强信号吗？多空机会？
4. 输出决策: 思维链分析 + JSON

---

记住:
- 目标是夏普比率，不是交易频率
- 宁可错过，不做低质量交易
- 风险回报比1:3是底线', -- 模板内容
    description TEXT DEFAULT '默认提示词模板', -- 模板描述
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

-- 5. 交易员配置表
CREATE TABLE traders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    ai_model_id UUID NOT NULL REFERENCES ai_models(id),
    exchange_id UUID NOT NULL REFERENCES exchanges(id),
    initial_balance DECIMAL(20, 8) NOT NULL,
    scan_interval_minutes INTEGER DEFAULT 3,
    is_running BOOLEAN DEFAULT FALSE,
    -- 杠杆配置
    btc_eth_leverage INTEGER DEFAULT 5,
    altcoin_leverage INTEGER DEFAULT 5,
    -- 币种配置
    trading_symbols TEXT DEFAULT '', -- 交易币种，逗号分隔
    use_default_coins BOOLEAN DEFAULT TRUE, -- 是否使用默认币种
    custom_coins TEXT DEFAULT '', -- 自定义币种列表（JSON格式）
    -- 信号源配置
    use_coin_pool BOOLEAN DEFAULT FALSE, -- 是否使用COIN POOL信号源
    use_oi_top BOOLEAN DEFAULT FALSE, -- 是否使用OI TOP信号源
    use_inside_coins BOOLEAN DEFAULT FALSE, -- 是否使用内置AI评分信号源
    -- 提示词配置
    system_prompt_template VARCHAR(255) DEFAULT 'default', -- 系统提示词模板名称
    custom_prompt TEXT DEFAULT '', -- 自定义提示词
    override_base_prompt BOOLEAN DEFAULT FALSE, -- 是否覆盖基础提示词
    -- 保证金模式
    is_cross_margin BOOLEAN DEFAULT TRUE, -- 默认为全仓模式
    -- LangGraph 决策引擎配置
    decision_graph_config JSONB, -- LangGraph 图配置（节点、边、状态等）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. 用户信号源配置表
CREATE TABLE user_signal_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    coin_pool_url TEXT DEFAULT '',
    oi_top_url TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. 系统配置表
CREATE TABLE system_config (
    key VARCHAR(255) PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- 8. 交易记录表（新增，用于记录实际交易）
CREATE TABLE trade_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trader_id UUID NOT NULL REFERENCES traders(id) ON DELETE CASCADE,
    symbol VARCHAR(50) NOT NULL, -- 交易对，如 'BTC/USDT'
    side VARCHAR(10) NOT NULL, -- 'buy' or 'sell'
    amount DECIMAL(20, 8) NOT NULL,
    price DECIMAL(20, 8) NOT NULL,
    leverage INTEGER DEFAULT 1,
    order_id VARCHAR(255), -- 交易所订单ID
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'filled', 'cancelled', 'failed'
    executed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. 决策日志表（新增，用于记录 LangGraph 决策过程）
CREATE TABLE decision_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trader_id UUID NOT NULL REFERENCES traders(id) ON DELETE CASCADE,
    symbol VARCHAR(50) NOT NULL,
    decision_state JSONB NOT NULL, -- LangGraph 状态快照
    decision_result VARCHAR(50), -- 'buy', 'sell', 'hold'
    reasoning TEXT, -- AI 决策理由
    confidence DECIMAL(5, 4), -- 决策置信度 0-1
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- 索引
CREATE INDEX idx_ai_models_user_id ON ai_models(user_id);
CREATE INDEX idx_exchanges_user_id ON exchanges(user_id);
CREATE INDEX idx_traders_user_id ON traders(user_id);
CREATE INDEX idx_traders_ai_model_id ON traders(ai_model_id);
CREATE INDEX idx_traders_exchange_id ON traders(exchange_id);
CREATE INDEX idx_traders_is_running ON traders(is_running);
CREATE INDEX idx_trade_records_trader_id ON trade_records(trader_id);
CREATE INDEX idx_trade_records_created_at ON trade_records(created_at);
CREATE INDEX idx_decision_logs_trader_id ON decision_logs(trader_id);
CREATE INDEX idx_decision_logs_created_at ON decision_logs(created_at);

-- 触发器：自动更新 updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ai_models_updated_at BEFORE UPDATE ON ai_models
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_exchanges_updated_at BEFORE UPDATE ON exchanges
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_traders_updated_at BEFORE UPDATE ON traders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_signal_sources_updated_at BEFORE UPDATE ON user_signal_sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_prompt_templates_updated_at BEFORE UPDATE ON prompt_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_config_updated_at BEFORE UPDATE ON system_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();