# Findings & Decisions

## Requirements
<!-- Captured from design document and user request -->
- Multi-account portfolio management with support for 401K, IRA (Traditional/Roth), and taxable accounts
- Stock screening based on fundamentals (PE, PB, ROE), technicals (MA, MACD, RSI), and guru recommendations
- ETF screening with specialized metrics (expense ratio, AUM, tracking error)
- Investment strategy engine with preset strategies (Value, Trend, Grid, DCA) and custom DSL
- ETF-specific strategies (Core-Satellite, Sector Rotation, Asset Allocation)
- Historical backtesting with performance metrics (return, drawdown, Sharpe ratio)
- Simulated trading with virtual accounts
- Support for US stocks (NASDAQ, NYSE) and Hong Kong stocks (HKEX)
- Data sources: Yahoo Finance API, Alpha Vantage API, optional broker APIs
- Individual stock deep analysis (financial trends, valuation percentiles, technical charts)
- ETF deep analysis (holdings breakdown, sector allocation, tracking error)

## Research Findings
<!-- Key discoveries during exploration -->
- Design document comprehensive and well-structured at docs/plans/2026-02-14-stock-investment-system-design.md
- Database schema includes all necessary tables for stocks, ETFs, holdings, strategies, backtests
- Account types properly designed: CASH, MARGIN, IRA_TRADITIONAL, IRA_ROTH, 401K, TAXABLE
- ETF-specific fields included: security_type, etf_category, expense_ratio, aum
- Separate screening logic needed for stocks vs ETFs (different metrics)
- Stock detail page components: company info, 5-year financial trends, valuation analysis, technical charts, news
- ETF detail page components: basic info, holdings breakdown, sector allocation, performance metrics
- Strategy DSL designed for JSON format with buy/sell conditions
- Backtest engine needs to consider transaction costs (commission, tax, slippage)

## Technical Decisions
<!-- Decisions made with rationale -->
| Decision | Rationale |
|----------|-----------|
| MySQL @ 10.0.0.7:37719 | Already configured and accessible |
| Spring Boot 3.2 + Java 17 | Modern Java stack, good ecosystem |
| Spring Data JPA | Simplifies database operations, reduces boilerplate |
| Vue 3 Composition API | Modern, reactive, better than Options API |
| Vite build tool | Fast HMR, better than webpack for development |
| Tailwind CSS + Radix Vue | Proven combination from finance project |
| Chart.js for visualization | Good balance of features and simplicity |
| Yahoo Finance API | Free, covers both US and HK markets |
| JSON for strategy parameters | Flexible schema, easy to extend |
| Separate security_type field in stocks table | Clean way to distinguish STOCK vs ETF vs INDEX |
| JWT for authentication | Stateless, scalable, industry standard |
| 22 database tables total | Comprehensive schema covering all features (users, portfolios, stocks, holdings, strategies, backtests, simulations) |
| CASCADE deletes on foreign keys | Clean data integrity when deleting parent records |
| utf8mb4_unicode_ci charset | Full Unicode support for international stock names |

## Issues Encountered
<!-- Errors and how they were resolved -->
| Issue | Resolution |
|-------|------------|
| .env file was committed to git with credentials | Removed from git history using git filter-branch, added to .gitignore |
| Git remote timeout on SSH | Switched from SSH to HTTPS (git@github.com → https://github.com) |

## Resources
<!-- URLs, file paths, API references -->
- Design document: docs/plans/2026-02-14-stock-investment-system-design.md
- Database: MySQL 8.0 @ 10.0.0.7:37719 (database: stock)
- Git repository: https://github.com/austinxyz/stock.git
- Yahoo Finance API: https://www.yahoofinanceapi.com/
- Alpha Vantage API: https://www.alphavantage.co/
- Spring Boot docs: https://spring.io/projects/spring-boot
- Vue 3 docs: https://vuejs.org/
- Tailwind CSS: https://tailwindcss.com/
- Radix Vue: https://www.radix-vue.com/

## Visual/Browser Findings
<!-- CRITICAL: Update after every 2 view/browser operations -->
<!-- Multimodal content must be captured as text immediately -->
- N/A (no visual content viewed yet)

---
*Update this file after every 2 view/browser/search operations*
*This prevents visual information from being lost*
