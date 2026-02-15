# Task Plan: Stock Investment System Implementation

## Goal
Build a comprehensive stock investment system with multi-account support (including 401K/IRA), stock screening (individual stocks and ETFs), investment strategy engine, historical backtesting, and simulated trading capabilities using Spring Boot backend and Vue 3 frontend.

## Current Phase
Phase 3

## Phases

### Phase 1: Project Foundation & Database Setup
- [x] Initialize Spring Boot backend project with Maven
- [x] Initialize Vue 3 frontend project with Vite
- [x] Configure Tailwind CSS and Radix Vue
- [x] Create all database tables based on design document
- [x] Test database connectivity
- [x] Setup JWT authentication (user registration/login)
- **Status:** complete

### Phase 2: User Authentication & Account Management
- [x] Implement user registration and login endpoints (completed in Phase 1)
- [x] Implement JWT token generation and validation (completed in Phase 1)
- [x] Create account management endpoints (CRUD for portfolios)
- [x] Support multiple account types (CASH, MARGIN, IRA_TRADITIONAL, IRA_ROTH, 401K, TAXABLE)
- [x] Build basic frontend login/registration pages
- [x] Build portfolio management UI
- **Status:** complete

### Phase 3: Data Collection & Stock Information
- [x] Integrate Yahoo Finance API for stock prices
- [ ] Integrate Alpha Vantage API for financial data (optional - deferred)
- [x] Implement scheduled tasks for daily data updates
- [x] Create stock CRUD endpoints
- [ ] Implement technical indicator calculation (deferred to later phase)
- [x] Build stock search and list UI
- **Status:** complete

### Phase 4: Holdings Import & Management
- [ ] Implement manual holding entry
- [ ] Implement Excel/CSV import functionality
- [ ] Create holdings display with profit/loss calculation
- [ ] Build holdings management UI with filtering (stocks vs ETFs)
- [ ] Add holdings analytics (industry distribution, market distribution)
- **Status:** pending

### Phase 5: Stock Screening Engine
- [ ] Implement fundamental screening (PE, PB, ROE, etc.)
- [ ] Implement technical screening (MA, MACD, RSI, etc.)
- [ ] Implement ETF-specific screening (expense ratio, AUM, etc.)
- [ ] Create screening templates system
- [ ] Build stock screening UI (separate tabs for stocks and ETFs)
- [ ] Build stock detail page (financial analysis, valuation, technical charts)
- [ ] Build ETF detail page (holdings, sector allocation, tracking error)
- **Status:** pending

### Phase 6: Investment Strategy Engine
- [ ] Implement preset strategies (Value, Trend, Grid, DCA)
- [ ] Implement ETF strategies (Core-Satellite, Sector Rotation, Asset Allocation)
- [ ] Create custom strategy DSL parser
- [ ] Implement signal generation logic
- [ ] Build strategy configuration UI
- [ ] Create signal display and management UI
- **Status:** pending

### Phase 7: Backtesting Engine
- [ ] Implement backtest execution engine
- [ ] Calculate performance metrics (return, drawdown, Sharpe ratio)
- [ ] Store backtest results
- [ ] Build backtest configuration UI
- [ ] Create visualization for backtest results (equity curve, drawdown chart)
- **Status:** pending

### Phase 8: Simulated Trading
- [ ] Implement virtual account system
- [ ] Create order execution simulator
- [ ] Build position tracking and P&L calculation
- [ ] Implement risk control checks
- [ ] Build simulated trading UI
- **Status:** pending

### Phase 9: Frontend Polish & Integration
- [ ] Complete dashboard page
- [ ] Integrate all feature pages
- [ ] Implement responsive design
- [ ] Add loading states and error handling
- [ ] Test all user flows
- **Status:** pending

### Phase 10: Testing & Deployment
- [ ] Write unit tests for critical services
- [ ] Write API integration tests
- [ ] Performance optimization
- [ ] Create Docker Compose setup
- [ ] Write deployment documentation
- **Status:** pending

## Key Questions
1. Should we implement券商API integration in Phase 1 or defer to later? (Defer to later - focus on manual/Excel import first)
2. Which stock screening criteria should be prioritized? (Start with fundamental: PE, PB, ROE; technical: MA, MACD, RSI)
3. How many preset strategies should we implement in Phase 1? (Start with 2: Value Investing and Trend Following)
4. Should ETF functionality be in the MVP or deferred? (Include in MVP - important for portfolio diversification)
5. What's the minimum viable backtest implementation? (Daily execution with basic metrics: return, max drawdown, Sharpe ratio)

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Use existing MySQL @ 10.0.0.7:37719 | Already configured and available |
| Spring Boot 3.2 + Java 17 | Modern, matches finance project experience |
| Vue 3 + Vite + Tailwind CSS | Proven stack from finance project |
| JWT authentication | Stateless, scalable, standard practice |
| JSON for strategy parameters | Flexible, easy to extend, human-readable |
| Support both stocks and ETFs from start | Important for comprehensive portfolio management |
| Separate tabs for stock vs ETF screening | Different metrics and user workflows |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
|       | 1       |            |

## Notes
- Design document is comprehensive at docs/plans/2026-02-14-stock-investment-system-design.md
- Database credentials configured in backend/.env (excluded from git)
- Git remote configured for HTTPS (https://github.com/austinxyz/stock.git)
- .env files now properly ignored in .gitignore
- Update phase status as you progress: pending → in_progress → complete
- Re-read this plan before major decisions (attention manipulation)
- Log ALL errors - they help avoid repetition
