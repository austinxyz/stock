-- Stock Prices Table
-- Stores historical price data for stocks
CREATE TABLE IF NOT EXISTS stock_prices (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_id BIGINT NOT NULL,
    price DECIMAL(15, 4) NOT NULL COMMENT 'Stock price',
    volume BIGINT COMMENT 'Trading volume',
    currency VARCHAR(10) DEFAULT 'USD' COMMENT 'Currency code',
    market_cap BIGINT COMMENT 'Market capitalization at this time',
    source VARCHAR(50) DEFAULT 'ALPHA_VANTAGE' COMMENT 'Data source: ALPHA_VANTAGE, YAHOO_FINANCE, MANUAL',
    price_date DATETIME NOT NULL COMMENT 'Price timestamp',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (stock_id) REFERENCES stocks(id) ON DELETE CASCADE,
    INDEX idx_stock_price_date (stock_id, price_date),
    INDEX idx_price_date (price_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Stock historical prices';
