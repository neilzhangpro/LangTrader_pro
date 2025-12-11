# LangTrader Pro

<div align="center">

**🚀 AI驱动的智能交易平台 | 让交易更简单，让生活更自由**

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/)
[![LangChain](https://img.shields.io/badge/LangChain-1.1.2+-green.svg)](https://www.langchain.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.0.4+-orange.svg)](https://github.com/langchain-ai/langgraph)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Official X: [@AIBTCAI](https://x.com/AIBTCAI)**

</div>

---

## 📖 项目简介

LangTrader Pro 是一个基于 **Python + LangChain + LangGraph + PostgreSQL** 架构的 AI 驱动智能交易平台。项目灵感来源于 Nofx，采用现代化的技术栈，专注于为加密货币交易提供安全、智能、可扩展的自动化交易解决方案。

### ✨ 核心特性

- 🤖 **多LLM支持**：集成 LangChain，支持数十种大语言模型
  - OpenAI API 兼容（OpenAI、Google、DeepSeek 等）
  - Anthropic Claude
  - **本地托管 LLM（Ollama）** - 充分保证金融交易数据安全性
- 🔄 **LangGraph 决策引擎**：基于状态图的智能决策流程
- 🏦 **多交易所支持**：
  - **Hyperliquid**（DEX）- 已集成
  - **CCXT 支持** - 可快速扩展到数十个 CEX 交易所（Binance、OKX、Gate.io 等）
- 📊 **实时市场监控**：WebSocket 实时数据流，支持多时间框架分析
- 🎯 **智能信号分析**：多维度技术指标计算（EMA、MACD、RSI、ATR 等）
- 💾 **PostgreSQL 持久化**：完整的交易记录、决策日志和配置管理
- 🔒 **企业级安全**：支持本地 LLM 部署，敏感数据不出本地

---

## 🏗️ 架构设计

### 技术栈

```
┌─────────────────────────────────────────────────────────┐
│                    LangTrader Platform                   │
├─────────────────────────────────────────────────────────┤
│  Frontend Layer (Future)                                │
├─────────────────────────────────────────────────────────┤
│  Decision Engine (LangGraph)                            │
│  ├── Coin Pool Node      (币种筛选)                     │
│  ├── Data Collector Node (数据收集)                     │
│  ├── Signal Analyzer Node(信号分析)                     │
│  └── AI Decision Node    (AI决策)                      │
├─────────────────────────────────────────────────────────┤
│  Service Layer                                          │
│  ├── Trader Manager      (交易员管理)                   │
│  ├── Exchange Service    (交易所服务)                   │
│  ├── Market Monitor      (市场监控)                     │
│  └── Prompt Service      (提示词服务)                   │
├─────────────────────────────────────────────────────────┤
│  LLM Integration (LangChain)                            │
│  ├── OpenAI API Compatible                             │
│  ├── Anthropic Claude                                   │
│  └── Ollama (Local) 🔒                                  │
├─────────────────────────────────────────────────────────┤
│  Exchange Integration                                   │
│  ├── Hyperliquid (DEX)                                 │
│  └── CCXT (CEX: Binance, OKX, Gate.io...)              │
├─────────────────────────────────────────────────────────┤
│  Data Layer (PostgreSQL)                                │
│  ├── User Management                                    │
│  ├── Trader Configuration                               │
│  ├── Trade Records                                      │
│  └── Decision Logs                                      │
└─────────────────────────────────────────────────────────┘
```

### 决策流程

```
START
  ↓
[Coin Pool] → 获取候选币种（信号源/配置）
  ↓
[Data Collector] → 收集市场数据（K线、价格）
  ↓
[Signal Analyzer] → 计算技术指标（EMA、MACD、RSI等）
  ↓
[AI Decision] → AI分析并生成交易决策
  ↓
END
```

---

## 🚀 快速开始

### 环境要求

- Python >= 3.13
- PostgreSQL >= 14
- (可选) Ollama - 用于本地 LLM 部署

### 安装步骤

1. **克隆仓库**

```bash
git clone https://github.com/yourusername/LangTrader_v0.2.0.git
cd LangTrader_v0.2.0
```

2. **安装依赖**

```bash
# 使用 uv (推荐)
uv sync

# 或使用 pip
pip install -e .
```

3. **配置环境变量**

创建 `.env` 文件：

```env
# 数据库配置
DATABASE=localhost
DATANAME=langtraders
DATAUSER=your_username
DATAPASS=your_password
DATEPORT=5432

# (可选) LLM API Keys
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
```

4. **初始化数据库**

```bash
# 使用提供的 SQL 脚本
psql -U your_username -d langtraders -f datbase/init.sql
```

5. **启动本地 LLM（可选，推荐用于生产环境）**

```bash
# 安装 Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 拉取模型（例如 Qwen）
ollama pull qwen2.5:7b

# 启动服务
ollama serve
```

6. **运行项目**

```bash
python main.py
```

---

## 📚 核心功能

### 1. 多 LLM 支持

LangTrader 通过 LangChain 统一接口支持多种 LLM：

```python
# OpenAI 兼容（包括 Google、DeepSeek 等）
provider: "openai"
model_name: "gpt-4"
base_url: "https://api.openai.com/v1"  # 可自定义

# Anthropic Claude
provider: "anthropic"
model_name: "claude-3-5-sonnet-20241022"

# 本地 Ollama（推荐用于生产）
provider: "ollama"
model_name: "qwen2.5:7b"
base_url: "http://localhost:11434"
```

### 2. 交易所集成

#### Hyperliquid (DEX)

```python
# 已完全集成
exchange_type: "DEX"
exchange_name: "hyperliquid"
wallet_address: "0x..."
secret_key: "your_private_key"
testnet: false
```

#### CCXT 支持的 CEX 交易所

通过 CCXT 可快速集成以下交易所：

- ✅ Binance (主网/测试网)
- ✅ OKX (主网)
- ✅ Gate.io (主网)
- 🔄 更多交易所可通过 CCXT 快速扩展

```python
exchange_type: "CEX"
exchange_name: "binance"  # 或 "okx", "gate.io"
api_key: "your_api_key"
secret_key: "your_secret_key"
testnet: false
```

### 3. LangGraph 决策引擎

决策引擎采用状态图模式，包含以下节点：

- **Coin Pool Node**: 从信号源或配置获取候选币种
- **Data Collector Node**: 实时收集市场数据（支持 WebSocket）
- **Signal Analyzer Node**: 计算技术指标（EMA、MACD、RSI、ATR）
- **AI Decision Node**: 基于多维度信息生成交易决策

### 4. 市场数据监控

- **实时 WebSocket 连接**：低延迟市场数据流
- **多时间框架支持**：3分钟、4小时 K线
- **自动重连机制**：保证数据连续性
- **缓存机制**：减少 API 调用

### 5. 智能信号分析

自动计算以下技术指标：

- **趋势指标**：EMA20、EMA50
- **动量指标**：MACD、RSI7、RSI14
- **波动率指标**：ATR
- **价格变化**：1小时、4小时涨跌幅

### 6. AI 决策系统

AI 决策节点会综合分析：

- 📊 账户余额和持仓情况
- 📈 实时市场数据（K线、价格）
- 🎯 技术指标信号
- 📉 历史趋势序列数据

生成结构化决策：
- 操作建议（买入/卖出/持有）
- 信心度评分（0-100）
- 决策理由
- 风险等级评估

---

## 🔧 配置说明

### 交易员配置

在数据库中配置交易员，主要字段：

```sql
-- 交易所配置
exchange_id: UUID
exchange_type: "CEX" | "DEX"
exchange_name: "binance" | "hyperliquid" | ...

-- AI 模型配置
ai_model_id: UUID
ai_model_provider: "openai" | "anthropic" | "ollama"
ai_model_name: "gpt-4" | "claude-3-5-sonnet" | "qwen2.5:7b"

-- 交易配置
trading_symbols: "BTC/USDT,ETH/USDT,SOL/USDT"
scan_interval_minutes: 3
btc_eth_leverage: 5
altcoin_leverage: 5

-- 信号源配置
use_coin_pool: true
use_oi_top: true
coin_pool_url: "https://..."
oi_top_url: "https://..."
```

### 提示词配置

支持自定义系统提示词，可在数据库中配置：

- 使用模板提示词
- 自定义提示词
- 覆盖基础提示词

---

## 📁 项目结构

```
LangTrader_v0.2.0/
├── config/                 # 配置模块
│   └── settings.py         # 数据库连接配置
├── datbase/               # 数据库脚本
│   ├── init.sql           # 初始化脚本
│   └── test_data.sql      # 测试数据
├── decision_engine/       # 决策引擎
│   ├── graph_builder.py   # LangGraph 图构建器
│   ├── state.py           # 状态定义
│   └── nodes/             # 决策节点
│       ├── coin_pool.py           # 币种池节点
│       ├── data_collector.py      # 数据收集节点
│       ├── signal_analyzer.py     # 信号分析节点
│       └── AI_decision.py         # AI决策节点
├── models/                # 数据模型
│   ├── trader.py          # 交易员模型
│   ├── exchange.py        # 交易所模型
│   ├── ai_model.py        # AI模型配置
│   └── ...
├── services/              # 业务服务
│   ├── trader_manager.py  # 交易员管理器
│   ├── ExchangeService.py # 交易所服务
│   ├── Auto_trader.py     # 自动交易服务
│   ├── market/            # 市场数据服务
│   │   ├── monitor.py     # WebSocket 监控
│   │   ├── indicators.py  # 技术指标计算
│   │   └── api_client.py  # REST API 客户端
│   └── trader/            # 交易接口
│       ├── interface.py   # 统一交易接口
│       └── hyperliquid_ccxt_trader.py  # Hyperliquid CCXT 实现
├── tests/                 # 测试文件
├── utils/                 # 工具类
│   └── logger.py          # 日志工具
├── main.py                # 入口文件
└── pyproject.toml         # 项目配置
```

---

## 🔒 安全特性

### 本地 LLM 支持

LangTrader 特别支持本地部署的 LLM（通过 Ollama），确保：

- ✅ **数据不出本地**：敏感交易数据不会发送到第三方 API
- ✅ **完全控制**：模型运行在您自己的服务器上
- ✅ **成本可控**：无需支付 API 调用费用
- ✅ **隐私保护**：交易策略和决策逻辑完全保密

### 推荐配置

```python
# 生产环境推荐使用本地 LLM
ai_model = {
    "provider": "ollama",
    "model_name": "qwen2.5:7b",  # 或 qwen2.5:14b, llama3.1:8b 等
    "base_url": "http://localhost:11434",
    "enabled": True
}
```

---

## 🧪 测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_auto_trader.py
pytest tests/test_database_connection.py
```

---

## 📊 监控与日志

日志文件位于 `logs/` 目录：

- `app.log` - 应用日志
- `error.log` - 错误日志

日志级别可通过配置调整。

---

## 🛣️ 路线图

### v0.2.0 (当前版本)
- ✅ LangChain 多 LLM 集成
- ✅ LangGraph 决策引擎
- ✅ Hyperliquid DEX 集成
- ✅ CCXT CEX 支持
- ✅ 实时市场监控
- ✅ AI 决策系统

### v0.3.0 (计划中)
- 🔄 风险管理系统
- 🔄 订单执行引擎
- 🔄 回测系统
- 🔄 Web Dashboard

### v0.4.0 (未来)
- 📋 多策略支持
- 📋 组合管理
- 📋 高级分析工具

---

## 🤝 贡献

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📝 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

---

## ⚠️ 免责声明

**重要提示**：加密货币交易存在高风险，可能导致资金损失。本项目仅供学习和研究使用。使用本软件进行交易的所有风险由用户自行承担。作者和贡献者不对任何交易损失负责。

---

## 📮 联系方式

- **Official X**: [@AIBTCAI](https://x.com/AIBTCAI)
- **Issues**: [GitHub Issues](https://github.com/yourusername/LangTrader_v0.2.0/issues)

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个 Star！**

Made with ❤️ by LangTrader Team

</div>
