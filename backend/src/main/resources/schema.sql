-- Stock Investment System Database Schema
-- Database: stock
-- Charset: utf8mb4_unicode_ci

-- Drop tables if exists (in reverse dependency order)
DROP TABLE IF EXISTS institutional_holdings;
DROP TABLE IF EXISTS stock_news;
DROP TABLE IF EXISTS trade_signals;
DROP TABLE IF EXISTS backtest_results;
DROP TABLE IF EXISTS backtest_jobs;
DROP TABLE IF EXISTS strategies;
DROP TABLE IF EXISTS screening_results;
DROP TABLE IF EXISTS guru_recommendations;
DROP TABLE IF EXISTS screening_templates;
DROP TABLE IF EXISTS simulated_transactions;
DROP TABLE IF EXISTS simulated_holdings;
DROP TABLE IF EXISTS simulated_accounts;
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS holdings;
DROP TABLE IF EXISTS etf_holdings;
DROP TABLE IF EXISTS stock_technical_indicators;
DROP TABLE IF EXISTS stock_fundamentals;
DROP TABLE IF EXISTS stock_prices;
DROP TABLE IF EXISTS stocks;
DROP TABLE IF EXISTS portfolio_goals;
DROP TABLE IF EXISTS portfolios;
DROP TABLE IF EXISTS users;

-- 1. Users and Accounts

CREATE TABLE users (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(50) UNIQUE NOT NULL,
  password VARCHAR(255) NOT NULL,
  email VARCHAR(100),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE portfolios (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  name VARCHAR(100) NOT NULL,
  broker VARCHAR(50),
  account_type VARCHAR(30),
  tax_deferred BOOLEAN DEFAULT FALSE,
  tax_free BOOLEAN DEFAULT FALSE,
  contribution_limit DECIMAL(15,2),
  withdrawal_penalty BOOLEAN DEFAULT FALSE,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE portfolio_goals (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  portfolio_id BIGINT NOT NULL,
  target_return_rate DECIMAL(10,4),
  investment_period_months INT,
  initial_capital DECIMAL(15,2),
  max_drawdown_limit DECIMAL(10,4),
  max_position_per_stock DECIMAL(10,4),
  max_position_per_sector DECIMAL(10,4),
  cash_reserve_ratio DECIMAL(10,4),
  stop_loss_ratio DECIMAL(10,4),
  take_profit_ratio DECIMAL(10,4),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Stock Data

CREATE TABLE stocks (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  symbol VARCHAR(20) UNIQUE NOT NULL,
  name VARCHAR(200) NOT NULL,
  security_type VARCHAR(10) NOT NULL DEFAULT 'STOCK',
  market VARCHAR(10) NOT NULL,
  exchange VARCHAR(50),
  sector VARCHAR(100),
  industry VARCHAR(100),
  market_cap BIGINT,
  listing_date DATE,
  etf_category VARCHAR(100),
  etf_holdings_count INT,
  expense_ratio DECIMAL(10,4),
  aum BIGINT,
  avg_volume BIGINT,
  dividend_yield DECIMAL(10,4),
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_market (market),
  INDEX idx_sector (sector),
  INDEX idx_security_type (security_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE stock_prices (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  stock_id BIGINT NOT NULL,
  trade_date DATE NOT NULL,
  open_price DECIMAL(15,4),
  high_price DECIMAL(15,4),
  low_price DECIMAL(15,4),
  close_price DECIMAL(15,4),
  volume BIGINT,
  adjusted_close DECIMAL(15,4),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (stock_id) REFERENCES stocks(id) ON DELETE CASCADE,
  UNIQUE KEY uk_stock_date (stock_id, trade_date),
  INDEX idx_trade_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE stock_fundamentals (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  stock_id BIGINT NOT NULL,
  report_date DATE NOT NULL,
  pe_ratio DECIMAL(10,4),
  pb_ratio DECIMAL(10,4),
  roe DECIMAL(10,4),
  revenue DECIMAL(18,2),
  net_income DECIMAL(18,2),
  revenue_growth_rate DECIMAL(10,4),
  debt_to_asset_ratio DECIMAL(10,4),
  dividend_yield DECIMAL(10,4),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (stock_id) REFERENCES stocks(id) ON DELETE CASCADE,
  UNIQUE KEY uk_stock_report (stock_id, report_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE stock_technical_indicators (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  stock_id BIGINT NOT NULL,
  trade_date DATE NOT NULL,
  ma5 DECIMAL(15,4),
  ma10 DECIMAL(15,4),
  ma20 DECIMAL(15,4),
  ma60 DECIMAL(15,4),
  ma120 DECIMAL(15,4),
  ma250 DECIMAL(15,4),
  macd_dif DECIMAL(15,4),
  macd_dea DECIMAL(15,4),
  macd_histogram DECIMAL(15,4),
  rsi DECIMAL(10,4),
  bollinger_upper DECIMAL(15,4),
  bollinger_middle DECIMAL(15,4),
  bollinger_lower DECIMAL(15,4),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (stock_id) REFERENCES stocks(id) ON DELETE CASCADE,
  UNIQUE KEY uk_stock_date (stock_id, trade_date),
  INDEX idx_trade_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE etf_holdings (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  etf_id BIGINT NOT NULL,
  holding_stock_id BIGINT NOT NULL,
  weight DECIMAL(10,4),
  shares BIGINT,
  market_value DECIMAL(18,2),
  as_of_date DATE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (etf_id) REFERENCES stocks(id) ON DELETE CASCADE,
  FOREIGN KEY (holding_stock_id) REFERENCES stocks(id) ON DELETE CASCADE,
  UNIQUE KEY uk_etf_holding_date (etf_id, holding_stock_id, as_of_date),
  INDEX idx_etf_id (etf_id),
  INDEX idx_as_of_date (as_of_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE stock_news (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  stock_id BIGINT NOT NULL,
  title VARCHAR(500),
  summary TEXT,
  url VARCHAR(500),
  source VARCHAR(100),
  published_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (stock_id) REFERENCES stocks(id) ON DELETE CASCADE,
  INDEX idx_published_at (published_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE institutional_holdings (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  stock_id BIGINT NOT NULL,
  institution_name VARCHAR(200),
  shares BIGINT,
  market_value DECIMAL(18,2),
  percentage DECIMAL(10,4),
  report_date DATE,
  change_shares BIGINT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (stock_id) REFERENCES stocks(id) ON DELETE CASCADE,
  INDEX idx_report_date (report_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Holdings and Transactions

CREATE TABLE holdings (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  portfolio_id BIGINT NOT NULL,
  stock_id BIGINT NOT NULL,
  quantity DECIMAL(15,4) NOT NULL,
  cost_price DECIMAL(15,4) NOT NULL,
  import_source VARCHAR(20),
  imported_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE,
  FOREIGN KEY (stock_id) REFERENCES stocks(id) ON DELETE CASCADE,
  UNIQUE KEY uk_portfolio_stock (portfolio_id, stock_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE transactions (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  portfolio_id BIGINT NOT NULL,
  stock_id BIGINT NOT NULL,
  transaction_type VARCHAR(10) NOT NULL,
  trade_date DATE NOT NULL,
  price DECIMAL(15,4) NOT NULL,
  quantity DECIMAL(15,4) NOT NULL,
  commission DECIMAL(15,2),
  notes TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE,
  FOREIGN KEY (stock_id) REFERENCES stocks(id) ON DELETE CASCADE,
  INDEX idx_trade_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Simulated Trading

CREATE TABLE simulated_accounts (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  name VARCHAR(100) NOT NULL,
  initial_capital DECIMAL(15,2) NOT NULL,
  current_cash DECIMAL(15,2) NOT NULL,
  current_market_value DECIMAL(15,2),
  total_assets DECIMAL(15,2),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE simulated_holdings (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  simulated_account_id BIGINT NOT NULL,
  stock_id BIGINT NOT NULL,
  quantity DECIMAL(15,4) NOT NULL,
  cost_price DECIMAL(15,4) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (simulated_account_id) REFERENCES simulated_accounts(id) ON DELETE CASCADE,
  FOREIGN KEY (stock_id) REFERENCES stocks(id) ON DELETE CASCADE,
  UNIQUE KEY uk_account_stock (simulated_account_id, stock_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE simulated_transactions (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  simulated_account_id BIGINT NOT NULL,
  stock_id BIGINT NOT NULL,
  transaction_type VARCHAR(10) NOT NULL,
  trade_date DATE NOT NULL,
  price DECIMAL(15,4) NOT NULL,
  quantity DECIMAL(15,4) NOT NULL,
  commission DECIMAL(15,2),
  signal_source VARCHAR(100),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (simulated_account_id) REFERENCES simulated_accounts(id) ON DELETE CASCADE,
  FOREIGN KEY (stock_id) REFERENCES stocks(id) ON DELETE CASCADE,
  INDEX idx_trade_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Screening and Recommendations

CREATE TABLE screening_templates (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  name VARCHAR(100) NOT NULL,
  description TEXT,
  criteria_json JSON NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE guru_recommendations (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  stock_id BIGINT NOT NULL,
  source VARCHAR(50) NOT NULL,
  recommender VARCHAR(100),
  recommendation_date DATE NOT NULL,
  reason TEXT,
  weight DECIMAL(10,4),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (stock_id) REFERENCES stocks(id) ON DELETE CASCADE,
  INDEX idx_source (source),
  INDEX idx_date (recommendation_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE screening_results (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  template_id BIGINT,
  stock_id BIGINT NOT NULL,
  score DECIMAL(10,4),
  fundamental_score DECIMAL(10,4),
  technical_score DECIMAL(10,4),
  guru_score DECIMAL(10,4),
  sector_score DECIMAL(10,4),
  screening_date DATE NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (template_id) REFERENCES screening_templates(id) ON DELETE SET NULL,
  FOREIGN KEY (stock_id) REFERENCES stocks(id) ON DELETE CASCADE,
  INDEX idx_screening_date (screening_date),
  INDEX idx_score (score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. Strategies and Backtesting

CREATE TABLE strategies (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  name VARCHAR(100) NOT NULL,
  strategy_type VARCHAR(50) NOT NULL,
  parameters_json JSON NOT NULL,
  buy_conditions_json JSON,
  sell_conditions_json JSON,
  is_active BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE backtest_jobs (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  strategy_id BIGINT NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  initial_capital DECIMAL(15,2) NOT NULL,
  status VARCHAR(20) NOT NULL,
  progress INT DEFAULT 0,
  error_message TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (strategy_id) REFERENCES strategies(id) ON DELETE CASCADE,
  INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE backtest_results (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  job_id BIGINT NOT NULL,
  total_return DECIMAL(10,4),
  annualized_return DECIMAL(10,4),
  max_drawdown DECIMAL(10,4),
  sharpe_ratio DECIMAL(10,4),
  volatility DECIMAL(10,4),
  win_rate DECIMAL(10,4),
  profit_loss_ratio DECIMAL(10,4),
  total_trades INT,
  turnover_rate DECIMAL(10,4),
  trades_json JSON,
  daily_returns_json JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (job_id) REFERENCES backtest_jobs(id) ON DELETE CASCADE,
  UNIQUE KEY uk_job (job_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE trade_signals (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  strategy_id BIGINT NOT NULL,
  stock_id BIGINT NOT NULL,
  signal_type VARCHAR(10) NOT NULL,
  signal_strength DECIMAL(10,4),
  price DECIMAL(15,4),
  quantity DECIMAL(15,4),
  reason TEXT,
  is_executed BOOLEAN DEFAULT FALSE,
  generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  executed_at TIMESTAMP,
  FOREIGN KEY (strategy_id) REFERENCES strategies(id) ON DELETE CASCADE,
  FOREIGN KEY (stock_id) REFERENCES stocks(id) ON DELETE CASCADE,
  INDEX idx_generated_at (generated_at),
  INDEX idx_is_executed (is_executed)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
