-- ============================================
-- 测试数据
-- ============================================

-- 1. 插入测试用户
INSERT INTO users (id, email, password_hash, otp_verified, created_at) VALUES
('00000000-0000-0000-0000-000000000001', 'test@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyY5Y5Y5Y5Y5', TRUE, CURRENT_TIMESTAMP),
('00000000-0000-0000-0000-000000000002', 'admin@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyY5Y5Y5Y5Y5', TRUE, CURRENT_TIMESTAMP);

-- 2. 插入 AI 模型配置
INSERT INTO ai_models (id, user_id, name, provider, enabled, api_key, base_url, model_name, created_at) VALUES
('10000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', 'OpenAI GPT-4', 'openai', TRUE, 'sk-test-key-123456', '', 'gpt-4', CURRENT_TIMESTAMP),
('10000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000001', 'Claude 3.5', 'anthropic', TRUE, 'sk-ant-test-key-123456', '', 'claude-3-5-sonnet', CURRENT_TIMESTAMP),
('10000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000002', 'Custom Model', 'custom', TRUE, 'custom-key-123', 'https://api.example.com/v1', 'custom-model-v1', CURRENT_TIMESTAMP);

-- 3. 插入交易所配置
INSERT INTO exchanges (id, user_id, name, type, enabled, api_key, secret_key, testnet, created_at) VALUES
('20000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', 'Binance Test', 'cex', TRUE, 'test-api-key-123', 'test-secret-key-456', TRUE, CURRENT_TIMESTAMP),
('20000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000001', 'OKX Test', 'cex', TRUE, 'okx-api-key-123', 'okx-secret-key-456', TRUE, CURRENT_TIMESTAMP),
('20000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000001', 'Hyperliquid', 'dex', TRUE, '', '', FALSE, CURRENT_TIMESTAMP);

-- 4. 插入提示词模板（系统默认模板已存在，这里添加用户自定义模板）
-- 注意：如果 prompt_templates 表有 user_id 字段，需要添加
-- 这里假设系统模板的 user_id 为 NULL

-- 5. 插入交易员配置
INSERT INTO traders (
    id, user_id, name, ai_model_id, exchange_id, 
    initial_balance, scan_interval_minutes, is_running,
    btc_eth_leverage, altcoin_leverage,
    trading_symbols, use_default_coins,
    use_coin_pool, use_oi_top, use_inside_coins,
    system_prompt_template, is_cross_margin,
    created_at
) VALUES
(
    '30000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000001',
    'BTC/ETH 交易员',
    '10000000-0000-0000-0000-000000000001',
    '20000000-0000-0000-0000-000000000001',
    10000.00000000,
    3,
    FALSE,
    5,
    3,
    'BTC/USDT,ETH/USDT',
    TRUE,
    FALSE,
    TRUE,
    TRUE,
    'default',
    TRUE,
    CURRENT_TIMESTAMP
),
(
    '30000000-0000-0000-0000-000000000002',
    '00000000-0000-0000-0000-000000000001',
    '山寨币交易员',
    '10000000-0000-0000-0000-000000000002',
    '20000000-0000-0000-0000-000000000002',
    5000.00000000,
    5,
    FALSE,
    3,
    5,
    'SOL/USDT,BNB/USDT,AVAX/USDT',
    FALSE,
    TRUE,
    FALSE,
    TRUE,
    'default',
    TRUE,
    CURRENT_TIMESTAMP
);

-- 6. 插入用户信号源配置
INSERT INTO user_signal_sources (id, user_id, coin_pool_url, oi_top_url, created_at) VALUES
('40000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', 'https://api.example.com/coin-pool', 'https://api.example.com/oi-top', CURRENT_TIMESTAMP),
('40000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000002', '', '', CURRENT_TIMESTAMP);

-- 7. 插入系统配置
INSERT INTO system_config (key, value, updated_at) VALUES
('default_coins', '["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"]', CURRENT_TIMESTAMP),
('max_leverage', '10', CURRENT_TIMESTAMP),
('min_balance', '100', CURRENT_TIMESTAMP),
('trading_enabled', 'true', CURRENT_TIMESTAMP);

-- 8. 插入交易记录（示例）
INSERT INTO trade_records (
    id, trader_id, symbol, side, amount, price, leverage, 
    order_id, status, executed_at, created_at
) VALUES
(
    '50000000-0000-0000-0000-000000000001',
    '30000000-0000-0000-0000-000000000001',
    'BTC/USDT',
    'buy',
    0.10000000,
    45000.00000000,
    5,
    'binance-order-123456',
    'filled',
    CURRENT_TIMESTAMP - INTERVAL '1 hour',
    CURRENT_TIMESTAMP - INTERVAL '1 hour'
),
(
    '50000000-0000-0000-0000-000000000002',
    '30000000-0000-0000-0000-000000000001',
    'ETH/USDT',
    'sell',
    1.00000000,
    2500.00000000,
    5,
    'binance-order-123457',
    'filled',
    CURRENT_TIMESTAMP - INTERVAL '30 minutes',
    CURRENT_TIMESTAMP - INTERVAL '30 minutes'
);

-- 9. 插入决策日志（示例）
INSERT INTO decision_logs (
    id, trader_id, symbol, decision_state, decision_result, 
    reasoning, confidence, created_at
) VALUES
(
    '60000000-0000-0000-0000-000000000001',
    '30000000-0000-0000-0000-000000000001',
    'BTC/USDT',
    '{"signal_strength": 85, "trend": "bullish", "rsi": 65, "macd": "positive"}'::jsonb,
    'buy',
    'BTC突破关键阻力位，RSI显示强势，MACD金叉，建议做多',
    0.85,
    CURRENT_TIMESTAMP - INTERVAL '1 hour'
),
(
    '60000000-0000-0000-0000-000000000002',
    '30000000-0000-0000-0000-000000000001',
    'ETH/USDT',
    '{"signal_strength": 70, "trend": "bearish", "rsi": 35, "macd": "negative"}'::jsonb,
    'sell',
    'ETH出现回调信号，RSI超买回落，建议止盈',
    0.70,
    CURRENT_TIMESTAMP - INTERVAL '30 minutes'
);