# 股票投资系统设计文档

**项目名称**: Stock Investment System
**设计日期**: 2026-02-14
**版本**: v1.0

---

## 目录

1. [项目概述](#1-项目概述)
2. [系统架构](#2-系统架构)
3. [数据库设计](#3-数据库设计)
4. [核心功能模块](#4-核心功能模块)
5. [投资策略引擎](#5-投资策略引擎)
6. [历史回测模块](#6-历史回测模块)
7. [模拟交易模块](#7-模拟交易模块)
8. [数据管理模块](#8-数据管理模块)
9. [持仓导入模块](#9-持仓导入模块)
10. [前端界面设计](#10-前端界面设计)
11. [API接口设计](#11-api接口设计)
12. [部署架构](#12-部署架构)
13. [开发计划](#13-开发计划)

---

## 1. 项目概述

### 1.1 项目目标

构建一个完整的股票投资系统，支持：
- **投资目标管理**: 设定收益率目标、资金分配、仓位管理
- **股票筛选**: 基本面、技术面、行业分类、投资大佬推荐
- **投资策略**: 价值投资、趋势跟踪、网格交易、定投、自定义策略
- **历史回测**: 验证策略有效性，计算收益率、最大回撤、夏普比率等指标
- **模拟交易**: 生成交易信号、模拟账户验证策略

### 1.2 目标市场

- **美股市场**: 纳斯达克、纽交所
- **港股市场**: 香港交易所

### 1.3 数据来源

- **免费API**: Yahoo Finance、Alpha Vantage（行情、财务数据）
- **券商API**: 富途OpenAPI、老虎证券API（行情、账户同步）
- **大佬推荐**: 13F文件（SEC）、雪球大V推荐（网页爬取）、手动录入

### 1.4 核心需求

- **持仓导入**: 支持手动录入、Excel批量导入、券商API自动同步
- **筛选功能**: 基本面指标（PE、PB、ROE）+ 技术指标（均线、MACD、RSI）+ 行业分类 + 大佬推荐
- **策略类型**: 价值投资、趋势跟踪、网格交易、定投、自定义策略
- **回测验证**: 可配置时间范围的历史数据回测
- **交易模式**: 生成交易信号建议 + 模拟交易验证

---

## 2. 系统架构

### 2.1 技术栈

基于 `~/claude/finance` 项目的成功经验，采用相同技术栈：

**后端技术栈**:
- **语言**: Java 17
- **框架**: Spring Boot 3.2
- **数据库**: MySQL 8.0 @ 10.0.0.7:37719
- **ORM**: Spring Data JPA
- **认证**: JWT (JSON Web Token)
- **定时任务**: Spring Scheduler
- **构建工具**: Maven

**前端技术栈**:
- **框架**: Vue 3 (Composition API)
- **构建工具**: Vite
- **样式**: Tailwind CSS
- **图表**: Chart.js (股票图表、策略回测可视化)
- **状态管理**: Pinia
- **路由**: Vue Router
- **UI组件**: Radix Vue

**外部集成**:
- Yahoo Finance API (美股、港股行情数据)
- Alpha Vantage API (财务数据、技术指标)
- 富途OpenAPI / 老虎证券API (行情数据 + 模拟交易，可选)
- 雪球API / 东方财富爬虫 (投资大佬推荐)

**部署方式**:
- Docker Compose (本地开发、单机部署)
- Kubernetes + Helm (可选，云端部署)

### 2.2 核心服务划分

1. **用户服务** (`UserService`)
   - JWT认证、用户注册/登录
   - 多账户管理
   - 权限控制（用户只能访问自己的数据）

2. **数据采集服务** (`DataCollectionService`)
   - Yahoo Finance API集成（美股、港股行情）
   - Alpha Vantage API集成（财务数据）
   - 券商API集成（富途/老虎，行情+账户同步）
   - 网页爬虫（雪球、东方财富大V推荐）
   - 定时任务调度（每日收盘后更新数据）

3. **持仓管理服务** (`HoldingService`)
   - 账户导入（手动/Excel/API）
   - 持仓跟踪
   - 盈亏计算（浮动盈亏、已实现盈亏）

4. **筛选引擎服务** (`ScreeningService`)
   - 基本面筛选
   - 技术面筛选
   - 行业/市值/地域筛选
   - 大佬推荐筛选
   - 综合评分系统

5. **策略引擎服务** (`StrategyEngine`)
   - 策略配置管理
   - 策略执行引擎
   - 交易信号生成
   - 支持预设策略和自定义策略

6. **回测引擎服务** (`BacktestEngine`)
   - 历史数据回测
   - 性能指标计算
   - 回测结果存储

7. **模拟交易服务** (`SimulationService`)
   - 虚拟账户管理
   - 模拟订单执行
   - 持仓更新
   - 盈亏跟踪

### 2.3 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        前端 (Vue 3)                         │
│  Dashboard | 持仓管理 | 股票筛选 | 策略配置 | 回测 | 模拟交易 │
└─────────────────────────────────────────────────────────────┘
                              ▼
                         API Gateway
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   后端 (Spring Boot)                        │
├─────────────────────────────────────────────────────────────┤
│  认证服务 | 持仓服务 | 筛选服务 | 策略引擎 | 回测引擎 | 模拟交易 │
├─────────────────────────────────────────────────────────────┤
│                    数据采集服务 (Scheduler)                   │
│  Yahoo Finance | Alpha Vantage | 券商API | 网页爬虫         │
└─────────────────────────────────────────────────────────────┘
                              ▼
                       MySQL Database
```

---

## 3. 数据库设计

### 3.1 数据库配置

- **数据库名**: `stock`
- **主机**: 10.0.0.7:37719
- **用户**: austinxu
- **字符集**: utf8mb4_unicode_ci

### 3.2 核心数据表

#### 3.2.1 用户与账户

**users** - 用户表
```sql
CREATE TABLE users (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(50) UNIQUE NOT NULL,
  password VARCHAR(255) NOT NULL,  -- BCrypt加密
  email VARCHAR(100),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

**portfolios** - 投资组合/证券账户表
```sql
CREATE TABLE portfolios (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  name VARCHAR(100) NOT NULL,  -- 账户名称
  broker VARCHAR(50),  -- 券商（富途、老虎等）
  account_type VARCHAR(30),  -- 账户类型（CASH, MARGIN, IRA_TRADITIONAL, IRA_ROTH, 401K, TAXABLE）
  tax_deferred BOOLEAN DEFAULT FALSE,  -- 是否延税账户（401K、Traditional IRA为true）
  tax_free BOOLEAN DEFAULT FALSE,  -- 是否免税账户（Roth IRA为true）
  contribution_limit DECIMAL(15,2),  -- 年度供款上限（IRA: $7,000, 401K: $23,000）
  withdrawal_penalty BOOLEAN DEFAULT FALSE,  -- 提前取款是否有罚金（退休账户为true）
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);
```

**账户类型说明**:
- `CASH`: 现金账户（普通券商账户）
- `MARGIN`: 保证金账户（支持融资融券）
- `IRA_TRADITIONAL`: 传统IRA（延税，取款时缴税）
- `IRA_ROTH`: Roth IRA（税后供款，取款免税）
- `401K`: 401K退休账户（延税，雇主匹配）
- `TAXABLE`: 一般应税账户

**portfolio_goals** - 投资目标表
```sql
CREATE TABLE portfolio_goals (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  portfolio_id BIGINT NOT NULL,
  target_return_rate DECIMAL(10,4),  -- 目标年化收益率（如0.15表示15%）
  investment_period_months INT,  -- 投资周期（月）
  initial_capital DECIMAL(15,2),  -- 初始资金
  max_drawdown_limit DECIMAL(10,4),  -- 最大回撤限制
  max_position_per_stock DECIMAL(10,4),  -- 单只股票最大持仓比例
  max_position_per_sector DECIMAL(10,4),  -- 单个行业最大持仓比例
  cash_reserve_ratio DECIMAL(10,4),  -- 现金保留比例
  stop_loss_ratio DECIMAL(10,4),  -- 止损比例
  take_profit_ratio DECIMAL(10,4),  -- 止盈比例
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (portfolio_id) REFERENCES portfolios(id)
);
```

#### 3.2.2 股票数据

**stocks** - 股票基础信息表
```sql
CREATE TABLE stocks (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  symbol VARCHAR(20) UNIQUE NOT NULL,  -- 股票代码（AAPL, 0700.HK, SPY）
  name VARCHAR(200) NOT NULL,
  security_type VARCHAR(10) NOT NULL DEFAULT 'STOCK',  -- 证券类型（STOCK, ETF, INDEX）
  market VARCHAR(10) NOT NULL,  -- 市场（US, HK）
  exchange VARCHAR(50),  -- 交易所（NASDAQ, NYSE, HKEX）
  sector VARCHAR(100),  -- 行业
  industry VARCHAR(100),  -- 细分行业
  market_cap BIGINT,  -- 市值
  listing_date DATE,  -- 上市日期
  -- ETF专用字段
  etf_category VARCHAR(100),  -- ETF类别（Index, Sector, Thematic等）
  etf_holdings_count INT,  -- ETF持仓数量
  expense_ratio DECIMAL(10,4),  -- 费用率（ETF重要指标，如0.0003表示0.03%）
  aum BIGINT,  -- 资产管理规模（AUM，仅ETF）
  avg_volume BIGINT,  -- 日均成交量
  dividend_yield DECIMAL(10,4),  -- 分红率
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_market (market),
  INDEX idx_sector (sector),
  INDEX idx_security_type (security_type)
);
```

**证券类型说明**:
- `STOCK`: 个股（如AAPL、0700.HK）
- `ETF`: 交易型开放式指数基金（如SPY、QQQ）
- `INDEX`: 指数（用于对比基准）

**stock_prices** - 历史行情表（日K线）
```sql
CREATE TABLE stock_prices (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  stock_id BIGINT NOT NULL,
  trade_date DATE NOT NULL,
  open_price DECIMAL(15,4),
  high_price DECIMAL(15,4),
  low_price DECIMAL(15,4),
  close_price DECIMAL(15,4),
  volume BIGINT,
  adjusted_close DECIMAL(15,4),  -- 复权价格
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (stock_id) REFERENCES stocks(id),
  UNIQUE KEY uk_stock_date (stock_id, trade_date),
  INDEX idx_trade_date (trade_date)
);
```

**stock_fundamentals** - 财务数据表
```sql
CREATE TABLE stock_fundamentals (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  stock_id BIGINT NOT NULL,
  report_date DATE NOT NULL,  -- 财报日期
  pe_ratio DECIMAL(10,4),  -- 市盈率
  pb_ratio DECIMAL(10,4),  -- 市净率
  roe DECIMAL(10,4),  -- 净资产收益率
  revenue DECIMAL(18,2),  -- 营业收入
  net_income DECIMAL(18,2),  -- 净利润
  revenue_growth_rate DECIMAL(10,4),  -- 营收增长率
  debt_to_asset_ratio DECIMAL(10,4),  -- 负债率
  dividend_yield DECIMAL(10,4),  -- 股息率
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (stock_id) REFERENCES stocks(id),
  UNIQUE KEY uk_stock_report (stock_id, report_date)
);
```

**stock_technical_indicators** - 技术指标表
```sql
CREATE TABLE stock_technical_indicators (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  stock_id BIGINT NOT NULL,
  trade_date DATE NOT NULL,
  ma5 DECIMAL(15,4),  -- 5日均线
  ma10 DECIMAL(15,4),
  ma20 DECIMAL(15,4),
  ma60 DECIMAL(15,4),
  ma120 DECIMAL(15,4),
  ma250 DECIMAL(15,4),
  macd_dif DECIMAL(15,4),  -- MACD DIF
  macd_dea DECIMAL(15,4),  -- MACD DEA
  macd_histogram DECIMAL(15,4),  -- MACD柱状图
  rsi DECIMAL(10,4),  -- RSI指标
  bollinger_upper DECIMAL(15,4),  -- 布林带上轨
  bollinger_middle DECIMAL(15,4),  -- 布林带中轨
  bollinger_lower DECIMAL(15,4),  -- 布林带下轨
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (stock_id) REFERENCES stocks(id),
  UNIQUE KEY uk_stock_date (stock_id, trade_date),
  INDEX idx_trade_date (trade_date)
);
```

**etf_holdings** - ETF持仓明细表
```sql
CREATE TABLE etf_holdings (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  etf_id BIGINT NOT NULL,  -- ETF的stock_id
  holding_stock_id BIGINT NOT NULL,  -- 持仓股票的stock_id
  weight DECIMAL(10,4),  -- 权重（如0.05表示5%）
  shares BIGINT,  -- 持有股数
  market_value DECIMAL(18,2),  -- 市值
  as_of_date DATE,  -- 数据日期
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (etf_id) REFERENCES stocks(id),
  FOREIGN KEY (holding_stock_id) REFERENCES stocks(id),
  UNIQUE KEY uk_etf_holding_date (etf_id, holding_stock_id, as_of_date),
  INDEX idx_etf_id (etf_id),
  INDEX idx_as_of_date (as_of_date)
);
```

#### 3.2.3 持仓与交易

**holdings** - 当前持仓表
```sql
CREATE TABLE holdings (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  portfolio_id BIGINT NOT NULL,
  stock_id BIGINT NOT NULL,
  quantity DECIMAL(15,4) NOT NULL,  -- 持仓数量
  cost_price DECIMAL(15,4) NOT NULL,  -- 成本价
  import_source VARCHAR(20),  -- 导入来源（manual, excel, api）
  imported_at TIMESTAMP,  -- 导入时间
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (portfolio_id) REFERENCES portfolios(id),
  FOREIGN KEY (stock_id) REFERENCES stocks(id),
  UNIQUE KEY uk_portfolio_stock (portfolio_id, stock_id)
);
```

**transactions** - 交易记录表
```sql
CREATE TABLE transactions (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  portfolio_id BIGINT NOT NULL,
  stock_id BIGINT NOT NULL,
  transaction_type VARCHAR(10) NOT NULL,  -- BUY, SELL
  trade_date DATE NOT NULL,
  price DECIMAL(15,4) NOT NULL,
  quantity DECIMAL(15,4) NOT NULL,
  commission DECIMAL(15,2),  -- 手续费
  notes TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (portfolio_id) REFERENCES portfolios(id),
  FOREIGN KEY (stock_id) REFERENCES stocks(id),
  INDEX idx_trade_date (trade_date)
);
```

**simulated_accounts** - 模拟账户表
```sql
CREATE TABLE simulated_accounts (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  name VARCHAR(100) NOT NULL,
  initial_capital DECIMAL(15,2) NOT NULL,
  current_cash DECIMAL(15,2) NOT NULL,
  current_market_value DECIMAL(15,2),  -- 当前持仓市值
  total_assets DECIMAL(15,2),  -- 总资产（现金+市值）
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);
```

**simulated_holdings** - 模拟持仓表
```sql
CREATE TABLE simulated_holdings (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  simulated_account_id BIGINT NOT NULL,
  stock_id BIGINT NOT NULL,
  quantity DECIMAL(15,4) NOT NULL,
  cost_price DECIMAL(15,4) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (simulated_account_id) REFERENCES simulated_accounts(id),
  FOREIGN KEY (stock_id) REFERENCES stocks(id),
  UNIQUE KEY uk_account_stock (simulated_account_id, stock_id)
);
```

**simulated_transactions** - 模拟交易记录表
```sql
CREATE TABLE simulated_transactions (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  simulated_account_id BIGINT NOT NULL,
  stock_id BIGINT NOT NULL,
  transaction_type VARCHAR(10) NOT NULL,
  trade_date DATE NOT NULL,
  price DECIMAL(15,4) NOT NULL,
  quantity DECIMAL(15,4) NOT NULL,
  commission DECIMAL(15,2),
  signal_source VARCHAR(100),  -- 信号来源（策略ID或手动）
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (simulated_account_id) REFERENCES simulated_accounts(id),
  FOREIGN KEY (stock_id) REFERENCES stocks(id),
  INDEX idx_trade_date (trade_date)
);
```

#### 3.2.4 筛选与推荐

**screening_templates** - 筛选模板表
```sql
CREATE TABLE screening_templates (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  name VARCHAR(100) NOT NULL,
  description TEXT,
  criteria_json JSON NOT NULL,  -- 筛选条件（JSON格式）
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);
```

**guru_recommendations** - 大佬推荐表
```sql
CREATE TABLE guru_recommendations (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  stock_id BIGINT NOT NULL,
  source VARCHAR(50) NOT NULL,  -- 来源（13F, 雪球, 手动）
  recommender VARCHAR(100),  -- 推荐人（巴菲特、段永平等）
  recommendation_date DATE NOT NULL,
  reason TEXT,  -- 推荐理由
  weight DECIMAL(10,4),  -- 推荐权重
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (stock_id) REFERENCES stocks(id),
  INDEX idx_source (source),
  INDEX idx_date (recommendation_date)
);
```

**screening_results** - 筛选结果表（快照）
```sql
CREATE TABLE screening_results (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  template_id BIGINT,
  stock_id BIGINT NOT NULL,
  score DECIMAL(10,4),  -- 综合评分
  fundamental_score DECIMAL(10,4),
  technical_score DECIMAL(10,4),
  guru_score DECIMAL(10,4),
  sector_score DECIMAL(10,4),
  screening_date DATE NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (template_id) REFERENCES screening_templates(id),
  FOREIGN KEY (stock_id) REFERENCES stocks(id),
  INDEX idx_screening_date (screening_date),
  INDEX idx_score (score)
);
```

#### 3.2.5 策略与回测

**strategies** - 策略配置表
```sql
CREATE TABLE strategies (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  name VARCHAR(100) NOT NULL,
  strategy_type VARCHAR(50) NOT NULL,  -- VALUE, TREND, GRID, DCA, CUSTOM
  parameters_json JSON NOT NULL,  -- 策略参数（JSON格式）
  buy_conditions_json JSON,  -- 买入条件
  sell_conditions_json JSON,  -- 卖出条件
  is_active BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);
```

**backtest_jobs** - 回测任务表
```sql
CREATE TABLE backtest_jobs (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  strategy_id BIGINT NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  initial_capital DECIMAL(15,2) NOT NULL,
  status VARCHAR(20) NOT NULL,  -- PENDING, RUNNING, COMPLETED, FAILED
  progress INT DEFAULT 0,  -- 进度百分比
  error_message TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (strategy_id) REFERENCES strategies(id),
  INDEX idx_status (status)
);
```

**backtest_results** - 回测结果表
```sql
CREATE TABLE backtest_results (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  job_id BIGINT NOT NULL,
  total_return DECIMAL(10,4),  -- 总收益率
  annualized_return DECIMAL(10,4),  -- 年化收益率
  max_drawdown DECIMAL(10,4),  -- 最大回撤
  sharpe_ratio DECIMAL(10,4),  -- 夏普比率
  volatility DECIMAL(10,4),  -- 波动率
  win_rate DECIMAL(10,4),  -- 胜率
  profit_loss_ratio DECIMAL(10,4),  -- 盈亏比
  total_trades INT,  -- 总交易次数
  turnover_rate DECIMAL(10,4),  -- 换手率
  trades_json JSON,  -- 交易明细（JSON数组）
  daily_returns_json JSON,  -- 每日收益率（JSON数组）
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (job_id) REFERENCES backtest_jobs(id),
  UNIQUE KEY uk_job (job_id)
);
```

**trade_signals** - 交易信号表
```sql
CREATE TABLE trade_signals (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  strategy_id BIGINT NOT NULL,
  stock_id BIGINT NOT NULL,
  signal_type VARCHAR(10) NOT NULL,  -- BUY, SELL
  signal_strength DECIMAL(10,4),  -- 信号强度（0-1）
  price DECIMAL(15,4),  -- 建议价格
  quantity DECIMAL(15,4),  -- 建议数量
  reason TEXT,  -- 信号原因
  is_executed BOOLEAN DEFAULT FALSE,
  generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  executed_at TIMESTAMP,
  FOREIGN KEY (strategy_id) REFERENCES strategies(id),
  FOREIGN KEY (stock_id) REFERENCES stocks(id),
  INDEX idx_generated_at (generated_at),
  INDEX idx_is_executed (is_executed)
);
```

---

## 4. 核心功能模块

### 4.1 投资目标管理模块

**功能界面**:
- 目标设定表单：年化收益率目标、投资周期（月/年）、初始资金
- 资金分配配置：不同策略的资金占比（如：60%价值投资 + 40%趋势跟踪）
- 仓位控制规则：
  - 单只股票最大持仓比例（如不超过总资产的10%）
  - 单个行业最大持仓比例（如不超过30%）
  - 现金保留比例（如保留20%现金）
- 风险控制参数：
  - 最大回撤限制（触发警报或自动止损）
  - 单只股票止损线（如-15%）
  - 止盈目标（如+50%）

**后端实现**:
- `PortfolioGoalService`：CRUD投资目标
- 目标与账户关联（一个账户可以有多个目标）
- 目标达成度跟踪（当前收益 vs 目标收益）

### 4.2 股票筛选模块

**筛选器设计**:

1. **基本面筛选器**（多条件组合）：
   - PE市盈率：范围筛选（如 5-20）
   - PB市净率：范围筛选（如 < 3）
   - ROE净资产收益率：最小值（如 > 15%）
   - 营收增长率：最小值（如 > 20%）
   - 负债率：最大值（如 < 50%）

2. **技术指标筛选器**：
   - 均线系统：金叉/死叉信号（5日/10日/20日/60日均线）
   - MACD：金叉/死叉信号
   - RSI：超买（>70）/超卖（<30）
   - 成交量：放量/缩量（与历史平均值对比）

3. **行业板块筛选**：
   - 按行业分类（科技、金融、消费、医药等）
   - 按市值分类（大盘、中盘、小盘）
   - 按地域分类（美国、香港、中国概念股）

4. **大佬推荐追踪**：
   - 13F文件解析器（定期抓取巴菲特等机构的季度持仓报告）
   - 雪球大V推荐爬虫（抓取特定大V的推荐股票）
   - 手动录入界面（用户自行添加关注的投资者推荐）
   - 推荐权重设置（不同来源的推荐赋予不同权重）

**综合评分系统**:
- 多维度打分：基本面30分 + 技术面30分 + 大佬推荐20分 + 行业景气度20分
- 排序和过滤：按综合得分排序，推荐Top 50股票

**后端实现**:
- `StockScreeningService`：执行筛选逻辑
- `GuruRecommendationService`：管理大佬推荐数据
- 筛选结果缓存（避免重复计算）

### 4.3 ETF专用筛选模块

**ETF筛选条件**:

1. **费用相关**：
   - 费用率（Expense Ratio）：< 0.5%为优（被动指数ETF通常<0.1%）
   - 折溢价（Premium/Discount）：接近0为优

2. **规模和流动性**：
   - 资产管理规模（AUM）：> $100M（规模越大越不容易清盘）
   - 日均成交量：> 100,000股（流动性好，买卖价差小）

3. **跟踪表现**（Index ETF）：
   - 跟踪误差（Tracking Error）：越小越好
   - 跟踪偏离度（Tracking Difference）：实际收益 vs 指数收益

4. **持仓特征**：
   - 持仓数量：分散度指标（>50只为高分散）
   - 前10大持仓占比：< 50%为分散
   - 行业集中度：避免过度集中于单一行业

5. **收益指标**：
   - 分红率（Dividend Yield）：对于收益型ETF很重要
   - 历史收益率：1年、3年、5年表现

**ETF分类筛选**:
- **指数ETF**: SPY（标普500）、QQQ（纳斯达克100）、VTI（全市场）
- **行业ETF**: XLK（科技）、XLF（金融）、XLE（能源）
- **主题ETF**: ARKK（创新科技）、ICLN（清洁能源）
- **债券ETF**: AGG（综合债券）、TLT（长期国债）
- **商品ETF**: GLD（黄金）、USO（原油）

**后端实现**:
- `ETFScreeningService`：ETF专用筛选逻辑
- `ETFAnalysisService`：ETF持仓分析、跟踪误差计算

### 4.4 个股深度分析模块

筛选后，用户可以点击个股查看详细分析。

**个股详情页面组件**:

1. **公司基本信息**：
   - 公司简介、CEO、员工数、成立时间
   - 官网、行业、市值
   - 数据来源：Yahoo Finance API

2. **财务分析**：
   - **5年财务趋势图**：
     - 营收（Revenue）
     - 净利润（Net Income）
     - 自由现金流（Free Cash Flow）
   - **财务比率雷达图**：
     - 盈利能力：ROE、ROA、净利率
     - 偿债能力：流动比率、负债率
     - 运营能力：总资产周转率、应收账款周转率
   - **与行业平均值对比**：同行业PE、PB、ROE对比

3. **估值分析**：
   - **历史估值百分位**：
     - PE历史百分位（当前PE在过去5年的位置）
     - PB历史百分位
     - 显示：当前值、历史最低、历史最高、中位数
   - **同行业估值对比**：
     - 与同行业Top 5公司的PE、PB对比
   - **DCF估值模型**（可选高级功能）：
     - 基于自由现金流折现

4. **技术分析**：
   - **K线图**（Chart.js或TradingView组件）：
     - 支持多种周期（日K、周K、月K）
     - 支持叠加技术指标（均线、MACD、RSI、布林带）
   - **成交量分析**：成交量柱状图
   - **支撑位/阻力位**：基于历史高低点计算

5. **新闻和事件**：
   - **最新新闻**：
     - 爬取Yahoo Finance、Seeking Alpha等新闻
     - 显示标题、日期、来源
   - **财报发布时间线**：
     - 历史财报发布日期
     - 下一次财报预期日期
   - **分红派息记录**：
     - 历史分红金额、分红日期
     - 股息率趋势

6. **机构持仓**：
   - **前10大股东变化**：
     - 股东名称、持股比例、变化趋势
   - **机构持仓变化**：
     - 增持/减持趋势图
     - 数据来源：13F文件

**后端实现**:
- `StockDetailService`：整合各个数据源
- `NewsService`：新闻爬取和聚合
- `InstitutionalHoldingService`：13F数据解析和分析

**数据库扩展**:
```sql
-- 股票新闻表
CREATE TABLE stock_news (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  stock_id BIGINT NOT NULL,
  title VARCHAR(500),
  summary TEXT,
  url VARCHAR(500),
  source VARCHAR(100),
  published_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (stock_id) REFERENCES stocks(id),
  INDEX idx_published_at (published_at)
);

-- 机构持仓表
CREATE TABLE institutional_holdings (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  stock_id BIGINT NOT NULL,
  institution_name VARCHAR(200),
  shares BIGINT,
  market_value DECIMAL(18,2),
  percentage DECIMAL(10,4),
  report_date DATE,
  change_shares BIGINT,  -- 相比上期变化
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (stock_id) REFERENCES stocks(id),
  INDEX idx_report_date (report_date)
);
```

---

## 5. 投资策略引擎

### 5.1 策略类型设计

#### 5.1.1 价值投资策略

**核心理念**: 买入低估股票，长期持有等待价值回归

**买入条件**:
- PE < 15
- PB < 2
- ROE > 15%
- 股息率 > 3%

**持有周期**: 长期持有（至少6个月）

**卖出条件**:
- 估值过高（PE > 30）
- 基本面恶化（ROE连续2个季度下降超过20%）

**仓位管理**:
- 均匀分散，单只股票不超过10%
- 至少持有8-10只股票

#### 5.1.2 趋势跟踪策略

**核心理念**: 跟随市场趋势，顺势而为

**买入信号**:
- 金叉：5日均线上穿20日均线 + MACD金叉 + RSI > 50
- 突破：股价突破近期高点（20日内最高价）+ 成交量放大（超过20日平均成交量的150%）

**卖出信号**:
- 死叉：5日均线下穿20日均线 或 MACD死叉
- 止损：跌破买入价-10%

**仓位管理**:
- 趋势强度决定仓位（强趋势70%，弱趋势30%）
- 趋势强度计算：综合ADX指标和均线斜率

#### 5.1.3 网格交易策略

**适用场景**: 震荡市，选择波动率适中的股票

**网格设置**:
- 基准价：当前价格
- 网格间距：5%（可配置）
- 网格层数：上下各5层（可配置）

**交易规则**:
- 每下跌5%买入一格（固定金额）
- 每上涨5%卖出一格（回收本金+利润）

**资金管理**:
- 预留足够资金覆盖所有下行网格
- 单只股票网格资金不超过总资产的20%

#### 5.1.4 定投策略

**核心理念**: 定期定额买入，平滑成本

**定期买入**:
- 每月/每周固定时间
- 固定金额 或 固定股数

**智能定投（可选）**:
- 估值低位加大投入：PE < 历史平均PE的80%时，投入金额×1.5
- 高位减少投入：PE > 历史平均PE的120%时，投入金额×0.5

### 5.2 ETF专用投资策略

#### 5.2.1 核心-卫星策略 (Core-Satellite)

**核心理念**: 核心仓位配置低成本宽基ETF，卫星仓位配置高增长主题/行业ETF

**资金分配**:
- 核心仓位（70%）：低费率宽基指数ETF
  - SPY（标普500）或 VTI（全市场）
  - 长期持有，年化收益目标8-10%
- 卫星仓位（30%）：行业/主题ETF
  - 科技（QQQ）、清洁能源（ICLN）等
  - 根据行业景气度轮动

**再平衡**:
- 每季度检查仓位偏离
- 偏离超过5%时调仓

**适用人群**: 长期投资者，追求稳健收益

#### 5.2.2 行业轮动策略

**核心理念**: 根据经济周期和行业景气度，轮动配置行业ETF

**景气度指标**:
- 行业相对表现（行业ETF vs 大盘指数）
- 资金流入流出（ETF净流入额）
- 宏观经济指标（PMI、利率、GDP增速）

**买入信号**:
- 行业开始跑赢大盘（3个月相对收益 > 5%）
- 资金持续流入（连续4周净流入）

**卖出信号**:
- 行业开始跑输大盘（3个月相对收益 < -5%）
- 资金持续流出（连续4周净流出）

**轮动周期**: 每月评估一次

**适用人群**: 中期投资者，能够承受较高波动

#### 5.2.3 动量策略（ETF版）

**核心理念**: 选择近期表现最好的ETF持有，定期淘汰弱势ETF

**选股池**: 50-100只主流ETF

**排序规则**:
- 综合3个月、6个月收益率排序
- 选择Top 10进入组合

**调仓频率**: 每月调仓一次

**风险控制**:
- 单只ETF不超过15%
- 设置止损线（-15%）

**适用人群**: 追求高收益，能承受高波动

#### 5.2.4 定投策略（ETF版）

**核心理念**: 定期定额投资宽基指数ETF，长期复利

**定投标的**:
- 美股：VOO（Vanguard标普500）、VTI（Vanguard全市场）
- 港股：2800（盈富基金，追踪恒生指数）

**定投规则**:
- 频率：每月固定日期（如每月1日）
- 金额：固定金额（如$1000/月）

**增强策略**:
- 估值低位加倍投入（VIX > 30时）
- 估值高位减半投入（VIX < 15时）

**适用人群**: 新手投资者，追求长期稳定

#### 5.2.5 资产配置策略

**核心理念**: 股债商品多资产配置，降低组合波动

**配置比例**（可根据风险偏好调整）:
- **保守型**（30/60/10）:
  - 30% 股票ETF（SPY）
  - 60% 债券ETF（AGG）
  - 10% 商品ETF（GLD）
- **稳健型**（60/30/10）:
  - 60% 股票ETF
  - 30% 债券ETF
  - 10% 商品ETF
- **激进型**（80/15/5）:
  - 80% 股票ETF
  - 15% 债券ETF
  - 5% 商品ETF

**再平衡**:
- 每季度检查配置偏离
- 偏离超过5%时调仓回目标比例

**适用人群**: 所有投资者，根据年龄和风险承受能力选择

### 5.3 自定义策略引擎

**策略DSL（领域特定语言）设计**:

```json
{
  "name": "我的混合策略",
  "description": "结合基本面和技术面的自定义策略",
  "buyConditions": [
    {
      "type": "fundamental",
      "field": "pe",
      "operator": "<",
      "value": 20
    },
    {
      "type": "fundamental",
      "field": "roe",
      "operator": ">",
      "value": 0.15
    },
    {
      "type": "technical",
      "field": "ma5",
      "operator": ">",
      "field2": "ma20"
    },
    {
      "type": "technical",
      "field": "rsi",
      "operator": ">",
      "value": 30
    }
  ],
  "sellConditions": [
    {
      "type": "technical",
      "field": "ma5",
      "operator": "<",
      "field2": "ma20"
    },
    {
      "type": "price_change",
      "operator": "<",
      "value": -0.10
    }
  ],
  "positionSize": {
    "type": "fixed_percent",
    "value": 0.2
  }
}
```

**条件类型说明**:
- `fundamental`: 基本面条件（pe, pb, roe, revenue_growth, debt_ratio等）
- `technical`: 技术指标条件（ma5, ma20, macd_dif, rsi等）
- `price_change`: 价格变化条件（相对于买入价的涨跌幅）
- `operator`: 比较运算符（>, <, >=, <=, ==）

**仓位大小策略**:
- `fixed_percent`: 固定比例（每次买入占总资金的固定百分比）
- `kelly_criterion`: 凯利公式（根据胜率和盈亏比动态调整）
- `risk_parity`: 风险平价（根据波动率分配仓位）

**策略参数化**:
- 所有阈值可调整（PE阈值、均线周期、止损比例等）
- 保存为模板，可复用和分享

### 5.4 后端实现

**核心类**:
- `StrategyEngine`: 策略执行引擎核心
- `StrategyParser`: 解析策略JSON配置
- `SignalGenerator`: 生成买卖信号
- `PositionSizeCalculator`: 计算仓位大小
- `ETFStrategyEngine`: ETF专用策略引擎
- `AssetAllocationService`: 资产配置和再平衡服务

**策略组合**:
- 支持多策略并行运行
- 资金分配：不同策略分配不同比例的资金
- 信号冲突处理：同一股票多个策略产生不同信号时的优先级规则

**账户类型影响**:
- IRA/401K账户：优先配置长期价值投资策略（税收优惠最大化）
- 现金账户：可配置短期趋势跟踪策略
- 回测时考虑税收影响：
  - Roth IRA：取款免税，回测收益不扣税
  - Traditional IRA/401K：回测假设取款时税率（如25%）
  - 应税账户：短期资本利得税（持有<1年，税率高）vs 长期资本利得税（持有>1年，税率低）

---

## 6. 历史回测模块

### 6.1 回测流程

#### 6.1.1 参数配置

- **选择策略**: 单个策略或策略组合
- **时间范围**: 开始日期、结束日期（可配置，支持1年到15年+）
- **初始资金**: 回测起始资金
- **交易成本**:
  - 手续费率（美股典型值：0.003，港股：0.001）
  - 印花税（港股单边：0.001）
  - 滑点（市价单成交价偏差，典型值：0.001）
- **回测频率**: 日K、周K

#### 6.1.2 回测执行

按时间顺序遍历历史数据，每个交易日执行以下步骤：

1. **计算技术指标**:
   - 基于历史价格计算均线、MACD、RSI等

2. **执行策略逻辑**:
   - 遍历所有候选股票
   - 应用买入条件，生成买入信号
   - 应用卖出条件，生成卖出信号

3. **模拟订单执行**:
   - 按收盘价或次日开盘价成交（可配置）
   - 扣除交易成本（手续费+印花税+滑点）
   - 检查资金是否充足，仓位是否超限

4. **更新持仓和现金**:
   - 买入：减少现金，增加持仓
   - 卖出：增加现金，减少持仓
   - 记录交易明细

5. **记录每日净值**:
   - 净值 = 现金 + 所有持仓市值
   - 收益率 = (当前净值 - 初始资金) / 初始资金

#### 6.1.3 回测结果指标

**收益指标**:
- 总收益率 = (最终净值 - 初始资金) / 初始资金
- 年化收益率 = (总收益率 + 1) ^ (365 / 总天数) - 1
- 累计收益曲线（每日净值数组）

**风险指标**:
- **最大回撤 (MDD)**:
  - 定义：从历史最高点到最低点的最大跌幅
  - 计算：max((历史最高净值 - 当前净值) / 历史最高净值)
  - 发生时间：记录最大回撤的起止日期
- **波动率**:
  - 日收益率的标准差 × √252（年化）
- **夏普比率 (Sharpe Ratio)**:
  - 公式：(年化收益率 - 无风险利率) / 年化波动率
  - 无风险利率：使用3%（可配置）

**交易指标**:
- 总交易次数（买入+卖出次数）
- 胜率 = 盈利交易次数 / 总交易次数
- 盈亏比 = 平均盈利金额 / 平均亏损金额
- 换手率 = 总交易金额 / 平均账户净值
- 最长连续盈利次数 / 最长连续亏损次数

**对比基准**:
- 与大盘指数对比：
  - 美股：标普500 (^GSPC)
  - 港股：恒生指数 (^HSI)
- 与买入持有策略对比（Buy and Hold）

#### 6.1.4 可视化

- **净值曲线图**: 策略净值 vs 基准指数（双Y轴折线图）
- **回撤曲线图**: 显示回撤变化趋势
- **每月收益热力图**: 年份×月份的收益率矩阵
- **持仓变化时间线**: 展示买入/卖出节点
- **交易分布**:
  - 按月统计交易次数
  - 按股票统计交易频率
  - 盈利/亏损交易分布直方图

### 6.2 后端实现

**核心类**:
- `BacktestEngine`: 回测引擎核心，协调整个回测流程
- `BacktestJob`: 异步回测任务（长时间回测后台执行）
- `PerformanceAnalyzer`: 计算回测指标（收益率、夏普比率等）
- `BacktestResultRepository`: 结果存储

**性能优化**:
- 历史数据预加载（避免每次查询数据库）
- 批量计算技术指标
- 异步执行（避免阻塞API）
- 进度通知（WebSocket或轮询）

**结果存储**:
- 汇总数据：存储到 `backtest_results` 表
- 详细交易记录：存储为JSON（`trades_json`字段）
- 每日收益率：存储为JSON（`daily_returns_json`字段）

---

## 7. 模拟交易模块

### 7.1 虚拟账户

**功能**:
- 用户可创建多个模拟账户（测试不同策略）
- 独立于真实持仓
- 初始资金可配置（默认$100,000）

**账户信息**:
- 账户名称
- 初始资金
- 当前现金
- 当前持仓市值
- 总资产（现金+持仓市值）
- 总收益率

### 7.2 实时行情模拟

**数据源**:
- 基于真实市场数据（Yahoo Finance、券商API）
- 延迟：免费API通常延迟15分钟，券商API可能实时

**模拟交易时间**:
- 遵循真实交易时段：
  - 美股：周一至周五，美东时间 9:30-16:00
  - 港股：周一至周五，香港时间 9:30-12:00, 13:00-16:00
- 非交易时段订单排队，开盘后执行

### 7.3 交易执行

**自动执行**:
- 策略生成信号后自动下单
- 用户可配置是否启用自动执行

**手动执行**:
- 查看信号建议（待处理信号列表）
- 用户确认后执行

**订单类型**:
- **市价单**: 按当前价格立即成交
- **限价单**: 设定买入/卖出价格，价格达到时成交

**部分成交模拟**:
- 考虑流动性，大单可能部分成交
- 简化处理：小单全部成交，大单（超过日均成交量1%）分批成交

### 7.4 持仓跟踪

**实时更新**:
- 持仓市值 = 持仓数量 × 最新价格
- 每次价格更新时自动重新计算

**盈亏计算**:
- **持仓盈亏**: (当前价 - 成本价) × 持仓数量
- **持仓盈亏率**: (当前价 - 成本价) / 成本价
- **已实现盈亏**: 卖出时的盈亏（卖出价 - 成本价）× 卖出数量

**持仓明细**:
- 每只股票的持仓数量、成本价、当前价、盈亏、盈亏率、占比

### 7.5 交易日志

**记录内容**:
- 所有买卖操作
- 信号来源（哪个策略生成的）
- 执行时间、价格、数量
- 手续费明细
- 交易前后的现金和持仓变化

**日志查询**:
- 按日期范围查询
- 按股票筛选
- 按策略筛选

### 7.6 风险控制

**仓位检查**:
- 买入前检查是否超出设定的仓位限制
- 单只股票持仓不超过总资产的X%
- 单个行业持仓不超过总资产的Y%

**风险提醒**:
- 接近止损线时发出警告通知
- 回撤超过设定阈值时警报

### 7.7 后端实现

**核心类**:
- `SimulationAccountService`: 虚拟账户管理
- `SimulationTradingService`: 模拟交易执行
- `PositionTracker`: 持仓跟踪和盈亏计算
- `RiskController`: 风险控制检查

**与策略引擎集成**:
- 订阅策略引擎的交易信号
- 信号触发时自动或手动执行订单

---

## 8. 数据管理模块

### 8.1 数据采集

#### 8.1.1 股票基础信息

**数据源**: Yahoo Finance、券商API

**字段**:
- 股票代码、名称、交易所、行业、市值、上市日期

**更新频率**: 每周一次（周日晚）

**处理逻辑**:
- 新股上市时更新
- 股票退市时标记 `is_active = false`

#### 8.1.2 历史行情数据

**数据源**: Yahoo Finance、Alpha Vantage、券商API

**字段**:
- 日期、开盘价、最高价、最低价、收盘价、成交量、复权因子

**更新频率**: 每日收盘后更新

**数据补全**:
- 初次使用时回填历史数据（默认10年）
- 支持配置更长时间范围（15年+）

**增量更新**:
- 每日只更新最新交易日的数据
- 检查缺失日期并补全

#### 8.1.3 财务数据

**数据源**: Yahoo Finance、Alpha Vantage

**字段**:
- PE、PB、ROE、营收、净利润、营收增长率、负债率、股息率

**更新频率**: 季报发布后更新（每季度）

**处理逻辑**:
- 定期检查最新财报发布日期
- 解析财报数据并入库

#### 8.1.4 技术指标

**计算方式**: 基于历史价格实时计算或预计算存储

**指标列表**:
- 均线：5日、10日、20日、60日、120日、250日
- MACD：DIF(12,26), DEA(9), Histogram
- RSI：14日
- 布林带：20日

**更新频率**:
- 实时计算：每次查询时计算
- 预计算存储：每日收盘后批量计算并存储

**性能优化**:
- 热门股票采用实时计算
- 冷门股票采用预计算存储（减少查询时计算开销）

#### 8.1.5 大佬推荐数据

**13F文件**:
- 数据源：SEC EDGAR（https://www.sec.gov/edgar）
- 更新频率：每季度（季度结束后45天内提交）
- 解析逻辑：
  - 下载XML格式的13F文件
  - 解析持仓变化（新增、减持、增持）
  - 存储到 `guru_recommendations` 表

**雪球爬虫**:
- 目标：指定大V的推荐股票
- 更新频率：每日（晚上23:00）
- 爬取逻辑：
  - 使用Selenium或Jsoup解析雪球用户主页
  - 提取推荐股票和理由
  - 去重后存储

**手动录入**:
- 用户界面直接添加
- 字段：股票代码、推荐人、推荐日期、推荐理由

### 8.2 定时任务调度

**Spring Scheduler配置**:

```java
@Scheduled(cron = "0 0 21 * * ?")  // 每日21:00（美股收盘后）
public void updateUSStockData() {
    // 更新美股行情
    // 计算技术指标
}

@Scheduled(cron = "0 0 18 * * ?")  // 每日18:00（港股收盘后）
public void updateHKStockData() {
    // 更新港股行情
    // 计算技术指标
}

@Scheduled(cron = "0 0 22 * * ?")  // 每日22:00
public void generateTradingSignals() {
    // 执行所有启用的策略
    // 生成交易信号
}

@Scheduled(cron = "0 0 23 * * ?")  // 每日23:00
public void crawlGuruRecommendations() {
    // 雪球大V推荐爬取
}

@Scheduled(cron = "0 0 0 * * SUN")  // 每周日00:00
public void updateStockBasicInfo() {
    // 更新股票基础信息
}

@Scheduled(cron = "0 0 0 1 */3 *")  // 每季度第一天00:00
public void updateFinancialData() {
    // 抓取13F文件
    // 更新财务数据
}
```

### 8.3 数据缓存

**Redis缓存（可选）**:

**缓存内容**:
- 热点股票的实时行情（TTL: 1小时）
- 筛选结果（TTL: 1天）
- API调用结果（TTL: 根据API限流策略）

**缓存策略**:
- Cache-Aside模式：
  - 读：先查缓存，未命中则查数据库并写入缓存
  - 写：更新数据库，然后删除缓存

**缓存过期**:
- 行情数据：1小时
- 筛选结果：1天
- 财务数据：1季度

### 8.4 API限流

**Yahoo Finance**:
- 免费版限制：2000次请求/小时/IP
- 策略：请求队列 + 限流（最多30次/分钟）

**Alpha Vantage**:
- 免费版限制：5次请求/分钟，500次请求/天
- 策略：请求队列 + 重试机制（失败后延迟重试）

**限流实现**:
- 使用 `RateLimiter`（Guava）或 Spring Cloud Gateway
- 请求超限时排队等待
- 超时失败时记录日志并告警

### 8.5 后端实现

**核心类**:
- `DataCollectionService`: 数据采集入口，协调各个数据源
- `YahooFinanceClient`: Yahoo Finance API封装
- `AlphaVantageClient`: Alpha Vantage API封装
- `FutuAPIClient` / `TigerAPIClient`: 券商API封装
- `TechnicalIndicatorCalculator`: 技术指标计算工具类
- `ScheduledTasksService`: 定时任务服务
- `GuruRecommendationCrawler`: 大佬推荐爬虫

**异常处理**:
- API调用失败：重试3次，失败后记录日志
- 数据解析错误：跳过该记录，记录错误日志
- 网络超时：延长超时时间或降低并发度

---

## 9. 持仓导入模块

### 9.1 导入方式

#### 9.1.1 手动录入

**表单界面**:
- 选择账户（下拉菜单）
- 输入股票代码（支持自动补全）
- 输入数量（正整数或小数）
- 输入成本价（正数）

**批量添加**:
- 支持在同一页面一次录入多只股票
- 表单验证：检查股票代码有效性、数量>0、成本价>0

**提交后处理**:
- 检查股票代码是否存在于数据库，不存在则自动从API获取并创建
- 插入 `holdings` 表
- 设置 `import_source = 'manual'`

#### 9.1.2 Excel/CSV导入

**模板下载**:
- 提供标准Excel模板
- 列定义：
  - 账户名称（或账户ID）
  - 股票代码
  - 数量
  - 成本价

**文件上传**:
- 前端选择Excel/CSV文件
- 后端使用Apache POI（Excel）或OpenCSV（CSV）解析

**预览和验证**:
- 解析文件后显示预览表格
- 验证逻辑：
  - 检查股票代码有效性（查询数据库或API）
  - 检查数量和成本价格式（必须为正数）
  - 标记错误行（红色高亮）
- 用户确认后导入

**导入逻辑**:
- 有效行插入数据库
- 如果持仓已存在：
  - 询问用户：覆盖（替换数量和成本价）还是累加（增加数量，重新计算平均成本价）
- 设置 `import_source = 'excel'`

#### 9.1.3 券商API同步

**支持的券商**:
- 富途证券（Futu OpenAPI）
- 老虎证券（Tiger Trade API）

**OAuth授权流程**:

1. 用户在系统中添加券商账户配置
2. 点击"授权"按钮，跳转到券商授权页面
3. 用户登录券商账户并授权
4. 回调到系统，获取访问令牌（Access Token）
5. 存储令牌到数据库（加密存储）

**自动同步**:
- 定期（每小时）从券商API拉取最新持仓
- 对比变化：
  - 新买入：新增持仓记录
  - 卖出：减少持仓数量或删除持仓
  - 持仓数量变化：更新数量和成本价
- 自动更新本地持仓数据
- 设置 `import_source = 'api'`

**手动同步**:
- 用户点击"立即同步"按钮
- 立即触发同步任务

### 9.2 数据映射

**股票代码标准化**:
- 美股：AAPL（Yahoo Finance格式）
- 港股：0700.HK（Yahoo Finance格式）
- 券商API返回的代码格式可能不同，需要映射转换：
  - 富途：HK.00700 → 0700.HK
  - 老虎：00700 → 0700.HK

**映射表**:
```java
Map<String, String> symbolMapping = Map.of(
    "HK.00700", "0700.HK",
    "HK.09988", "9988.HK",
    "US.AAPL", "AAPL"
);
```

### 9.3 导入后处理

**计算当前市值**:
- 持仓市值 = 持仓数量 × 最新价格
- 从 `stock_prices` 表获取最新收盘价

**计算浮动盈亏**:
- 浮动盈亏 = (当前价 - 成本价) × 数量
- 浮动盈亏率 = (当前价 - 成本价) / 成本价

**计算持仓占比**:
- 单只股票占比 = 单只股票市值 / 总资产
- 总资产 = 所有持仓市值之和

### 9.4 后端实现

**核心类**:
- `HoldingImportService`: 持仓导入服务，协调各种导入方式
- `ExcelParser`: Excel文件解析工具
- `FutuAPIClient`: 富途OpenAPI集成
- `TigerAPIClient`: 老虎证券API集成
- `HoldingSyncScheduler`: 定时同步任务

**API集成示例（富途OpenAPI）**:
```java
@Service
public class FutuAPIClient {
    public List<HoldingDTO> fetchHoldings(String accessToken) {
        // 调用富途API获取持仓
        // 解析响应并转换为标准格式
        // 返回持仓列表
    }
}
```

---

## 10. 前端界面设计

基于 `~/claude/finance` 项目的界面风格，采用现代化、简洁的设计。

### 10.1 页面结构

#### 10.1.1 首页/Dashboard

**布局**:
- 顶部：总资产、总收益、总收益率卡片
- 左侧：投资目标达成度（进度条）
- 中部：近期交易信号列表（待处理的买卖建议）
- 右侧：持仓概览（Top 10持仓，饼图）
- 底部：账户净值曲线图（近30天）

**组件**:
- 卡片组件（总资产、收益等）
- 进度条（目标达成度）
- 表格（交易信号）
- 饼图（持仓分布）
- 折线图（净值曲线）

#### 10.1.2 持仓管理

**布局**:
- 顶部：
  - 账户切换下拉菜单（显示账户名称 + 账户类型标签）
  - 账户类型徽章：
    - IRA账户显示"IRA"徽章（蓝色）
    - 401K账户显示"401K"徽章（绿色）
    - 应税账户显示"TAXABLE"徽章（灰色）
  - 导入按钮（手动、Excel、API同步）
  - "新建账户"按钮
- 中部：当前持仓表格
  - 列：证券类型标签、股票代码、名称、数量、成本价、当前价、盈亏、盈亏率、占比
  - 证券类型标签：个股（无标签）、ETF（橙色"ETF"标签）
  - 支持排序（按盈亏率、占比等）
  - 支持筛选：显示全部/仅个股/仅ETF
- 底部：持仓分析图表
  - 饼图：行业分布（个股按行业分组，ETF按类别分组）
  - 饼图：市场分布（美股/港股）
  - 饼图：证券类型分布（个股 vs ETF占比）

**账户信息卡片**（选中账户后显示）:
- 账户类型信息
- 税收优惠提示（如IRA显示"延税账户，59.5岁前取款有10%罚金"）
- 年度供款限额和已用额度（IRA/401K）

**交互**:
- 点击"新建账户"弹出表单，选择账户类型（含401K、IRA选项）
- 点击"导入"按钮弹出模态框，选择导入方式
- 点击股票代码跳转到详情页（个股详情页 或 ETF详情页）

#### 10.1.3 股票筛选

**顶部标签页**:
- "个股筛选" 标签页
- "ETF筛选" 标签页

**个股筛选布局**:
- 左侧：筛选条件配置面板
  - 基本面指标（PE、PB、ROE等，范围输入）
  - 技术指标（均线、MACD、RSI等，下拉选择）
  - 行业板块（多选）
  - 大佬推荐来源（多选）
  - "保存模板"按钮
- 右侧：筛选结果表格
  - 列：股票代码、名称、综合评分、PE、PB、ROE、技术信号
  - 支持排序和分页

**ETF筛选布局**:
- 左侧：ETF筛选条件
  - 费用率范围（<0.1%, 0.1-0.5%, >0.5%）
  - 资产规模（>$100M, >$1B）
  - ETF类别（指数、行业、主题、债券、商品）
  - 分红率范围
  - 流动性（日均成交量）
- 右侧：筛选结果表格
  - 列：ETF代码、名称、类别、费用率、规模、分红率、1年收益率
  - 支持排序和分页

**交互**:
- 调整筛选条件后点击"筛选"按钮
- 点击股票代码查看详情：
  - 个股：弹出个股详情抽屉（财务分析、估值分析、技术图表）
  - ETF：弹出ETF详情抽屉（持仓明细、行业分布、跟踪误差）

#### 10.1.4 投资策略

**布局**:
- 顶部：策略列表（卡片布局）
  - 每个卡片显示：策略名称、类型、状态（启用/停用）、最近信号数
  - "新建策略"按钮
- 点击策略卡片展开详情：
  - 策略参数（只读或可编辑）
  - 买卖条件（列表展示）
  - "编辑"/"删除"/"启用"/"停用"按钮

**新建/编辑策略界面**:
- 选择证券类型：个股策略 / ETF策略
- 选择策略类型：
  - 个股：价值投资、趋势跟踪、网格交易、定投、自定义
  - ETF：核心-卫星、行业轮动、动量策略、定投、资产配置、自定义
- 预设策略：调整参数（PE阈值、均线周期、资产配置比例等）
- 自定义策略：
  - 可视化条件配置器（拖拽式）
  - 或 JSON编辑器（高级用户）

#### 10.1.5 历史回测

**布局**:
- 顶部：回测配置表单
  - 选择策略（下拉菜单）
  - 时间范围（日期选择器）
  - 初始资金（数字输入）
  - "启动回测"按钮
- 中部：回测任务列表
  - 显示历史回测记录（策略名、时间范围、状态、收益率）
  - 点击查看详情
- 底部：回测详情页（点击任务后展开）
  - 收益指标卡片（总收益率、年化收益率、最大回撤、夏普比率）
  - 净值曲线图（策略 vs 基准）
  - 回撤曲线图
  - 交易统计（胜率、盈亏比、交易次数）
  - 交易明细表格（分页）

#### 10.1.6 模拟交易

**布局**:
- 顶部：虚拟账户列表（卡片布局）+ "创建新账户"按钮
- 点击账户卡片展开详情：
  - 账户信息：余额、总资产、收益率
  - 持仓列表（表格）
  - 待执行信号列表（策略生成的买卖建议）
  - "手动下单"按钮
- 底部：交易历史记录（表格，分页）

**手动下单界面**:
- 模态框：
  - 选择股票（自动补全）
  - 买入/卖出（单选）
  - 数量（数字输入）
  - 订单类型（市价/限价）
  - 限价（仅限价单需要）
  - "提交订单"按钮

#### 10.1.7 数据管理

**布局**:
- 股票列表（表格）
  - 列：股票代码、名称、市场、行业、最后更新时间
  - 支持搜索（按代码或名称）
  - 支持分页
- 数据更新状态面板
  - 显示最后更新时间
  - "手动更新"按钮（触发数据抓取）
- 大佬推荐管理（表格）
  - 列：推荐人、来源、股票、日期、理由
  - "添加推荐"按钮

#### 10.1.8 设置

**布局**:
- 标签页布局（Tabs）
  - **账户设置**：
    - 券商API配置（富途、老虎）
    - 授权管理（查看/撤销授权）
  - **投资目标设置**：
    - 收益率目标、时间周期、风险控制参数（表单）
  - **通知设置**：
    - 交易信号通知（启用/停用）
    - 通知方式（邮件、短信、推送）
  - **数据源配置**：
    - Yahoo Finance API密钥（可选）
    - Alpha Vantage API密钥

### 10.2 UI组件（复用finance项目）

**组件库**:
- Tailwind CSS（样式）
- Radix Vue（无障碍UI组件）
- Lucide Vue（图标）
- Chart.js（图表）
- Vue Router（路由）
- Pinia（状态管理）

**响应式设计**:
- 移动端友好（Tailwind响应式断点）
- 平板和桌面端优化

---

## 11. API接口设计

### 11.1 认证接口

**POST /api/auth/register**
- 描述：用户注册
- 请求体：`{ username, password, email }`
- 响应：`{ message, userId }`

**POST /api/auth/login**
- 描述：用户登录
- 请求体：`{ username, password }`
- 响应：`{ token, refreshToken, user }`

**POST /api/auth/refresh**
- 描述：刷新JWT token
- 请求体：`{ refreshToken }`
- 响应：`{ token, refreshToken }`

### 11.2 持仓管理

**GET /api/portfolios**
- 描述：获取当前用户的账户列表
- 响应：`[ { id, name, broker, accountType, isActive } ]`

**POST /api/portfolios**
- 描述：创建新账户
- 请求体：`{ name, broker, accountType, taxDeferred?, taxFree?, contributionLimit?, withdrawalPenalty? }`
- accountType可选值：CASH, MARGIN, IRA_TRADITIONAL, IRA_ROTH, 401K, TAXABLE
- 响应：`{ id, message }`

**GET /api/portfolios/{id}**
- 描述：获取账户详情（含税收信息）
- 响应：`{ id, name, broker, accountType, taxDeferred, taxFree, contributionLimit, withdrawalPenalty, currentContribution }`

**GET /api/portfolios/{id}/holdings**
- 描述：获取指定账户的持仓列表
- 查询参数：`?securityType=STOCK|ETF|ALL` （筛选证券类型，默认ALL）
- 响应：`[ { id, stockSymbol, stockName, securityType, quantity, costPrice, currentPrice, profit, profitRate, percentage } ]`

**POST /api/holdings/import/manual**
- 描述：手动录入持仓
- 请求体：`{ portfolioId, stockSymbol, quantity, costPrice }`
- 响应：`{ message }`

**POST /api/holdings/import/excel**
- 描述：Excel批量导入
- 请求体：`multipart/form-data (file)`
- 响应：`{ validRows, invalidRows, message }`

**POST /api/holdings/sync**
- 描述：券商API同步持仓
- 请求体：`{ portfolioId }`
- 响应：`{ syncedCount, message }`

### 11.3 股票筛选

**POST /api/screening/execute**
- 描述：执行个股筛选
- 请求体：`{ fundamentalCriteria: {...}, technicalCriteria: {...}, sectors: [], guruSources: [] }`
- 响应：`[ { stockId, symbol, name, score, fundamentalScore, technicalScore, guruScore, sectorScore } ]`

**POST /api/screening/etf/execute**
- 描述：执行ETF筛选
- 请求体：`{ expenseRatioMax, aumMin, categories: [], dividendYieldMin, avgVolumeMin }`
- 响应：`[ { etfId, symbol, name, category, expenseRatio, aum, dividendYield, oneYearReturn } ]`

**GET /api/screening/templates**
- 描述：获取筛选模板列表
- 查询参数：`?securityType=STOCK|ETF` （筛选证券类型）
- 响应：`[ { id, name, description, securityType, criteriaJson } ]`

**POST /api/screening/templates**
- 描述：保存筛选模板
- 请求体：`{ name, description, securityType, criteriaJson }`
- 响应：`{ id, message }`

**GET /api/guru-recommendations**
- 描述：获取大佬推荐列表
- 查询参数：`?source=13F&recommender=巴菲特`
- 响应：`[ { id, stockSymbol, stockName, source, recommender, date, reason } ]`

**GET /api/stocks/{symbol}/detail**
- 描述：获取个股详情（深度分析）
- 响应：`{ basicInfo, financialData, valuationAnalysis, technicalAnalysis, news, institutionalHoldings }`

**GET /api/etfs/{symbol}/detail**
- 描述：获取ETF详情
- 响应：`{ basicInfo, holdings, sectorAllocation, performance, trackingError }`

**GET /api/etfs/{symbol}/holdings**
- 描述：获取ETF持仓明细
- 响应：`[ { stockSymbol, stockName, weight, shares, marketValue } ]`

### 11.4 投资策略

**GET /api/strategies**
- 描述：获取策略列表
- 响应：`[ { id, name, type, parametersJson, isActive } ]`

**POST /api/strategies**
- 描述：创建策略
- 请求体：`{ name, type, parametersJson, buyConditionsJson, sellConditionsJson }`
- 响应：`{ id, message }`

**PUT /api/strategies/{id}**
- 描述：更新策略
- 请求体：`{ name, parametersJson, buyConditionsJson, sellConditionsJson }`
- 响应：`{ message }`

**DELETE /api/strategies/{id}**
- 描述：删除策略
- 响应：`{ message }`

**POST /api/strategies/{id}/activate**
- 描述：启用/停用策略
- 请求体：`{ isActive: true/false }`
- 响应：`{ message }`

**GET /api/signals**
- 描述：获取交易信号列表
- 查询参数：`?strategyId=1&isExecuted=false`
- 响应：`[ { id, strategyName, stockSymbol, signalType, signalStrength, price, quantity, reason, generatedAt } ]`

### 11.5 历史回测

**POST /api/backtest/start**
- 描述：启动回测任务
- 请求体：`{ strategyId, startDate, endDate, initialCapital }`
- 响应：`{ jobId, message }`

**GET /api/backtest/jobs**
- 描述：获取回测任务列表
- 响应：`[ { id, strategyName, startDate, endDate, status, progress, createdAt } ]`

**GET /api/backtest/jobs/{id}**
- 描述：获取回测结果详情
- 响应：`{ jobId, totalReturn, annualizedReturn, maxDrawdown, sharpeRatio, winRate, profitLossRatio, totalTrades, tradesJson, dailyReturnsJson }`

**DELETE /api/backtest/jobs/{id}**
- 描述：删除回测记录
- 响应：`{ message }`

### 11.6 模拟交易

**GET /api/simulation/accounts**
- 描述：获取模拟账户列表
- 响应：`[ { id, name, initialCapital, currentCash, currentMarketValue, totalAssets } ]`

**POST /api/simulation/accounts**
- 描述：创建模拟账户
- 请求体：`{ name, initialCapital }`
- 响应：`{ id, message }`

**GET /api/simulation/accounts/{id}/holdings**
- 描述：获取模拟持仓
- 响应：`[ { stockSymbol, stockName, quantity, costPrice, currentPrice, profit, profitRate } ]`

**POST /api/simulation/orders**
- 描述：下模拟订单
- 请求体：`{ simulatedAccountId, stockSymbol, transactionType, orderType, quantity, limitPrice? }`
- 响应：`{ orderId, message }`

**GET /api/simulation/orders**
- 描述：获取交易历史
- 查询参数：`?accountId=1&startDate=2024-01-01&endDate=2024-12-31`
- 响应：`[ { id, stockSymbol, transactionType, tradeDate, price, quantity, commission, signalSource } ]`

### 11.7 数据管理

**GET /api/stocks**
- 描述：获取股票列表（支持搜索、分页）
- 查询参数：`?search=AAPL&market=US&page=1&pageSize=50`
- 响应：`{ stocks: [...], totalCount, page, pageSize }`

**GET /api/stocks/{symbol}**
- 描述：获取股票详情
- 响应：`{ symbol, name, market, sector, industry, marketCap, latestPrice, pe, pb, roe }`

**POST /api/data/update**
- 描述：手动触发数据更新
- 请求体：`{ dataType: "prices" | "fundamentals" | "all" }`
- 响应：`{ message, taskId }`

**GET /api/data/status**
- 描述：获取数据更新状态
- 响应：`{ lastUpdateTime, nextUpdateTime, isUpdating }`

---

## 12. 部署架构

### 12.1 本地开发环境

**后端**:
- Spring Boot应用
- 端口：8080
- 启动命令：`./backend/start.sh` 或 `mvn spring-boot:run`

**前端**:
- Vite开发服务器
- 端口：3000
- 启动命令：`npm run dev`

**数据库**:
- MySQL 8.0 @ 10.0.0.7:37719
- 数据库名：stock

**环境变量**:
- 配置文件：`backend/.env`

### 12.2 Docker Compose部署

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    container_name: stock-backend
    ports:
      - "8080:8080"
    environment:
      - DB_HOST=10.0.0.7
      - DB_PORT=37719
      - DB_NAME=stock
      - DB_USER=austinxu
      - DB_PASSWORD=helloworld
      - JWT_SECRET=${JWT_SECRET}
    restart: unless-stopped

  frontend:
    build: ./frontend
    container_name: stock-frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
    restart: unless-stopped

  # 定时任务服务（可选，或集成在backend中）
  scheduler:
    build: ./backend
    container_name: stock-scheduler
    environment:
      - DB_HOST=10.0.0.7
      - DB_PORT=37719
      - DB_NAME=stock
      - DB_USER=austinxu
      - DB_PASSWORD=helloworld
    command: ["java", "-jar", "app.jar", "--scheduler.enabled=true"]
    restart: unless-stopped
```

**启动命令**:
```bash
docker-compose up -d
```

### 12.3 Kubernetes部署（可选）

**Helm Chart配置**:

目录结构：
```
k8s/
├── Chart.yaml
├── values.yaml
└── templates/
    ├── backend-deployment.yaml
    ├── backend-service.yaml
    ├── frontend-deployment.yaml
    ├── frontend-service.yaml
    ├── ingress.yaml
    └── configmap.yaml
```

**部署命令**:
```bash
cd k8s
helm install stock-app .
```

**环境变量**:
- 通过ConfigMap和Secret管理
- 敏感信息（数据库密码、JWT密钥）使用Secret

---

## 13. 开发计划

### 13.1 开发阶段

#### 第一阶段：基础框架（2-3周）

**任务**:
- [x] 数据库设计和建表
- [x] 环境配置（backend/.env）
- [ ] 项目初始化（Spring Boot + Vue 3）
  - [ ] 创建Spring Boot项目（Maven）
  - [ ] 创建Vue 3项目（Vite）
  - [ ] 配置Tailwind CSS
- [ ] JWT认证系统
  - [ ] 用户注册/登录接口
  - [ ] JWT token生成和验证
  - [ ] 权限拦截器
- [ ] 基础CRUD接口
  - [ ] 用户管理
  - [ ] 账户管理

**交付物**:
- 可运行的前后端基础框架
- 用户可以注册、登录、创建账户

#### 第二阶段：数据采集（2周）

**任务**:
- [ ] Yahoo Finance API集成
  - [ ] 股票基础信息采集
  - [ ] 历史行情数据采集
- [ ] Alpha Vantage API集成（可选）
  - [ ] 财务数据采集
- [ ] 定时任务调度
  - [ ] 每日行情更新
  - [ ] 技术指标计算
- [ ] 数据存储和查询优化

**交付物**:
- 能够自动抓取美股、港股的历史行情数据
- 定时任务正常运行

#### 第三阶段：持仓管理（1周）

**任务**:
- [ ] 持仓导入
  - [ ] 手动录入界面
  - [ ] Excel批量导入
  - [ ] 券商API集成（可选，富途/老虎）
- [ ] 持仓展示
  - [ ] 持仓列表（表格）
  - [ ] 盈亏计算
  - [ ] 持仓分析图表（饼图：行业分布、市场分布）

**交付物**:
- 用户可以导入持仓（手动、Excel）
- 查看持仓详情和盈亏

#### 第四阶段：股票筛选（2-3周）

**任务**:
- [ ] 个股筛选器
  - [ ] 基本面筛选（PE、PB、ROE等）
  - [ ] 技术指标筛选（均线、MACD、RSI）
- [ ] ETF筛选器
  - [ ] 费用率、规模、分红率筛选
  - [ ] ETF类别筛选
- [ ] 大佬推荐爬取
  - [ ] 13F文件解析
  - [ ] 雪球大V推荐爬虫
  - [ ] 手动录入界面
- [ ] 综合评分系统
- [ ] 筛选结果展示
- [ ] 个股深度分析页面
  - [ ] 财务分析图表
  - [ ] 估值分析
  - [ ] 新闻和机构持仓
- [ ] ETF详情页面
  - [ ] 持仓明细
  - [ ] 行业分布
  - [ ] 跟踪误差

**交付物**:
- 用户可以筛选个股和ETF
- 查看详细分析页面
- 大佬推荐数据可用

#### 第五阶段：投资策略（3-4周）

**任务**:
- [ ] 个股预设策略
  - [ ] 价值投资策略
  - [ ] 趋势跟踪策略
  - [ ] 网格交易策略（可选）
  - [ ] 定投策略（可选）
- [ ] ETF预设策略
  - [ ] 核心-卫星策略
  - [ ] 行业轮动策略
  - [ ] 动量策略
  - [ ] 资产配置策略
- [ ] 自定义策略引擎
  - [ ] 策略DSL解析器
  - [ ] 条件匹配逻辑
- [ ] 交易信号生成
  - [ ] 定时执行策略
  - [ ] 信号存储和查询
- [ ] 账户类型与策略适配
  - [ ] IRA/401K账户策略推荐
  - [ ] 税收优化逻辑

**交付物**:
- 用户可以创建个股和ETF策略
- 策略自动生成交易信号
- 根据账户类型推荐合适策略

#### 第六阶段：历史回测（2周）

**任务**:
- [ ] 回测引擎核心
  - [ ] 时间序列遍历
  - [ ] 策略执行
  - [ ] 订单模拟
- [ ] 性能指标计算
  - [ ] 收益率、最大回撤、夏普比率等
- [ ] 回测结果可视化
  - [ ] 净值曲线图
  - [ ] 回撤曲线图
  - [ ] 交易明细表格

**交付物**:
- 用户可以启动回测任务
- 查看回测结果和性能指标

#### 第七阶段：模拟交易（1-2周）

**任务**:
- [ ] 虚拟账户系统
  - [ ] 创建模拟账户
  - [ ] 账户信息展示
- [ ] 模拟订单执行
  - [ ] 市价单、限价单
  - [ ] 自动执行/手动执行
- [ ] 实时盈亏跟踪
  - [ ] 持仓更新
  - [ ] 盈亏计算

**交付物**:
- 用户可以创建模拟账户并模拟交易
- 查看模拟持仓和交易历史

#### 第八阶段：前端界面（3周）

**任务**:
- [ ] Dashboard首页
- [ ] 持仓管理页面
- [ ] 股票筛选页面
- [ ] 策略配置页面
- [ ] 回测结果页面
- [ ] 模拟交易页面
- [ ] 数据管理页面
- [ ] 设置页面
- [ ] 响应式设计优化

**交付物**:
- 完整的前端界面
- 所有功能可通过UI操作

#### 第九阶段：测试和优化（1-2周）

**任务**:
- [ ] 单元测试
  - [ ] 后端Service层测试
  - [ ] 前端组件测试
- [ ] 集成测试
  - [ ] API接口测试
  - [ ] 端到端测试
- [ ] 性能优化
  - [ ] 数据库查询优化
  - [ ] 前端加载性能优化
- [ ] Bug修复
- [ ] 文档完善

**交付物**:
- 测试覆盖率 > 70%
- 系统稳定可用

### 13.2 时间估算

**总计**: 16-22周（约4-5.5个月）

**里程碑**:
- 第4周：基础框架和数据采集完成
- 第9周：持仓管理（含401K/IRA）和筛选完成
- 第15周：策略引擎（含ETF策略）和回测模块完成
- 第19周：模拟交易和前端界面完成
- 第22周：测试完成，系统上线

**新增功能时间估算**:
- 401K/IRA账户支持：+0.5周（数据库+前端表单）
- ETF数据采集和筛选：+1周
- 个股深度分析页面：+1周
- ETF详情页面：+0.5周
- ETF投资策略：+1周

### 13.3 优先级

**MVP（最小可行产品）**:
1. 用户认证
2. 多账户类型支持（含401K、IRA）
3. 持仓导入（手动、Excel）
4. 个股筛选（基本面、技术面）
5. 简单个股策略（价值投资、趋势跟踪）
6. 历史回测

**增强功能（第二阶段）**:
1. ETF筛选和详情
2. ETF投资策略（核心-卫星、资产配置）
3. 个股深度分析（财务图表、估值分析）
4. 大佬推荐追踪（13F、雪球）
5. 券商API同步
6. 自定义策略引擎
7. 模拟交易

**可选功能（第三阶段）**:
- 网格交易和定投策略
- Kubernetes部署
- Redis缓存
- 实时通知（WebSocket）
- 移动端应用
- DCF估值模型

---

## 附录

### A. 技术栈版本

- Java 17
- Spring Boot 3.2.0
- MySQL 8.0
- Vue 3.3.4
- Vite 4.4.9
- Tailwind CSS 3.3.5
- Chart.js 4.5.1

### B. 参考资料

- Yahoo Finance API: https://www.yahoofinanceapi.com/
- Alpha Vantage API: https://www.alphavantage.co/
- 富途OpenAPI: https://openapi.futunn.com/
- 老虎证券API: https://quant.itigerup.com/
- SEC EDGAR 13F: https://www.sec.gov/edgar

### C. 设计原则

1. **YAGNI（You Aren't Gonna Need It）**: 只实现当前需要的功能，不过度设计
2. **DRY（Don't Repeat Yourself）**: 避免代码重复，提取公共逻辑
3. **关注点分离**: 前后端分离，业务逻辑和数据访问分离
4. **可扩展性**: 预留扩展点，支持新策略、新数据源的接入
5. **用户体验优先**: 界面简洁、操作直观、响应快速

---

**文档结束**
