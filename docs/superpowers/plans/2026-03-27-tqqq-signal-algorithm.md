# TQQQ Signal Algorithm Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a TQQQ buy-signal algorithm that scores 0–100 using five technical indicators and provides position tracking, soft stop-loss alerts, and historical backtesting.

**Architecture:** New independent module (backend services + REST controller + Vue page) integrated into the existing Spring Boot + Vue 3 system. Alpha Vantage `TIME_SERIES_DAILY_ADJUSTED` provides daily OHLCV for QQQ and TQQQ. Scores drive dynamic position sizing recommendations. Red-alert conditions suppress buy signals.

**Tech Stack:** Spring Boot 3.2 / Java 17 / JPA / MySQL, Vue 3 / Vite / Tailwind CSS / Chart.js, Alpha Vantage API

---

## File Map

### Backend — New Files
| File | Responsibility |
|------|---------------|
| `backend/src/main/resources/db/migration/V4__tqqq_tables.sql` | 3 new DB tables |
| `backend/src/main/java/com/stock/investment/entity/TqqqOhlcv.java` | Daily OHLCV record for QQQ/TQQQ |
| `backend/src/main/java/com/stock/investment/entity/TqqqPosition.java` | User's manual buy records |
| `backend/src/main/java/com/stock/investment/entity/TqqqSignal.java` | Historical signal snapshots |
| `backend/src/main/java/com/stock/investment/repository/TqqqOhlcvRepository.java` | OHLCV queries |
| `backend/src/main/java/com/stock/investment/repository/TqqqPositionRepository.java` | Position queries |
| `backend/src/main/java/com/stock/investment/repository/TqqqSignalRepository.java` | Signal queries |
| `backend/src/main/java/com/stock/investment/service/TqqqDataService.java` | Fetch & persist OHLCV from Alpha Vantage |
| `backend/src/main/java/com/stock/investment/service/TqqqIndicatorService.java` | Calculate RSI, MACD, BB, ATR, drawdown |
| `backend/src/main/java/com/stock/investment/service/TqqqScoringService.java` | Combine indicators → 0–100 score |
| `backend/src/main/java/com/stock/investment/service/TqqqPositionService.java` | Avg cost, alert levels, budget tracking |
| `backend/src/main/java/com/stock/investment/service/TqqqBacktestService.java` | Historical replay engine |
| `backend/src/main/java/com/stock/investment/controller/TqqqController.java` | REST endpoints |
| `backend/src/main/java/com/stock/investment/dto/TqqqSignalResponse.java` | Signal API response |
| `backend/src/main/java/com/stock/investment/dto/TqqqPositionRequest.java` | Add-position request |
| `backend/src/main/java/com/stock/investment/dto/TqqqPositionResponse.java` | Position summary response |
| `backend/src/main/java/com/stock/investment/dto/TqqqBacktestRequest.java` | Backtest config |
| `backend/src/main/java/com/stock/investment/dto/TqqqBacktestResult.java` | Backtest output |

### Backend — Modified Files
| File | Change |
|------|--------|
| `backend/src/main/java/com/stock/investment/service/AlphaVantageService.java` | Add `getHistoricalDaily(symbol, outputSize)` |
| `backend/src/main/resources/application.properties` | Add `alphavantage.api.key` placeholder reference |

### Frontend — New Files
| File | Responsibility |
|------|---------------|
| `frontend/src/api/tqqq.js` | Axios calls to TQQQ endpoints |
| `frontend/src/views/Tqqq.vue` | Main TQQQ dashboard page |
| `frontend/src/components/tqqq/SignalPanel.vue` | Today's score + buy suggestion |
| `frontend/src/components/tqqq/PositionPanel.vue` | Position tracker + alerts |
| `frontend/src/components/tqqq/BacktestPanel.vue` | Backtest config form + results chart |

### Frontend — Modified Files
| File | Change |
|------|--------|
| `frontend/src/router/index.js` | Add `/tqqq` route |
| `frontend/src/components/Sidebar.vue` | Add TQQQ nav item under Strategy section |

### Test Files
| File | Tests |
|------|-------|
| `backend/src/test/java/com/stock/investment/service/TqqqIndicatorServiceTest.java` | RSI, MACD, BB, ATR, drawdown calculations |
| `backend/src/test/java/com/stock/investment/service/TqqqScoringServiceTest.java` | Score combinations and edge cases |
| `backend/src/test/java/com/stock/investment/service/TqqqPositionServiceTest.java` | Avg cost, alert levels, budget math |
| `backend/src/test/java/com/stock/investment/service/TqqqBacktestServiceTest.java` | Backtest simulation logic |

---

## Task 1: Database Tables

**Files:**
- Create: `backend/src/main/resources/db/migration/V4__tqqq_tables.sql`

- [ ] **Step 1: Create SQL migration file**

```sql
-- V4__tqqq_tables.sql

CREATE TABLE tqqq_ohlcv (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    open_price DECIMAL(15,4),
    high_price DECIMAL(15,4),
    low_price DECIMAL(15,4),
    close_price DECIMAL(15,4) NOT NULL,
    adjusted_close DECIMAL(15,4),
    volume BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_tqqq_ohlcv_symbol_date (symbol, trade_date),
    INDEX idx_tqqq_ohlcv_symbol_date (symbol, trade_date)
);

CREATE TABLE tqqq_positions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    buy_date DATE NOT NULL,
    shares DECIMAL(15,4) NOT NULL,
    price_per_share DECIMAL(15,4) NOT NULL,
    total_cost DECIMAL(15,2) NOT NULL,
    notes VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_tqqq_positions_user (user_id)
);

CREATE TABLE tqqq_signals (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    signal_date DATE NOT NULL,
    total_score INT NOT NULL,
    drawdown_score INT NOT NULL DEFAULT 0,
    rsi_score INT NOT NULL DEFAULT 0,
    macd_score INT NOT NULL DEFAULT 0,
    bb_score INT NOT NULL DEFAULT 0,
    atr_score INT NOT NULL DEFAULT 0,
    qqq_drawdown_pct DECIMAL(8,4),
    tqqq_rsi DECIMAL(8,4),
    suggested_amount DECIMAL(15,2),
    alert_level VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_tqqq_signals_date (signal_date),
    INDEX idx_tqqq_signals_date (signal_date)
);
```

- [ ] **Step 2: Execute migration**

```bash
cd backend
# Connect to DB and run the migration
mysql -h 10.0.0.7 -P 37719 -u austinxu -p stock < src/main/resources/db/migration/V4__tqqq_tables.sql
```

Expected output: no errors. Verify with:
```bash
mysql -h 10.0.0.7 -P 37719 -u austinxu -p stock -e "SHOW TABLES LIKE 'tqqq%';"
```
Expected: 3 rows — `tqqq_ohlcv`, `tqqq_positions`, `tqqq_signals`

- [ ] **Step 3: Commit**

```bash
git add backend/src/main/resources/db/migration/V4__tqqq_tables.sql
git commit -m "feat: add tqqq_ohlcv, tqqq_positions, tqqq_signals tables"
```

---

## Task 2: Alpha Vantage Historical Data

**Files:**
- Modify: `backend/src/main/java/com/stock/investment/service/AlphaVantageService.java`
- Modify: `backend/src/main/resources/application.properties`

- [ ] **Step 1: Add alphavantage.api.key to application.properties**

Add after the existing `jwt.expiration` line:

```properties
# Alpha Vantage
alphavantage.api.key=${ALPHAVANTAGE_API_KEY:DEMO}
```

Also add `ALPHAVANTAGE_API_KEY=your_key_here` to `backend/.env` (not committed).

- [ ] **Step 2: Add getHistoricalDaily method to AlphaVantageService**

Add the following method to the existing `AlphaVantageService` class (after `getStockDetails`):

```java
/**
 * Get daily adjusted OHLCV for a symbol.
 * outputSize: "compact" = last 100 days, "full" = up to 20 years
 */
public List<Map<String, Object>> getHistoricalDaily(String symbol, String outputSize) {
    try {
        String url = String.format(
            "%s?function=TIME_SERIES_DAILY_ADJUSTED&symbol=%s&outputsize=%s&apikey=%s",
            BASE_URL, symbol, outputSize, apiKey);

        String response = restTemplate.getForObject(url, String.class);
        JsonNode root = objectMapper.readTree(response);

        if (root.has("Error Message")) {
            throw new RuntimeException("Invalid symbol: " + symbol);
        }
        if (root.has("Note")) {
            throw new RuntimeException("API rate limit reached. Please try again later.");
        }
        if (root.has("Information")) {
            throw new RuntimeException("API limit reached: " + root.path("Information").asText());
        }

        JsonNode timeSeries = root.path("Time Series (Daily)");
        List<Map<String, Object>> result = new ArrayList<>();

        timeSeries.fields().forEachRemaining(entry -> {
            Map<String, Object> day = new HashMap<>();
            day.put("date", entry.getKey());
            JsonNode v = entry.getValue();
            day.put("open", v.path("1. open").asDouble());
            day.put("high", v.path("2. high").asDouble());
            day.put("low", v.path("3. low").asDouble());
            day.put("close", v.path("4. close").asDouble());
            day.put("adjustedClose", v.path("5. adjusted close").asDouble());
            day.put("volume", v.path("6. volume").asLong());
            result.add(day);
        });

        // Sort ascending by date
        result.sort(Comparator.comparing(m -> (String) m.get("date")));
        return result;

    } catch (Exception e) {
        log.error("Error fetching historical daily for {}: {}", symbol, e.getMessage());
        throw new RuntimeException("Failed to fetch historical data: " + e.getMessage());
    }
}
```

Add the missing imports at the top of the file:
```java
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
```

- [ ] **Step 3: Verify the project still compiles**

```bash
cd backend
mvn compile -q
```
Expected: `BUILD SUCCESS`

- [ ] **Step 4: Commit**

```bash
git add backend/src/main/java/com/stock/investment/service/AlphaVantageService.java
git add backend/src/main/resources/application.properties
git commit -m "feat: add getHistoricalDaily to AlphaVantageService"
```

---

## Task 3: TqqqOhlcv Entity and Repository

**Files:**
- Create: `backend/src/main/java/com/stock/investment/entity/TqqqOhlcv.java`
- Create: `backend/src/main/java/com/stock/investment/repository/TqqqOhlcvRepository.java`

- [ ] **Step 1: Create TqqqOhlcv entity**

```java
// backend/src/main/java/com/stock/investment/entity/TqqqOhlcv.java
package com.stock.investment.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(name = "tqqq_ohlcv")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class TqqqOhlcv {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 10)
    private String symbol;

    @Column(name = "trade_date", nullable = false)
    private LocalDate tradeDate;

    @Column(name = "open_price", precision = 15, scale = 4)
    private BigDecimal openPrice;

    @Column(name = "high_price", precision = 15, scale = 4)
    private BigDecimal highPrice;

    @Column(name = "low_price", precision = 15, scale = 4)
    private BigDecimal lowPrice;

    @Column(name = "close_price", precision = 15, scale = 4, nullable = false)
    private BigDecimal closePrice;

    @Column(name = "adjusted_close", precision = 15, scale = 4)
    private BigDecimal adjustedClose;

    @Column
    private Long volume;

    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
    }
}
```

- [ ] **Step 2: Create TqqqOhlcvRepository**

```java
// backend/src/main/java/com/stock/investment/repository/TqqqOhlcvRepository.java
package com.stock.investment.repository;

import com.stock.investment.entity.TqqqOhlcv;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

@Repository
public interface TqqqOhlcvRepository extends JpaRepository<TqqqOhlcv, Long> {
    List<TqqqOhlcv> findBySymbolOrderByTradeDateAsc(String symbol);

    List<TqqqOhlcv> findBySymbolAndTradeDateBetweenOrderByTradeDateAsc(
            String symbol, LocalDate from, LocalDate to);

    Optional<TqqqOhlcv> findBySymbolAndTradeDate(String symbol, LocalDate date);

    @Query("SELECT t FROM TqqqOhlcv t WHERE t.symbol = :symbol ORDER BY t.tradeDate DESC")
    List<TqqqOhlcv> findLatestBySymbol(String symbol, org.springframework.data.domain.Pageable pageable);

    @Query("SELECT MAX(t.tradeDate) FROM TqqqOhlcv t WHERE t.symbol = :symbol")
    Optional<LocalDate> findLatestDateBySymbol(String symbol);
}
```

- [ ] **Step 3: Compile**

```bash
cd backend && mvn compile -q
```
Expected: `BUILD SUCCESS`

- [ ] **Step 4: Commit**

```bash
git add backend/src/main/java/com/stock/investment/entity/TqqqOhlcv.java
git add backend/src/main/java/com/stock/investment/repository/TqqqOhlcvRepository.java
git commit -m "feat: add TqqqOhlcv entity and repository"
```

---

## Task 4: TqqqDataService (Fetch & Persist OHLCV)

**Files:**
- Create: `backend/src/main/java/com/stock/investment/service/TqqqDataService.java`

- [ ] **Step 1: Create TqqqDataService**

```java
// backend/src/main/java/com/stock/investment/service/TqqqDataService.java
package com.stock.investment.service;

import com.stock.investment.entity.TqqqOhlcv;
import com.stock.investment.repository.TqqqOhlcvRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@Service
@Slf4j
@RequiredArgsConstructor
public class TqqqDataService {

    private final AlphaVantageService alphaVantageService;
    private final TqqqOhlcvRepository ohlcvRepository;

    private static final List<String> SYMBOLS = List.of("QQQ", "TQQQ");

    /**
     * Load up to 5 years of history for QQQ and TQQQ.
     * Uses "full" outputSize. Call once manually to seed data.
     */
    public void loadFullHistory() {
        for (String symbol : SYMBOLS) {
            log.info("Loading full history for {}", symbol);
            persistHistoricalData(symbol, "full");
            sleepForRateLimit();
        }
    }

    /**
     * Refresh latest data (last 100 days) for QQQ and TQQQ.
     * Intended for daily scheduled updates.
     */
    public void refreshDailyData() {
        for (String symbol : SYMBOLS) {
            log.info("Refreshing daily data for {}", symbol);
            persistHistoricalData(symbol, "compact");
            sleepForRateLimit();
        }
    }

    /**
     * Returns the stored OHLCV records for a symbol, sorted ascending by date.
     */
    public List<TqqqOhlcv> getOhlcv(String symbol) {
        return ohlcvRepository.findBySymbolOrderByTradeDateAsc(symbol);
    }

    /**
     * Returns OHLCV records for a symbol within a date range.
     */
    public List<TqqqOhlcv> getOhlcvInRange(String symbol, LocalDate from, LocalDate to) {
        return ohlcvRepository.findBySymbolAndTradeDateBetweenOrderByTradeDateAsc(symbol, from, to);
    }

    private void persistHistoricalData(String symbol, String outputSize) {
        List<Map<String, Object>> data = alphaVantageService.getHistoricalDaily(symbol, outputSize);
        int saved = 0;
        for (Map<String, Object> day : data) {
            LocalDate date = LocalDate.parse((String) day.get("date"));
            Optional<TqqqOhlcv> existing = ohlcvRepository.findBySymbolAndTradeDate(symbol, date);
            if (existing.isPresent()) continue;

            TqqqOhlcv record = new TqqqOhlcv();
            record.setSymbol(symbol);
            record.setTradeDate(date);
            record.setOpenPrice(toBigDecimal(day.get("open")));
            record.setHighPrice(toBigDecimal(day.get("high")));
            record.setLowPrice(toBigDecimal(day.get("low")));
            record.setClosePrice(toBigDecimal(day.get("close")));
            record.setAdjustedClose(toBigDecimal(day.get("adjustedClose")));
            record.setVolume((Long) day.get("volume"));
            ohlcvRepository.save(record);
            saved++;
        }
        log.info("Saved {} new records for {}", saved, symbol);
    }

    private BigDecimal toBigDecimal(Object value) {
        if (value == null) return null;
        return BigDecimal.valueOf(((Number) value).doubleValue());
    }

    private void sleepForRateLimit() {
        try {
            Thread.sleep(13000); // Alpha Vantage free tier: 5 req/min → 12s gap
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}
```

- [ ] **Step 2: Compile**

```bash
cd backend && mvn compile -q
```
Expected: `BUILD SUCCESS`

- [ ] **Step 3: Commit**

```bash
git add backend/src/main/java/com/stock/investment/service/TqqqDataService.java
git commit -m "feat: add TqqqDataService to fetch and persist OHLCV data"
```

---

## Task 5: TqqqIndicatorService (Technical Indicators)

**Files:**
- Create: `backend/src/main/java/com/stock/investment/service/TqqqIndicatorService.java`
- Create: `backend/src/test/java/com/stock/investment/service/TqqqIndicatorServiceTest.java`

- [ ] **Step 1: Write failing tests**

```java
// backend/src/test/java/com/stock/investment/service/TqqqIndicatorServiceTest.java
package com.stock.investment.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class TqqqIndicatorServiceTest {

    private TqqqIndicatorService service;

    @BeforeEach
    void setUp() {
        service = new TqqqIndicatorService();
    }

    @Test
    void rsi_allGains_returns100() {
        // 15 days all gaining
        List<BigDecimal> closes = ascendingPrices(15, 10.0, 1.0);
        double rsi = service.calculateRsi(closes, 14);
        assertEquals(100.0, rsi, 0.01);
    }

    @Test
    void rsi_allLosses_returns0() {
        List<BigDecimal> closes = descendingPrices(15, 20.0, 1.0);
        double rsi = service.calculateRsi(closes, 14);
        assertEquals(0.0, rsi, 0.01);
    }

    @Test
    void rsi_requiresAtLeastPeriodPlusOnePrices() {
        List<BigDecimal> closes = ascendingPrices(5, 10.0, 1.0);
        assertThrows(IllegalArgumentException.class,
            () -> service.calculateRsi(closes, 14));
    }

    @Test
    void drawdown_returnsCorrectPct() {
        // high=100, current=80 → -20%
        List<BigDecimal> closes = new ArrayList<>();
        for (int i = 0; i < 58; i++) closes.add(BigDecimal.valueOf(90));
        closes.add(BigDecimal.valueOf(100)); // 60-day high
        closes.add(BigDecimal.valueOf(80));  // current
        double dd = service.calculateDrawdownFromHigh(closes, 60);
        assertEquals(-20.0, dd, 0.01);
    }

    @Test
    void atr_returnsPositiveValue() {
        List<BigDecimal> highs = ascendingPrices(20, 15.0, 0.5);
        List<BigDecimal> lows  = ascendingPrices(20, 10.0, 0.5);
        List<BigDecimal> closes = ascendingPrices(20, 12.0, 0.5);
        double atr = service.calculateAtr(highs, lows, closes, 14);
        assertTrue(atr > 0);
    }

    @Test
    void bollingerBand_currentBelowLower_returnsNegativeZscore() {
        // 20 equal prices then a big drop → should be below lower band
        List<BigDecimal> closes = new ArrayList<>();
        for (int i = 0; i < 20; i++) closes.add(BigDecimal.valueOf(100));
        closes.add(BigDecimal.valueOf(80)); // drop
        double zScore = service.calculateBollingerZScore(closes, 20, 2.0);
        assertTrue(zScore < -1.0, "Should be below lower band: " + zScore);
    }

    // helpers
    private List<BigDecimal> ascendingPrices(int n, double start, double step) {
        List<BigDecimal> list = new ArrayList<>();
        for (int i = 0; i < n; i++) list.add(BigDecimal.valueOf(start + i * step));
        return list;
    }

    private List<BigDecimal> descendingPrices(int n, double start, double step) {
        List<BigDecimal> list = new ArrayList<>();
        for (int i = 0; i < n; i++) list.add(BigDecimal.valueOf(start - i * step));
        return list;
    }
}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && mvn test -pl . -Dtest=TqqqIndicatorServiceTest -q 2>&1 | tail -20
```
Expected: compilation error or test failures (class not found)

- [ ] **Step 3: Create TqqqIndicatorService**

```java
// backend/src/main/java/com/stock/investment/service/TqqqIndicatorService.java
package com.stock.investment.service;

import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;

@Service
public class TqqqIndicatorService {

    /**
     * RSI using Wilder's smoothed moving average.
     * Requires at least (period + 1) prices.
     */
    public double calculateRsi(List<BigDecimal> closes, int period) {
        if (closes.size() < period + 1) {
            throw new IllegalArgumentException(
                "Need at least " + (period + 1) + " prices for RSI(" + period + ")");
        }

        // First averages
        double avgGain = 0, avgLoss = 0;
        for (int i = 1; i <= period; i++) {
            double change = closes.get(i).doubleValue() - closes.get(i - 1).doubleValue();
            if (change > 0) avgGain += change;
            else avgLoss += Math.abs(change);
        }
        avgGain /= period;
        avgLoss /= period;

        // Smooth remaining
        for (int i = period + 1; i < closes.size(); i++) {
            double change = closes.get(i).doubleValue() - closes.get(i - 1).doubleValue();
            double gain = change > 0 ? change : 0;
            double loss = change < 0 ? Math.abs(change) : 0;
            avgGain = (avgGain * (period - 1) + gain) / period;
            avgLoss = (avgLoss * (period - 1) + loss) / period;
        }

        if (avgLoss == 0) return 100.0;
        double rs = avgGain / avgLoss;
        return 100.0 - (100.0 / (1 + rs));
    }

    /**
     * MACD line, signal line, and histogram for the last data point.
     * Returns double[3]: {macdLine, signalLine, histogram}
     * Requires at least 34 prices (26 for slow EMA + 9 for signal EMA).
     */
    public double[] calculateMacd(List<BigDecimal> closes, int fast, int slow, int signal) {
        if (closes.size() < slow + signal) {
            throw new IllegalArgumentException(
                "Need at least " + (slow + signal) + " prices for MACD");
        }
        List<Double> macdLine = new ArrayList<>();
        for (int i = slow - 1; i < closes.size(); i++) {
            double fastEma = ema(closes, i, fast);
            double slowEma = ema(closes, i, slow);
            macdLine.add(fastEma - slowEma);
        }
        double signalLine = emaFromList(macdLine, macdLine.size() - 1, signal);
        double macd = macdLine.get(macdLine.size() - 1);
        double histogram = macd - signalLine;
        return new double[]{macd, signalLine, histogram};
    }

    /**
     * Drawdown % from highest close in the last lookback days.
     * Returns negative value, e.g. -0.20 for -20%.
     * Requires at least lookback prices.
     */
    public double calculateDrawdownFromHigh(List<BigDecimal> closes, int lookback) {
        if (closes.size() < lookback) {
            throw new IllegalArgumentException("Need at least " + lookback + " prices for drawdown");
        }
        int start = closes.size() - lookback;
        double high = closes.subList(start, closes.size()).stream()
            .mapToDouble(BigDecimal::doubleValue).max().orElseThrow();
        double current = closes.get(closes.size() - 1).doubleValue();
        return ((current - high) / high) * 100.0;
    }

    /**
     * ATR using Wilder's smoothing.
     * All three lists must be same length and >= period + 1.
     */
    public double calculateAtr(List<BigDecimal> highs, List<BigDecimal> lows,
                                List<BigDecimal> closes, int period) {
        if (highs.size() < period + 1) {
            throw new IllegalArgumentException("Need at least " + (period + 1) + " bars for ATR");
        }
        // First ATR = simple average of first `period` true ranges
        double atr = 0;
        for (int i = 1; i <= period; i++) {
            atr += trueRange(highs.get(i), lows.get(i), closes.get(i - 1));
        }
        atr /= period;
        // Smooth remaining
        for (int i = period + 1; i < highs.size(); i++) {
            double tr = trueRange(highs.get(i), lows.get(i), closes.get(i - 1));
            atr = (atr * (period - 1) + tr) / period;
        }
        return atr;
    }

    /**
     * Bollinger Band z-score for the last data point.
     * z = (current - mean) / stdDev.  Returns positive above mean, negative below.
     * A value of -2 means exactly at the lower band (with multiplier=2).
     */
    public double calculateBollingerZScore(List<BigDecimal> closes, int period, double multiplier) {
        if (closes.size() < period + 1) {
            throw new IllegalArgumentException("Need at least " + (period + 1) + " prices for BB");
        }
        // Use last `period` values for band calculation
        List<BigDecimal> window = closes.subList(closes.size() - period - 1, closes.size() - 1);
        double mean = window.stream().mapToDouble(BigDecimal::doubleValue).average().orElseThrow();
        double variance = window.stream()
            .mapToDouble(v -> Math.pow(v.doubleValue() - mean, 2))
            .average().orElseThrow();
        double stdDev = Math.sqrt(variance);
        double current = closes.get(closes.size() - 1).doubleValue();
        if (stdDev == 0) return 0;
        return (current - mean) / stdDev;
    }

    // --- private helpers ---

    private double trueRange(BigDecimal high, BigDecimal low, BigDecimal prevClose) {
        double hl = high.doubleValue() - low.doubleValue();
        double hc = Math.abs(high.doubleValue() - prevClose.doubleValue());
        double lc = Math.abs(low.doubleValue() - prevClose.doubleValue());
        return Math.max(hl, Math.max(hc, lc));
    }

    /** EMA ending at index `endIdx`, looking back `period` bars. */
    private double ema(List<BigDecimal> closes, int endIdx, int period) {
        int startIdx = endIdx - period + 1;
        double multiplier = 2.0 / (period + 1);
        double ema = closes.get(startIdx).doubleValue();
        for (int i = startIdx + 1; i <= endIdx; i++) {
            ema = closes.get(i).doubleValue() * multiplier + ema * (1 - multiplier);
        }
        return ema;
    }

    /** EMA on a plain double list. */
    private double emaFromList(List<Double> values, int endIdx, int period) {
        int startIdx = endIdx - period + 1;
        double multiplier = 2.0 / (period + 1);
        double ema = values.get(startIdx);
        for (int i = startIdx + 1; i <= endIdx; i++) {
            ema = values.get(i) * multiplier + ema * (1 - multiplier);
        }
        return ema;
    }
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && mvn test -Dtest=TqqqIndicatorServiceTest -q 2>&1 | tail -10
```
Expected: `BUILD SUCCESS`, `Tests run: 6, Failures: 0`

- [ ] **Step 5: Commit**

```bash
git add backend/src/main/java/com/stock/investment/service/TqqqIndicatorService.java
git add backend/src/test/java/com/stock/investment/service/TqqqIndicatorServiceTest.java
git commit -m "feat: add TqqqIndicatorService with RSI, MACD, drawdown, ATR, Bollinger Band"
```

---

## Task 6: TqqqScoringService

**Files:**
- Create: `backend/src/main/java/com/stock/investment/service/TqqqScoringService.java`
- Create: `backend/src/test/java/com/stock/investment/service/TqqqScoringServiceTest.java`

- [ ] **Step 1: Write failing tests**

```java
// backend/src/test/java/com/stock/investment/service/TqqqScoringServiceTest.java
package com.stock.investment.service;

import com.stock.investment.entity.TqqqOhlcv;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class TqqqScoringServiceTest {

    private TqqqScoringService scoringService;

    @BeforeEach
    void setUp() {
        scoringService = new TqqqScoringService(new TqqqIndicatorService());
    }

    @Test
    void score_insufficientData_returnsZero() {
        List<TqqqOhlcv> qqq = makeOhlcv("QQQ", 10);
        List<TqqqOhlcv> tqqq = makeOhlcv("TQQQ", 10);
        TqqqScoringService.ScoreResult result = scoringService.calculateScore(qqq, tqqq);
        assertEquals(0, result.getTotalScore());
    }

    @Test
    void score_allIndicatorsStrong_returnsHighScore() {
        // Build QQQ with big drawdown: high=100 for first 60, then drops to 65 → -35%
        List<TqqqOhlcv> qqq = new ArrayList<>();
        for (int i = 0; i < 60; i++) qqq.add(ohlcv("QQQ", i, 100, 100, 95, 100));
        qqq.add(ohlcv("QQQ", 60, 70, 70, 63, 65)); // -35% drawdown → 25 pts

        // TQQQ: declining prices → low RSI, below BB, MACD negative
        List<TqqqOhlcv> tqqq = new ArrayList<>();
        for (int i = 0; i < 61; i++) {
            double price = 50.0 - i * 0.4;
            tqqq.add(ohlcv("TQQQ", i, price + 0.5, price + 1, price - 0.5, price));
        }

        TqqqScoringService.ScoreResult result = scoringService.calculateScore(qqq, tqqq);
        assertTrue(result.getTotalScore() >= 40,
            "Strong bearish setup should score >= 40, got " + result.getTotalScore());
    }

    @Test
    void score_bullMarket_returnsLowScore() {
        // QQQ near all-time high, TQQQ rising → no signal
        List<TqqqOhlcv> qqq = makeOhlcv("QQQ", 65);
        List<TqqqOhlcv> tqqq = makeOhlcv("TQQQ", 65);
        TqqqScoringService.ScoreResult result = scoringService.calculateScore(qqq, tqqq);
        assertTrue(result.getTotalScore() < 40,
            "Bull market should score < 40, got " + result.getTotalScore());
    }

    @Test
    void score_components_sumToTotal() {
        List<TqqqOhlcv> qqq = makeOhlcv("QQQ", 65);
        List<TqqqOhlcv> tqqq = makeOhlcv("TQQQ", 65);
        TqqqScoringService.ScoreResult r = scoringService.calculateScore(qqq, tqqq);
        int sum = r.getDrawdownScore() + r.getRsiScore() + r.getMacdScore()
                + r.getBbScore() + r.getAtrScore();
        assertEquals(r.getTotalScore(), sum);
    }

    // helpers
    private List<TqqqOhlcv> makeOhlcv(String symbol, int n) {
        List<TqqqOhlcv> list = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            double price = 100.0 + i * 0.5;
            list.add(ohlcv(symbol, i, price + 0.5, price + 1, price - 0.5, price));
        }
        return list;
    }

    private TqqqOhlcv ohlcv(String symbol, int dayOffset, double open, double high, double low, double close) {
        TqqqOhlcv r = new TqqqOhlcv();
        r.setSymbol(symbol);
        r.setTradeDate(LocalDate.of(2024, 1, 1).plusDays(dayOffset));
        r.setOpenPrice(BigDecimal.valueOf(open));
        r.setHighPrice(BigDecimal.valueOf(high));
        r.setLowPrice(BigDecimal.valueOf(low));
        r.setClosePrice(BigDecimal.valueOf(close));
        r.setAdjustedClose(BigDecimal.valueOf(close));
        return r;
    }
}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && mvn test -Dtest=TqqqScoringServiceTest -q 2>&1 | tail -10
```
Expected: compilation error (class not found)

- [ ] **Step 3: Create TqqqScoringService**

```java
// backend/src/main/java/com/stock/investment/service/TqqqScoringService.java
package com.stock.investment.service;

import com.stock.investment.entity.TqqqOhlcv;
import lombok.Getter;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class TqqqScoringService {

    private final TqqqIndicatorService indicatorService;

    // Minimum bars required: 60 for drawdown, 35 for MACD, 21 for BB (use 65 to be safe)
    private static final int MIN_BARS = 65;

    public ScoreResult calculateScore(List<TqqqOhlcv> qqqData, List<TqqqOhlcv> tqqqData) {
        if (qqqData.size() < MIN_BARS || tqqqData.size() < MIN_BARS) {
            return ScoreResult.zero();
        }

        List<BigDecimal> qqqCloses  = closes(qqqData);
        List<BigDecimal> tqqqCloses = closes(tqqqData);
        List<BigDecimal> tqqqHighs  = highs(tqqqData);
        List<BigDecimal> tqqqLows   = lows(tqqqData);

        // 1. Drawdown score (25 pts) — based on QQQ
        double drawdownPct = indicatorService.calculateDrawdownFromHigh(qqqCloses, 60);
        int drawdownScore = scoreDrawdown(drawdownPct);

        // 2. RSI score (25 pts) — based on TQQQ
        double rsi = indicatorService.calculateRsi(tqqqCloses, 14);
        int rsiScore = scoreRsi(rsi);

        // 3. MACD score (20 pts) — based on TQQQ, need prev histogram too
        double[] macdNow  = indicatorService.calculateMacd(tqqqCloses, 12, 26, 9);
        List<BigDecimal> prevCloses = tqqqCloses.subList(0, tqqqCloses.size() - 1);
        double[] macdPrev = prevCloses.size() >= MIN_BARS
            ? indicatorService.calculateMacd(prevCloses, 12, 26, 9)
            : new double[]{0, 0, 0};
        int macdScore = scoreMacd(macdPrev[2], macdNow[2]);

        // 4. Bollinger Band score (15 pts) — based on TQQQ
        double bbZScore = indicatorService.calculateBollingerZScore(tqqqCloses, 20, 2.0);
        int bbScore = scoreBollingerBand(bbZScore);

        // 5. ATR score (15 pts) — based on TQQQ
        double atrNow  = indicatorService.calculateAtr(tqqqHighs, tqqqLows, tqqqCloses, 14);
        double atrMean = atrMean60(tqqqHighs, tqqqLows, tqqqCloses);
        int atrScore = scoreAtr(atrNow, atrMean);

        int total = drawdownScore + rsiScore + macdScore + bbScore + atrScore;
        return new ScoreResult(total, drawdownScore, rsiScore, macdScore, bbScore, atrScore,
                               drawdownPct, rsi);
    }

    // --- scoring rules ---

    private int scoreDrawdown(double pct) {
        if (pct > -10) return 5;
        if (pct > -20) return 15;
        return 25;
    }

    private int scoreRsi(double rsi) {
        if (rsi > 50)  return 0;
        if (rsi > 40)  return 5;
        if (rsi > 30)  return 15;
        return 25;
    }

    private int scoreMacd(double prevHistogram, double currentHistogram) {
        // Cross from negative to positive
        if (prevHistogram < 0 && currentHistogram > 0) return 20;
        // Both negative but shrinking (bottom forming)
        if (currentHistogram < 0 && prevHistogram < 0 && currentHistogram > prevHistogram) return 10;
        return 0;
    }

    private int scoreBollingerBand(double zScore) {
        if (zScore < -2.0) return 15;  // Below lower band
        if (zScore < -1.5) return 8;   // Within 5% of lower band (approx)
        return 0;
    }

    private int scoreAtr(double atrNow, double atrMean60) {
        double ratio = atrMean60 > 0 ? atrNow / atrMean60 : 1.0;
        // ATR was elevated (>1.5x mean) but now falling back — panic subsiding
        if (ratio > 1.0 && ratio < 1.5) return 15; // returning from elevated
        if (ratio <= 1.5) return 5;  // normal range
        return 0;  // still spiking
    }

    /** Average ATR over last 60 bars */
    private double atrMean60(List<BigDecimal> highs, List<BigDecimal> lows, List<BigDecimal> closes) {
        int n = highs.size();
        double sum = 0;
        int count = Math.min(60, n - 15);
        for (int i = n - count; i < n; i++) {
            List<BigDecimal> h = highs.subList(0, i + 1);
            List<BigDecimal> l = lows.subList(0, i + 1);
            List<BigDecimal> c = closes.subList(0, i + 1);
            if (h.size() >= 15) sum += indicatorService.calculateAtr(h, l, c, 14);
        }
        return count > 0 ? sum / count : 1.0;
    }

    // --- data extraction helpers ---
    private List<BigDecimal> closes(List<TqqqOhlcv> data) {
        return data.stream().map(TqqqOhlcv::getClosePrice).collect(Collectors.toList());
    }
    private List<BigDecimal> highs(List<TqqqOhlcv> data) {
        return data.stream().map(TqqqOhlcv::getHighPrice).collect(Collectors.toList());
    }
    private List<BigDecimal> lows(List<TqqqOhlcv> data) {
        return data.stream().map(TqqqOhlcv::getLowPrice).collect(Collectors.toList());
    }

    // --- result DTO ---

    @Getter
    public static class ScoreResult {
        private final int totalScore;
        private final int drawdownScore;
        private final int rsiScore;
        private final int macdScore;
        private final int bbScore;
        private final int atrScore;
        private final double qqqDrawdownPct;
        private final double tqqqRsi;

        public ScoreResult(int totalScore, int drawdownScore, int rsiScore,
                           int macdScore, int bbScore, int atrScore,
                           double qqqDrawdownPct, double tqqqRsi) {
            this.totalScore   = totalScore;
            this.drawdownScore = drawdownScore;
            this.rsiScore     = rsiScore;
            this.macdScore    = macdScore;
            this.bbScore      = bbScore;
            this.atrScore     = atrScore;
            this.qqqDrawdownPct = qqqDrawdownPct;
            this.tqqqRsi      = tqqqRsi;
        }

        public static ScoreResult zero() {
            return new ScoreResult(0, 0, 0, 0, 0, 0, 0.0, 0.0);
        }
    }
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && mvn test -Dtest=TqqqScoringServiceTest -q 2>&1 | tail -10
```
Expected: `BUILD SUCCESS`, `Tests run: 4, Failures: 0`

- [ ] **Step 5: Commit**

```bash
git add backend/src/main/java/com/stock/investment/service/TqqqScoringService.java
git add backend/src/test/java/com/stock/investment/service/TqqqScoringServiceTest.java
git commit -m "feat: add TqqqScoringService with 5-dimension composite score"
```

---

## Task 7: TqqqPosition Entity, Repository, and PositionService

**Files:**
- Create: `backend/src/main/java/com/stock/investment/entity/TqqqPosition.java`
- Create: `backend/src/main/java/com/stock/investment/repository/TqqqPositionRepository.java`
- Create: `backend/src/main/java/com/stock/investment/service/TqqqPositionService.java`
- Create: `backend/src/test/java/com/stock/investment/service/TqqqPositionServiceTest.java`
- Create: `backend/src/main/java/com/stock/investment/dto/TqqqPositionRequest.java`
- Create: `backend/src/main/java/com/stock/investment/dto/TqqqPositionResponse.java`

- [ ] **Step 1: Create TqqqPosition entity**

```java
// backend/src/main/java/com/stock/investment/entity/TqqqPosition.java
package com.stock.investment.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(name = "tqqq_positions")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class TqqqPosition {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "buy_date", nullable = false)
    private LocalDate buyDate;

    @Column(nullable = false, precision = 15, scale = 4)
    private BigDecimal shares;

    @Column(name = "price_per_share", nullable = false, precision = 15, scale = 4)
    private BigDecimal pricePerShare;

    @Column(name = "total_cost", nullable = false, precision = 15, scale = 2)
    private BigDecimal totalCost;

    @Column(length = 500)
    private String notes;

    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() { createdAt = LocalDateTime.now(); }
}
```

- [ ] **Step 2: Create TqqqPositionRepository**

```java
// backend/src/main/java/com/stock/investment/repository/TqqqPositionRepository.java
package com.stock.investment.repository;

import com.stock.investment.entity.TqqqPosition;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface TqqqPositionRepository extends JpaRepository<TqqqPosition, Long> {
    List<TqqqPosition> findByUserIdOrderByBuyDateAsc(Long userId);
}
```

- [ ] **Step 3: Create DTOs**

```java
// backend/src/main/java/com/stock/investment/dto/TqqqPositionRequest.java
package com.stock.investment.dto;

import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDate;

@Data
public class TqqqPositionRequest {
    private LocalDate buyDate;
    private BigDecimal shares;
    private BigDecimal pricePerShare;
    private String notes;
}
```

```java
// backend/src/main/java/com/stock/investment/dto/TqqqPositionResponse.java
package com.stock.investment.dto;

import lombok.Data;
import java.math.BigDecimal;

@Data
public class TqqqPositionResponse {
    private BigDecimal avgCostPerShare;
    private BigDecimal totalShares;
    private BigDecimal totalInvested;
    private BigDecimal currentPrice;
    private BigDecimal currentValue;
    private double unrealizedPnlPct;
    private BigDecimal remainingBudget;
    private String alertLevel;       // NONE, YELLOW, ORANGE, RED
    private String alertMessage;
}
```

- [ ] **Step 4: Write failing tests**

```java
// backend/src/test/java/com/stock/investment/service/TqqqPositionServiceTest.java
package com.stock.investment.service;

import com.stock.investment.entity.TqqqPosition;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class TqqqPositionServiceTest {

    private final TqqqPositionService service = new TqqqPositionService(null);

    @Test
    void avgCost_singlePosition_returnsEntryPrice() {
        List<TqqqPosition> positions = List.of(
            position(BigDecimal.valueOf(10), BigDecimal.valueOf(50.0))
        );
        double avg = service.calculateAvgCost(positions);
        assertEquals(50.0, avg, 0.001);
    }

    @Test
    void avgCost_twoPositions_returnsWeightedAvg() {
        // 10 shares at $50 + 20 shares at $40 = $500 + $800 = $1300 / 30 = $43.33
        List<TqqqPosition> positions = List.of(
            position(BigDecimal.valueOf(10), BigDecimal.valueOf(50.0)),
            position(BigDecimal.valueOf(20), BigDecimal.valueOf(40.0))
        );
        double avg = service.calculateAvgCost(positions);
        assertEquals(43.333, avg, 0.001);
    }

    @Test
    void alertLevel_pnlMinus26pct_returnsOrange() {
        String alert = service.determineAlertLevel(-26.0, false, false);
        assertEquals("ORANGE", alert);
    }

    @Test
    void alertLevel_pnlMinus18pct_returnsYellow() {
        String alert = service.determineAlertLevel(-18.0, false, false);
        assertEquals("YELLOW", alert);
    }

    @Test
    void alertLevel_qqqBelowMa200_returnsRed() {
        String alert = service.determineAlertLevel(-10.0, true, false);
        assertEquals("RED", alert);
    }

    @Test
    void alertLevel_noProblem_returnsNone() {
        String alert = service.determineAlertLevel(-5.0, false, false);
        assertEquals("NONE", alert);
    }

    @Test
    void remainingBudget_partiallyUsed_returnsCorrect() {
        List<TqqqPosition> positions = List.of(
            position(BigDecimal.valueOf(10), BigDecimal.valueOf(50.0)),  // $500
            position(BigDecimal.valueOf(20), BigDecimal.valueOf(40.0))   // $800
        );
        double remaining = service.calculateRemainingBudget(positions, 10000.0);
        assertEquals(8700.0, remaining, 0.01);
    }

    private TqqqPosition position(BigDecimal shares, BigDecimal price) {
        TqqqPosition p = new TqqqPosition();
        p.setShares(shares);
        p.setPricePerShare(price);
        p.setTotalCost(shares.multiply(price));
        p.setBuyDate(LocalDate.now());
        return p;
    }
}
```

- [ ] **Step 5: Run tests to verify they fail**

```bash
cd backend && mvn test -Dtest=TqqqPositionServiceTest -q 2>&1 | tail -10
```
Expected: compilation error (class not found)

- [ ] **Step 6: Create TqqqPositionService**

```java
// backend/src/main/java/com/stock/investment/service/TqqqPositionService.java
package com.stock.investment.service;

import com.stock.investment.dto.TqqqPositionRequest;
import com.stock.investment.dto.TqqqPositionResponse;
import com.stock.investment.entity.TqqqPosition;
import com.stock.investment.repository.TqqqPositionRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;

@Service
@RequiredArgsConstructor
public class TqqqPositionService {

    private final TqqqPositionRepository positionRepository;

    private static final double BUDGET = 10000.0;

    public TqqqPosition addPosition(Long userId, TqqqPositionRequest request) {
        TqqqPosition position = new TqqqPosition();
        position.setUserId(userId);
        position.setBuyDate(request.getBuyDate());
        position.setShares(request.getShares());
        position.setPricePerShare(request.getPricePerShare());
        position.setTotalCost(request.getShares().multiply(request.getPricePerShare()));
        position.setNotes(request.getNotes());
        return positionRepository.save(position);
    }

    public TqqqPositionResponse getSummary(Long userId, BigDecimal currentTqqqPrice,
                                            boolean qqqBelowMa200, boolean qqqThreeRedMonths) {
        List<TqqqPosition> positions = positionRepository.findByUserIdOrderByBuyDateAsc(userId);

        BigDecimal totalShares = positions.stream()
            .map(TqqqPosition::getShares)
            .reduce(BigDecimal.ZERO, BigDecimal::add);

        BigDecimal totalInvested = positions.stream()
            .map(TqqqPosition::getTotalCost)
            .reduce(BigDecimal.ZERO, BigDecimal::add);

        BigDecimal avgCost = totalShares.compareTo(BigDecimal.ZERO) > 0
            ? totalInvested.divide(totalShares, 4, RoundingMode.HALF_UP)
            : BigDecimal.ZERO;

        BigDecimal currentValue = totalShares.multiply(currentTqqqPrice);
        double pnlPct = totalInvested.compareTo(BigDecimal.ZERO) > 0
            ? currentValue.subtract(totalInvested)
                .divide(totalInvested, 6, RoundingMode.HALF_UP)
                .doubleValue() * 100.0
            : 0.0;

        String alertLevel = determineAlertLevel(pnlPct, qqqBelowMa200, qqqThreeRedMonths);
        String alertMessage = buildAlertMessage(alertLevel, pnlPct);
        double remaining = calculateRemainingBudget(positions, BUDGET);

        TqqqPositionResponse response = new TqqqPositionResponse();
        response.setAvgCostPerShare(avgCost);
        response.setTotalShares(totalShares);
        response.setTotalInvested(totalInvested);
        response.setCurrentPrice(currentTqqqPrice);
        response.setCurrentValue(currentValue);
        response.setUnrealizedPnlPct(pnlPct);
        response.setRemainingBudget(BigDecimal.valueOf(remaining));
        response.setAlertLevel(alertLevel);
        response.setAlertMessage(alertMessage);
        return response;
    }

    /** Package-visible for tests */
    double calculateAvgCost(List<TqqqPosition> positions) {
        BigDecimal totalCost   = positions.stream().map(TqqqPosition::getTotalCost)
            .reduce(BigDecimal.ZERO, BigDecimal::add);
        BigDecimal totalShares = positions.stream().map(TqqqPosition::getShares)
            .reduce(BigDecimal.ZERO, BigDecimal::add);
        if (totalShares.compareTo(BigDecimal.ZERO) == 0) return 0.0;
        return totalCost.divide(totalShares, 6, RoundingMode.HALF_UP).doubleValue();
    }

    /** Package-visible for tests */
    String determineAlertLevel(double pnlPct, boolean qqqBelowMa200_10days, boolean qqqThreeRedMonths) {
        if (qqqBelowMa200_10days || qqqThreeRedMonths) return "RED";
        if (pnlPct < -40) return "ORANGE";
        if (pnlPct < -25) return "YELLOW";
        return "NONE";
    }

    /** Package-visible for tests */
    double calculateRemainingBudget(List<TqqqPosition> positions, double totalBudget) {
        double used = positions.stream()
            .mapToDouble(p -> p.getTotalCost().doubleValue())
            .sum();
        return Math.max(0, totalBudget - used);
    }

    private String buildAlertMessage(String level, double pnlPct) {
        return switch (level) {
            case "RED"    -> "宏观趋势恶化，暂停所有买入，评估是否离场";
            case "ORANGE" -> String.format("浮亏 %.1f%%，考虑减仓 50%% 保留子弹", pnlPct);
            case "YELLOW" -> String.format("浮亏 %.1f%%，暂停新买入，等待反弹信号", pnlPct);
            default       -> "";
        };
    }
}
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
cd backend && mvn test -Dtest=TqqqPositionServiceTest -q 2>&1 | tail -10
```
Expected: `BUILD SUCCESS`, `Tests run: 6, Failures: 0`

- [ ] **Step 8: Compile full project**

```bash
cd backend && mvn compile -q
```
Expected: `BUILD SUCCESS`

- [ ] **Step 9: Commit**

```bash
git add backend/src/main/java/com/stock/investment/entity/TqqqPosition.java
git add backend/src/main/java/com/stock/investment/repository/TqqqPositionRepository.java
git add backend/src/main/java/com/stock/investment/service/TqqqPositionService.java
git add backend/src/main/java/com/stock/investment/dto/TqqqPositionRequest.java
git add backend/src/main/java/com/stock/investment/dto/TqqqPositionResponse.java
git add backend/src/test/java/com/stock/investment/service/TqqqPositionServiceTest.java
git commit -m "feat: add TqqqPosition entity, repository, and position tracking service"
```

---

## Task 8: TqqqSignal Entity, Repository, and Signal Generation

**Files:**
- Create: `backend/src/main/java/com/stock/investment/entity/TqqqSignal.java`
- Create: `backend/src/main/java/com/stock/investment/repository/TqqqSignalRepository.java`
- Create: `backend/src/main/java/com/stock/investment/dto/TqqqSignalResponse.java`

- [ ] **Step 1: Create TqqqSignal entity**

```java
// backend/src/main/java/com/stock/investment/entity/TqqqSignal.java
package com.stock.investment.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(name = "tqqq_signals")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class TqqqSignal {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "signal_date", nullable = false)
    private LocalDate signalDate;

    @Column(name = "total_score", nullable = false)
    private Integer totalScore;

    @Column(name = "drawdown_score")
    private Integer drawdownScore;

    @Column(name = "rsi_score")
    private Integer rsiScore;

    @Column(name = "macd_score")
    private Integer macdScore;

    @Column(name = "bb_score")
    private Integer bbScore;

    @Column(name = "atr_score")
    private Integer atrScore;

    @Column(name = "qqq_drawdown_pct", precision = 8, scale = 4)
    private BigDecimal qqqDrawdownPct;

    @Column(name = "tqqq_rsi", precision = 8, scale = 4)
    private BigDecimal tqqqRsi;

    @Column(name = "suggested_amount", precision = 15, scale = 2)
    private BigDecimal suggestedAmount;

    @Column(name = "alert_level", length = 20)
    private String alertLevel;

    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() { createdAt = LocalDateTime.now(); }
}
```

- [ ] **Step 2: Create TqqqSignalRepository**

```java
// backend/src/main/java/com/stock/investment/repository/TqqqSignalRepository.java
package com.stock.investment.repository;

import com.stock.investment.entity.TqqqSignal;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

@Repository
public interface TqqqSignalRepository extends JpaRepository<TqqqSignal, Long> {
    Optional<TqqqSignal> findBySignalDate(LocalDate date);
    List<TqqqSignal> findTop30ByOrderBySignalDateDesc();
}
```

- [ ] **Step 3: Create TqqqSignalResponse DTO**

```java
// backend/src/main/java/com/stock/investment/dto/TqqqSignalResponse.java
package com.stock.investment.dto;

import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDate;

@Data
public class TqqqSignalResponse {
    private LocalDate signalDate;
    private int totalScore;
    private int drawdownScore;
    private int rsiScore;
    private int macdScore;
    private int bbScore;
    private int atrScore;
    private double qqqDrawdownPct;
    private double tqqqRsi;
    private BigDecimal suggestedAmount;
    private String alertLevel;
    private String alertMessage;
    private boolean buySignalActive;  // true if score >= 40 AND alertLevel != RED
}
```

- [ ] **Step 4: Compile**

```bash
cd backend && mvn compile -q
```
Expected: `BUILD SUCCESS`

- [ ] **Step 5: Commit**

```bash
git add backend/src/main/java/com/stock/investment/entity/TqqqSignal.java
git add backend/src/main/java/com/stock/investment/repository/TqqqSignalRepository.java
git add backend/src/main/java/com/stock/investment/dto/TqqqSignalResponse.java
git commit -m "feat: add TqqqSignal entity, repository, and signal response DTO"
```

---

## Task 9: TqqqBacktestService

**Files:**
- Create: `backend/src/main/java/com/stock/investment/service/TqqqBacktestService.java`
- Create: `backend/src/main/java/com/stock/investment/dto/TqqqBacktestRequest.java`
- Create: `backend/src/main/java/com/stock/investment/dto/TqqqBacktestResult.java`
- Create: `backend/src/test/java/com/stock/investment/service/TqqqBacktestServiceTest.java`

- [ ] **Step 1: Create DTOs**

```java
// backend/src/main/java/com/stock/investment/dto/TqqqBacktestRequest.java
package com.stock.investment.dto;

import lombok.Data;
import java.time.LocalDate;

@Data
public class TqqqBacktestRequest {
    private LocalDate startDate;
    private LocalDate endDate;
    private double budget;          // total budget to deploy, default 10000
    private double initialPosition; // starting value already invested, default 0
    // Score weight overrides (0-25, 0-25, 0-20, 0-15, 0-15). null = use defaults.
    private Integer drawdownWeight;
    private Integer rsiWeight;
    private Integer macdWeight;
    private Integer bbWeight;
    private Integer atrWeight;
}
```

```java
// backend/src/main/java/com/stock/investment/dto/TqqqBacktestResult.java
package com.stock.investment.dto;

import lombok.Data;
import java.util.List;

@Data
public class TqqqBacktestResult {
    private double totalReturn;         // %
    private double maxDrawdown;         // %
    private double finalValue;
    private double totalInvested;
    private int signalCount;
    private double avgCostPerShare;
    private double lumpSumReturn;       // % if bought all at startDate
    private List<DailySnapshot> snapshots; // for equity curve chart

    @Data
    public static class DailySnapshot {
        private String date;
        private double portfolioValue;
        private double invested;
        private int score;
    }
}
```

- [ ] **Step 2: Write failing tests**

```java
// backend/src/test/java/com/stock/investment/service/TqqqBacktestServiceTest.java
package com.stock.investment.service;

import com.stock.investment.dto.TqqqBacktestRequest;
import com.stock.investment.dto.TqqqBacktestResult;
import com.stock.investment.entity.TqqqOhlcv;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class TqqqBacktestServiceTest {

    private TqqqBacktestService backtestService;

    @BeforeEach
    void setUp() {
        backtestService = new TqqqBacktestService(
            new TqqqScoringService(new TqqqIndicatorService()));
    }

    @Test
    void backtest_insufficientData_returnsZeroResult() {
        List<TqqqOhlcv> qqq = makeOhlcv("QQQ", 10, 100.0, 0.5);
        List<TqqqOhlcv> tqqq = makeOhlcv("TQQQ", 10, 30.0, 0.5);
        TqqqBacktestRequest req = new TqqqBacktestRequest();
        req.setBudget(10000);
        TqqqBacktestResult result = backtestService.runBacktest(qqq, tqqq, req);
        assertEquals(0.0, result.getTotalInvested(), 0.01);
    }

    @Test
    void backtest_risingMarket_noSignalsTriggered() {
        // Steadily rising market → low score → no buys
        List<TqqqOhlcv> qqq = makeOhlcv("QQQ", 120, 300.0, 1.0);
        List<TqqqOhlcv> tqqq = makeOhlcv("TQQQ", 120, 50.0, 0.3);
        TqqqBacktestRequest req = new TqqqBacktestRequest();
        req.setBudget(10000);
        TqqqBacktestResult result = backtestService.runBacktest(qqq, tqqq, req);
        assertEquals(0, result.getSignalCount());
    }

    @Test
    void backtest_budgetNeverExceeded() {
        List<TqqqOhlcv> qqq = crashThenRecover("QQQ", 120);
        List<TqqqOhlcv> tqqq = crashThenRecover("TQQQ", 120);
        TqqqBacktestRequest req = new TqqqBacktestRequest();
        req.setBudget(10000);
        TqqqBacktestResult result = backtestService.runBacktest(qqq, tqqq, req);
        assertTrue(result.getTotalInvested() <= 10000.0 + 0.01,
            "Total invested should not exceed budget: " + result.getTotalInvested());
    }

    @Test
    void backtest_snapshotsNotEmpty() {
        List<TqqqOhlcv> qqq = crashThenRecover("QQQ", 120);
        List<TqqqOhlcv> tqqq = crashThenRecover("TQQQ", 120);
        TqqqBacktestRequest req = new TqqqBacktestRequest();
        req.setBudget(10000);
        TqqqBacktestResult result = backtestService.runBacktest(qqq, tqqq, req);
        assertFalse(result.getSnapshots().isEmpty());
    }

    // helpers
    private List<TqqqOhlcv> makeOhlcv(String symbol, int n, double start, double step) {
        List<TqqqOhlcv> list = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            double price = start + i * step;
            list.add(ohlcv(symbol, i, price));
        }
        return list;
    }

    private List<TqqqOhlcv> crashThenRecover(String symbol, int n) {
        List<TqqqOhlcv> list = new ArrayList<>();
        double base = "QQQ".equals(symbol) ? 300.0 : 50.0;
        for (int i = 0; i < n; i++) {
            double price = i < 60 ? base - i * 1.5 : base - 90 + (i - 60) * 1.5;
            list.add(ohlcv(symbol, i, Math.max(price, 1.0)));
        }
        return list;
    }

    private TqqqOhlcv ohlcv(String symbol, int dayOffset, double price) {
        TqqqOhlcv r = new TqqqOhlcv();
        r.setSymbol(symbol);
        r.setTradeDate(LocalDate.of(2024, 1, 1).plusDays(dayOffset));
        r.setOpenPrice(BigDecimal.valueOf(price));
        r.setHighPrice(BigDecimal.valueOf(price * 1.01));
        r.setLowPrice(BigDecimal.valueOf(price * 0.99));
        r.setClosePrice(BigDecimal.valueOf(price));
        r.setAdjustedClose(BigDecimal.valueOf(price));
        return r;
    }
}
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd backend && mvn test -Dtest=TqqqBacktestServiceTest -q 2>&1 | tail -10
```
Expected: compilation error

- [ ] **Step 4: Create TqqqBacktestService**

```java
// backend/src/main/java/com/stock/investment/service/TqqqBacktestService.java
package com.stock.investment.service;

import com.stock.investment.dto.TqqqBacktestRequest;
import com.stock.investment.dto.TqqqBacktestResult;
import com.stock.investment.entity.TqqqOhlcv;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

@Service
@RequiredArgsConstructor
public class TqqqBacktestService {

    private final TqqqScoringService scoringService;

    private static final int MIN_HISTORY = 65;

    public TqqqBacktestResult runBacktest(List<TqqqOhlcv> qqqAll,
                                          List<TqqqOhlcv> tqqqAll,
                                          TqqqBacktestRequest request) {
        TqqqBacktestResult result = new TqqqBacktestResult();
        result.setSnapshots(new ArrayList<>());

        if (qqqAll.size() < MIN_HISTORY || tqqqAll.size() < MIN_HISTORY) {
            result.setTotalReturn(0);
            result.setMaxDrawdown(0);
            result.setFinalValue(0);
            result.setTotalInvested(0);
            result.setSignalCount(0);
            result.setAvgCostPerShare(0);
            result.setLumpSumReturn(0);
            return result;
        }

        double budget = request.getBudget();
        double remainingBudget = budget;
        double totalShares = request.getInitialPosition() > 0
            ? request.getInitialPosition() / tqqqAll.get(MIN_HISTORY - 1).getClosePrice().doubleValue()
            : 0;
        double totalInvested = request.getInitialPosition();
        int signalCount = 0;
        double peakValue = 0;
        double maxDrawdown = 0;

        // Walk forward from index MIN_HISTORY to end
        for (int i = MIN_HISTORY; i < Math.min(qqqAll.size(), tqqqAll.size()); i++) {
            List<TqqqOhlcv> qqqWindow  = qqqAll.subList(0, i + 1);
            List<TqqqOhlcv> tqqqWindow = tqqqAll.subList(0, i + 1);

            TqqqScoringService.ScoreResult score = scoringService.calculateScore(qqqWindow, tqqqWindow);
            double tqqqPrice = tqqqAll.get(i).getClosePrice().doubleValue();

            // Buy logic
            if (score.getTotalScore() >= 40 && remainingBudget > 0) {
                double fraction = allocationFraction(score.getTotalScore());
                double amount = Math.min(budget * fraction, remainingBudget);
                double shares = amount / tqqqPrice;
                totalShares += shares;
                totalInvested += amount;
                remainingBudget -= amount;
                signalCount++;
            }

            // Portfolio value snapshot
            double portfolioValue = totalShares * tqqqPrice + remainingBudget;
            if (portfolioValue > peakValue) peakValue = portfolioValue;
            double drawdown = peakValue > 0 ? (portfolioValue - peakValue) / peakValue * 100.0 : 0;
            if (drawdown < maxDrawdown) maxDrawdown = drawdown;

            TqqqBacktestResult.DailySnapshot snap = new TqqqBacktestResult.DailySnapshot();
            snap.setDate(tqqqAll.get(i).getTradeDate().toString());
            snap.setPortfolioValue(portfolioValue);
            snap.setInvested(totalInvested);
            snap.setScore(score.getTotalScore());
            result.getSnapshots().add(snap);
        }

        double finalTqqqPrice = tqqqAll.get(tqqqAll.size() - 1).getClosePrice().doubleValue();
        double finalValue = totalShares * finalTqqqPrice + remainingBudget;
        double totalReturn = totalInvested > 0 ? (finalValue - totalInvested) / totalInvested * 100.0 : 0;

        // Lump-sum comparison: buy all at first eligible day
        double lumpSumPrice = tqqqAll.get(MIN_HISTORY).getClosePrice().doubleValue();
        double lumpSumShares = budget / lumpSumPrice;
        double lumpSumFinal = lumpSumShares * finalTqqqPrice;
        double lumpSumReturn = (lumpSumFinal - budget) / budget * 100.0;

        double avgCost = totalShares > 0 ? totalInvested / totalShares : 0;

        result.setTotalReturn(totalReturn);
        result.setMaxDrawdown(maxDrawdown);
        result.setFinalValue(finalValue);
        result.setTotalInvested(totalInvested);
        result.setSignalCount(signalCount);
        result.setAvgCostPerShare(avgCost);
        result.setLumpSumReturn(lumpSumReturn);
        return result;
    }

    private double allocationFraction(int score) {
        if (score >= 80) return 0.50;
        if (score >= 60) return 0.35;
        return 0.15;
    }
}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend && mvn test -Dtest=TqqqBacktestServiceTest -q 2>&1 | tail -10
```
Expected: `BUILD SUCCESS`, `Tests run: 4, Failures: 0`

- [ ] **Step 6: Commit**

```bash
git add backend/src/main/java/com/stock/investment/service/TqqqBacktestService.java
git add backend/src/main/java/com/stock/investment/dto/TqqqBacktestRequest.java
git add backend/src/main/java/com/stock/investment/dto/TqqqBacktestResult.java
git add backend/src/test/java/com/stock/investment/service/TqqqBacktestServiceTest.java
git commit -m "feat: add TqqqBacktestService with historical replay and lump-sum comparison"
```

---

## Task 10: REST Controller

**Files:**
- Create: `backend/src/main/java/com/stock/investment/controller/TqqqController.java`

- [ ] **Step 1: Create TqqqController**

```java
// backend/src/main/java/com/stock/investment/controller/TqqqController.java
package com.stock.investment.controller;

import com.stock.investment.dto.*;
import com.stock.investment.entity.TqqqOhlcv;
import com.stock.investment.entity.TqqqSignal;
import com.stock.investment.repository.TqqqSignalRepository;
import com.stock.investment.security.JwtTokenProvider;
import com.stock.investment.service.*;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

@RestController
@RequestMapping("/api/tqqq")
@RequiredArgsConstructor
public class TqqqController {

    private final TqqqDataService dataService;
    private final TqqqScoringService scoringService;
    private final TqqqPositionService positionService;
    private final TqqqBacktestService backtestService;
    private final TqqqSignalRepository signalRepository;
    private final UserService userService;

    /** Fetch today's signal. Computes and stores if not already done today. */
    @GetMapping("/signal/today")
    public ResponseEntity<TqqqSignalResponse> getTodaySignal(
            @AuthenticationPrincipal UserDetails userDetails) {
        LocalDate today = LocalDate.now();
        Optional<TqqqSignal> existing = signalRepository.findBySignalDate(today);
        if (existing.isPresent()) {
            return ResponseEntity.ok(toSignalResponse(existing.get(),
                positionService.getSummary(userId(userDetails),
                    latestTqqqPrice(), false, false).getAlertLevel()));
        }

        List<TqqqOhlcv> qqq  = dataService.getOhlcv("QQQ");
        List<TqqqOhlcv> tqqq = dataService.getOhlcv("TQQQ");
        TqqqScoringService.ScoreResult score = scoringService.calculateScore(qqq, tqqq);

        TqqqPositionResponse positionSummary = positionService.getSummary(
            userId(userDetails), latestTqqqPrice(), false, false);

        double suggestedAmount = computeSuggestedAmount(
            score.getTotalScore(), positionSummary.getRemainingBudget().doubleValue());

        TqqqSignal signal = new TqqqSignal();
        signal.setSignalDate(today);
        signal.setTotalScore(score.getTotalScore());
        signal.setDrawdownScore(score.getDrawdownScore());
        signal.setRsiScore(score.getRsiScore());
        signal.setMacdScore(score.getMacdScore());
        signal.setBbScore(score.getBbScore());
        signal.setAtrScore(score.getAtrScore());
        signal.setQqqDrawdownPct(BigDecimal.valueOf(score.getQqqDrawdownPct()));
        signal.setTqqqRsi(BigDecimal.valueOf(score.getTqqqRsi()));
        signal.setSuggestedAmount(BigDecimal.valueOf(suggestedAmount));
        signal.setAlertLevel(positionSummary.getAlertLevel());
        signalRepository.save(signal);

        return ResponseEntity.ok(toSignalResponse(signal, positionSummary.getAlertLevel()));
    }

    /** Last 30 signals for history chart */
    @GetMapping("/signal/history")
    public ResponseEntity<List<TqqqSignal>> getSignalHistory() {
        return ResponseEntity.ok(signalRepository.findTop30ByOrderBySignalDateDesc());
    }

    /** Add a manual buy position */
    @PostMapping("/position")
    public ResponseEntity<Void> addPosition(
            @AuthenticationPrincipal UserDetails userDetails,
            @RequestBody TqqqPositionRequest request) {
        positionService.addPosition(userId(userDetails), request);
        return ResponseEntity.ok().build();
    }

    /** Get position summary (avg cost, P&L, alerts, remaining budget) */
    @GetMapping("/position/summary")
    public ResponseEntity<TqqqPositionResponse> getPositionSummary(
            @AuthenticationPrincipal UserDetails userDetails) {
        BigDecimal currentPrice = latestTqqqPrice();
        // MA200 and 3-red-month checks are simplified here; extend later if needed
        return ResponseEntity.ok(positionService.getSummary(
            userId(userDetails), currentPrice, false, false));
    }

    /** Seed full 5-year history (admin/manual trigger) */
    @PostMapping("/data/load-history")
    public ResponseEntity<String> loadHistory() {
        dataService.loadFullHistory();
        return ResponseEntity.ok("History loading started");
    }

    /** Refresh last 100 days of data */
    @PostMapping("/data/refresh")
    public ResponseEntity<String> refreshData() {
        dataService.refreshDailyData();
        return ResponseEntity.ok("Data refresh started");
    }

    /** Run backtest with given config */
    @PostMapping("/backtest")
    public ResponseEntity<TqqqBacktestResult> runBacktest(
            @RequestBody TqqqBacktestRequest request) {
        List<TqqqOhlcv> qqq  = dataService.getOhlcv("QQQ");
        List<TqqqOhlcv> tqqq = dataService.getOhlcv("TQQQ");

        // Filter by date range if specified
        if (request.getStartDate() != null) {
            qqq  = qqq.stream().filter(o -> !o.getTradeDate().isBefore(request.getStartDate())).toList();
            tqqq = tqqq.stream().filter(o -> !o.getTradeDate().isBefore(request.getStartDate())).toList();
        }
        if (request.getEndDate() != null) {
            qqq  = qqq.stream().filter(o -> !o.getTradeDate().isAfter(request.getEndDate())).toList();
            tqqq = tqqq.stream().filter(o -> !o.getTradeDate().isAfter(request.getEndDate())).toList();
        }

        return ResponseEntity.ok(backtestService.runBacktest(qqq, tqqq, request));
    }

    // helpers

    private BigDecimal latestTqqqPrice() {
        List<TqqqOhlcv> data = dataService.getOhlcv("TQQQ");
        if (data.isEmpty()) return BigDecimal.ZERO;
        return data.get(data.size() - 1).getClosePrice();
    }

    private Long userId(UserDetails userDetails) {
        return userService.findByUsername(userDetails.getUsername()).getId();
    }

    private double computeSuggestedAmount(int score, double remainingBudget) {
        if (score < 40) return 0;
        if (score >= 80) return remainingBudget * 0.50;
        if (score >= 60) return remainingBudget * 0.35;
        return remainingBudget * 0.15;
    }

    private TqqqSignalResponse toSignalResponse(TqqqSignal signal, String alertLevel) {
        TqqqSignalResponse r = new TqqqSignalResponse();
        r.setSignalDate(signal.getSignalDate());
        r.setTotalScore(signal.getTotalScore());
        r.setDrawdownScore(signal.getDrawdownScore() != null ? signal.getDrawdownScore() : 0);
        r.setRsiScore(signal.getRsiScore() != null ? signal.getRsiScore() : 0);
        r.setMacdScore(signal.getMacdScore() != null ? signal.getMacdScore() : 0);
        r.setBbScore(signal.getBbScore() != null ? signal.getBbScore() : 0);
        r.setAtrScore(signal.getAtrScore() != null ? signal.getAtrScore() : 0);
        r.setQqqDrawdownPct(signal.getQqqDrawdownPct() != null ? signal.getQqqDrawdownPct().doubleValue() : 0);
        r.setTqqqRsi(signal.getTqqqRsi() != null ? signal.getTqqqRsi().doubleValue() : 0);
        r.setSuggestedAmount(signal.getSuggestedAmount());
        r.setAlertLevel(alertLevel);
        r.setBuySignalActive(signal.getTotalScore() >= 40 && !"RED".equals(alertLevel));
        return r;
    }
}
```

- [ ] **Step 2: Add findByUsername to UserService (check if exists first)**

Read `backend/src/main/java/com/stock/investment/service/UserService.java`. If `findByUsername` doesn't exist, add:
```java
public User findByUsername(String username) {
    return userRepository.findByUsername(username)
        .orElseThrow(() -> new RuntimeException("User not found: " + username));
}
```

- [ ] **Step 3: Compile**

```bash
cd backend && mvn compile -q
```
Expected: `BUILD SUCCESS`

- [ ] **Step 4: Commit**

```bash
git add backend/src/main/java/com/stock/investment/controller/TqqqController.java
git add backend/src/main/java/com/stock/investment/service/UserService.java
git commit -m "feat: add TqqqController with signal, position, backtest endpoints"
```

---

## Task 11: Frontend API Module

**Files:**
- Create: `frontend/src/api/tqqq.js`

- [ ] **Step 1: Create tqqq.js**

```javascript
// frontend/src/api/tqqq.js
import api from './axios'

export const tqqqApi = {
  getTodaySignal() {
    return api.get('/tqqq/signal/today')
  },
  getSignalHistory() {
    return api.get('/tqqq/signal/history')
  },
  addPosition(data) {
    return api.post('/tqqq/position', data)
  },
  getPositionSummary() {
    return api.get('/tqqq/position/summary')
  },
  runBacktest(config) {
    return api.post('/tqqq/backtest', config)
  },
  loadHistory() {
    return api.post('/tqqq/data/load-history')
  },
  refreshData() {
    return api.post('/tqqq/data/refresh')
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/tqqq.js
git commit -m "feat: add tqqq frontend API module"
```

---

## Task 12: Frontend — SignalPanel Component

**Files:**
- Create: `frontend/src/components/tqqq/SignalPanel.vue`

- [ ] **Step 1: Create SignalPanel.vue**

```vue
<!-- frontend/src/components/tqqq/SignalPanel.vue -->
<template>
  <div class="bg-white rounded-lg shadow p-6">
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-lg font-semibold text-gray-900">今日信号</h2>
      <span class="text-sm text-gray-500">{{ signal?.signalDate }}</span>
    </div>

    <div v-if="loading" class="text-gray-400 text-sm">加载中...</div>
    <div v-else-if="error" class="text-red-500 text-sm">{{ error }}</div>
    <div v-else-if="signal">
      <!-- Total Score -->
      <div class="flex items-center gap-4 mb-6">
        <div class="relative w-24 h-24">
          <svg class="w-24 h-24 -rotate-90" viewBox="0 0 36 36">
            <circle cx="18" cy="18" r="15.9" fill="none" stroke="#e5e7eb" stroke-width="3" />
            <circle cx="18" cy="18" r="15.9" fill="none"
              :stroke="scoreColor"
              stroke-width="3"
              stroke-dasharray="100"
              :stroke-dashoffset="100 - signal.totalScore"
              stroke-linecap="round" />
          </svg>
          <div class="absolute inset-0 flex flex-col items-center justify-center">
            <span class="text-2xl font-bold" :class="scoreTextColor">{{ signal.totalScore }}</span>
            <span class="text-xs text-gray-400">/ 100</span>
          </div>
        </div>
        <div>
          <div class="text-sm font-medium" :class="scoreTextColor">{{ scoreLabel }}</div>
          <div v-if="signal.buySignalActive" class="mt-1">
            <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
              买入信号激活
            </span>
            <div class="mt-1 text-sm text-gray-600">
              建议投入：<span class="font-semibold text-green-700">${{ formatAmount(signal.suggestedAmount) }}</span>
            </div>
          </div>
          <div v-else-if="signal.alertLevel === 'RED'" class="mt-1">
            <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
              红色预警 — 买入已屏蔽
            </span>
          </div>
          <div v-else class="mt-1 text-sm text-gray-400">信号不足（&lt; 40分），暂不操作</div>
        </div>
      </div>

      <!-- Score breakdown -->
      <div class="space-y-2">
        <div class="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">评分明细</div>
        <ScoreRow label="QQQ 回撤" :score="signal.drawdownScore" :max="25"
          :detail="`回撤 ${signal.qqqDrawdownPct?.toFixed(1)}%`" />
        <ScoreRow label="RSI 超卖" :score="signal.rsiScore" :max="25"
          :detail="`RSI ${signal.tqqqRsi?.toFixed(1)}`" />
        <ScoreRow label="MACD 状态" :score="signal.macdScore" :max="20" />
        <ScoreRow label="布林带位置" :score="signal.bbScore" :max="15" />
        <ScoreRow label="ATR 波动" :score="signal.atrScore" :max="15" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { tqqqApi } from '@/api/tqqq'
import ScoreRow from './ScoreRow.vue'

const signal = ref(null)
const loading = ref(false)
const error = ref(null)

const scoreColor = computed(() => {
  if (!signal.value) return '#e5e7eb'
  const s = signal.value.totalScore
  if (s >= 80) return '#16a34a'
  if (s >= 60) return '#ca8a04'
  if (s >= 40) return '#2563eb'
  return '#9ca3af'
})

const scoreTextColor = computed(() => {
  if (!signal.value) return 'text-gray-400'
  const s = signal.value.totalScore
  if (s >= 80) return 'text-green-600'
  if (s >= 60) return 'text-yellow-600'
  if (s >= 40) return 'text-blue-600'
  return 'text-gray-400'
})

const scoreLabel = computed(() => {
  if (!signal.value) return ''
  const s = signal.value.totalScore
  if (s >= 80) return '强烈买入信号'
  if (s >= 60) return '中等买入信号'
  if (s >= 40) return '弱买入信号'
  return '无信号'
})

function formatAmount(amount) {
  if (!amount) return '0'
  return Number(amount).toLocaleString('en-US', { maximumFractionDigits: 0 })
}

onMounted(async () => {
  loading.value = true
  try {
    const res = await tqqqApi.getTodaySignal()
    signal.value = res.data
  } catch (e) {
    error.value = e.response?.data?.message || '加载失败'
  } finally {
    loading.value = false
  }
})
</script>
```

- [ ] **Step 2: Create ScoreRow helper component**

```vue
<!-- frontend/src/components/tqqq/ScoreRow.vue -->
<template>
  <div class="flex items-center gap-2">
    <span class="w-24 text-xs text-gray-600 shrink-0">{{ label }}</span>
    <div class="flex-1 bg-gray-100 rounded-full h-2">
      <div class="h-2 rounded-full transition-all"
        :style="{ width: pct + '%', backgroundColor: barColor }"
      />
    </div>
    <span class="w-10 text-right text-xs font-medium" :class="textColor">{{ score }}/{{ max }}</span>
    <span v-if="detail" class="text-xs text-gray-400 w-20 text-right">{{ detail }}</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ label: String, score: Number, max: Number, detail: String })
const pct = computed(() => props.max > 0 ? (props.score / props.max) * 100 : 0)
const barColor = computed(() => pct.value >= 70 ? '#16a34a' : pct.value >= 40 ? '#ca8a04' : '#9ca3af')
const textColor = computed(() => pct.value >= 70 ? 'text-green-600' : pct.value >= 40 ? 'text-yellow-600' : 'text-gray-400')
</script>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/tqqq/
git commit -m "feat: add SignalPanel and ScoreRow components"
```

---

## Task 13: Frontend — PositionPanel Component

**Files:**
- Create: `frontend/src/components/tqqq/PositionPanel.vue`

- [ ] **Step 1: Create PositionPanel.vue**

```vue
<!-- frontend/src/components/tqqq/PositionPanel.vue -->
<template>
  <div class="bg-white rounded-lg shadow p-6">
    <h2 class="text-lg font-semibold text-gray-900 mb-4">持仓状态</h2>

    <!-- Alert banner -->
    <div v-if="summary?.alertLevel && summary.alertLevel !== 'NONE'"
      class="mb-4 p-3 rounded-md text-sm"
      :class="alertClass">
      {{ summary.alertMessage }}
    </div>

    <div v-if="loading" class="text-gray-400 text-sm">加载中...</div>
    <div v-else-if="summary">
      <div class="grid grid-cols-2 gap-4 mb-6">
        <Stat label="平均成本" :value="'$' + fmt(summary.avgCostPerShare)" />
        <Stat label="当前价格" :value="'$' + fmt(summary.currentPrice)" />
        <Stat label="总持股数" :value="fmt(summary.totalShares, 2)" />
        <Stat label="浮盈/亏" :value="pnlText" :color="pnlColor" />
        <Stat label="已用预算" :value="'$' + fmt(summary.totalInvested, 0)" />
        <Stat label="剩余预算" :value="'$' + fmt(summary.remainingBudget, 0)" />
      </div>

      <!-- Add position form -->
      <div class="border-t pt-4">
        <div class="text-sm font-medium text-gray-700 mb-3">记录买入</div>
        <div class="grid grid-cols-2 gap-2">
          <input v-model="form.buyDate" type="date"
            class="col-span-2 border rounded px-2 py-1 text-sm" />
          <input v-model="form.shares" type="number" placeholder="股数"
            class="border rounded px-2 py-1 text-sm" />
          <input v-model="form.pricePerShare" type="number" placeholder="买入价"
            class="border rounded px-2 py-1 text-sm" />
          <input v-model="form.notes" type="text" placeholder="备注（可选）"
            class="col-span-2 border rounded px-2 py-1 text-sm" />
          <button @click="addPosition"
            class="col-span-2 bg-indigo-600 text-white rounded px-3 py-1.5 text-sm hover:bg-indigo-700">
            添加
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { tqqqApi } from '@/api/tqqq'
import Stat from './Stat.vue'

const summary = ref(null)
const loading = ref(false)
const form = ref({ buyDate: '', shares: '', pricePerShare: '', notes: '' })

const pnlText = computed(() => {
  if (!summary.value) return '-'
  const pnl = summary.value.unrealizedPnlPct
  return (pnl >= 0 ? '+' : '') + pnl.toFixed(1) + '%'
})
const pnlColor = computed(() => {
  if (!summary.value) return 'text-gray-600'
  return summary.value.unrealizedPnlPct >= 0 ? 'text-green-600' : 'text-red-600'
})
const alertClass = computed(() => {
  const level = summary.value?.alertLevel
  if (level === 'RED')    return 'bg-red-50 text-red-700 border border-red-200'
  if (level === 'ORANGE') return 'bg-orange-50 text-orange-700 border border-orange-200'
  if (level === 'YELLOW') return 'bg-yellow-50 text-yellow-700 border border-yellow-200'
  return ''
})

function fmt(val, decimals = 2) {
  if (val == null) return '-'
  return Number(val).toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}

async function loadSummary() {
  loading.value = true
  try {
    const res = await tqqqApi.getPositionSummary()
    summary.value = res.data
  } finally {
    loading.value = false
  }
}

async function addPosition() {
  if (!form.value.shares || !form.value.pricePerShare || !form.value.buyDate) return
  await tqqqApi.addPosition({
    buyDate: form.value.buyDate,
    shares: parseFloat(form.value.shares),
    pricePerShare: parseFloat(form.value.pricePerShare),
    notes: form.value.notes
  })
  form.value = { buyDate: '', shares: '', pricePerShare: '', notes: '' }
  await loadSummary()
}

onMounted(loadSummary)
</script>
```

- [ ] **Step 2: Create Stat helper component**

```vue
<!-- frontend/src/components/tqqq/Stat.vue -->
<template>
  <div class="bg-gray-50 rounded p-3">
    <div class="text-xs text-gray-500 mb-1">{{ label }}</div>
    <div class="text-sm font-semibold" :class="color || 'text-gray-900'">{{ value }}</div>
  </div>
</template>
<script setup>
defineProps({ label: String, value: String, color: String })
</script>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/tqqq/PositionPanel.vue
git add frontend/src/components/tqqq/Stat.vue
git commit -m "feat: add PositionPanel with position tracking and add-position form"
```

---

## Task 14: Frontend — BacktestPanel Component

**Files:**
- Create: `frontend/src/components/tqqq/BacktestPanel.vue`

- [ ] **Step 1: Create BacktestPanel.vue**

```vue
<!-- frontend/src/components/tqqq/BacktestPanel.vue -->
<template>
  <div class="bg-white rounded-lg shadow p-6">
    <h2 class="text-lg font-semibold text-gray-900 mb-4">历史回测</h2>

    <!-- Config form -->
    <div class="grid grid-cols-2 gap-3 mb-4">
      <div>
        <label class="text-xs text-gray-500">开始日期</label>
        <input v-model="config.startDate" type="date" class="w-full border rounded px-2 py-1 text-sm mt-1" />
      </div>
      <div>
        <label class="text-xs text-gray-500">结束日期</label>
        <input v-model="config.endDate" type="date" class="w-full border rounded px-2 py-1 text-sm mt-1" />
      </div>
      <div>
        <label class="text-xs text-gray-500">总预算 ($)</label>
        <input v-model="config.budget" type="number" class="w-full border rounded px-2 py-1 text-sm mt-1" />
      </div>
      <div>
        <label class="text-xs text-gray-500">初始持仓价值 ($)</label>
        <input v-model="config.initialPosition" type="number" class="w-full border rounded px-2 py-1 text-sm mt-1" />
      </div>
      <button @click="runBacktest" :disabled="loading"
        class="col-span-2 bg-indigo-600 text-white rounded px-3 py-2 text-sm hover:bg-indigo-700 disabled:opacity-50">
        {{ loading ? '回测中...' : '运行回测' }}
      </button>
    </div>

    <!-- Results -->
    <div v-if="result" class="border-t pt-4">
      <div class="grid grid-cols-3 gap-3 mb-4">
        <Stat label="总收益率" :value="result.totalReturn.toFixed(1) + '%'"
          :color="result.totalReturn >= 0 ? 'text-green-600' : 'text-red-600'" />
        <Stat label="最大回撤" :value="result.maxDrawdown.toFixed(1) + '%'" color="text-red-600" />
        <Stat label="信号触发次数" :value="String(result.signalCount)" />
        <Stat label="平均持仓成本" :value="'$' + result.avgCostPerShare.toFixed(2)" />
        <Stat label="最终价值" :value="'$' + result.finalValue.toFixed(0)" />
        <Stat label="一次性买入收益" :value="result.lumpSumReturn.toFixed(1) + '%'"
          :color="result.lumpSumReturn >= 0 ? 'text-green-600' : 'text-red-600'" />
      </div>

      <!-- Equity curve chart -->
      <div class="h-48">
        <canvas ref="chartCanvas"></canvas>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { tqqqApi } from '@/api/tqqq'
import Stat from './Stat.vue'
import { Chart, LineElement, PointElement, LineController, CategoryScale,
         LinearScale, Tooltip, Legend } from 'chart.js'

Chart.register(LineElement, PointElement, LineController, CategoryScale,
               LinearScale, Tooltip, Legend)

const config = ref({
  startDate: '2020-01-01',
  endDate: new Date().toISOString().split('T')[0],
  budget: 10000,
  initialPosition: 0
})
const result = ref(null)
const loading = ref(false)
const chartCanvas = ref(null)
let chartInstance = null

async function runBacktest() {
  loading.value = true
  try {
    const res = await tqqqApi.runBacktest(config.value)
    result.value = res.data
    await nextTick()
    renderChart(res.data.snapshots)
  } finally {
    loading.value = false
  }
}

function renderChart(snapshots) {
  if (chartInstance) chartInstance.destroy()
  if (!chartCanvas.value || !snapshots?.length) return

  // Sample every 5 days to keep chart readable
  const sampled = snapshots.filter((_, i) => i % 5 === 0)
  chartInstance = new Chart(chartCanvas.value, {
    type: 'line',
    data: {
      labels: sampled.map(s => s.date),
      datasets: [{
        label: '组合价值',
        data: sampled.map(s => s.portfolioValue),
        borderColor: '#4f46e5',
        tension: 0.1,
        pointRadius: 0,
        borderWidth: 2
      }, {
        label: '累计投入',
        data: sampled.map(s => s.invested),
        borderColor: '#9ca3af',
        tension: 0.1,
        pointRadius: 0,
        borderWidth: 1,
        borderDash: [4, 4]
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: true, position: 'top' } },
      scales: { x: { ticks: { maxTicksLimit: 8 } } }
    }
  })
}
</script>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/tqqq/BacktestPanel.vue
git commit -m "feat: add BacktestPanel with equity curve chart"
```

---

## Task 15: Frontend — Main Dashboard Page and Router

**Files:**
- Create: `frontend/src/views/Tqqq.vue`
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/src/components/Sidebar.vue`

- [ ] **Step 1: Create Tqqq.vue**

```vue
<!-- frontend/src/views/Tqqq.vue -->
<template>
  <div class="p-6 space-y-6">
    <div>
      <h1 class="text-2xl font-bold text-gray-900">TQQQ 买入信号</h1>
      <p class="text-sm text-gray-500 mt-1">基于复合评分模型的加仓辅助决策系统</p>
    </div>

    <!-- Data status bar -->
    <div class="bg-blue-50 border border-blue-200 rounded p-3 flex items-center justify-between">
      <span class="text-sm text-blue-700">首次使用请先加载历史数据（约需 30 秒）</span>
      <div class="flex gap-2">
        <button @click="loadHistory" :disabled="loadingHistory"
          class="text-xs bg-blue-600 text-white rounded px-3 py-1 hover:bg-blue-700 disabled:opacity-50">
          {{ loadingHistory ? '加载中...' : '加载 5 年历史数据' }}
        </button>
        <button @click="refreshData" :disabled="loadingRefresh"
          class="text-xs bg-white border border-blue-300 text-blue-700 rounded px-3 py-1 hover:bg-blue-50 disabled:opacity-50">
          {{ loadingRefresh ? '刷新中...' : '刷新今日数据' }}
        </button>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <SignalPanel />
      <PositionPanel />
    </div>

    <BacktestPanel />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { tqqqApi } from '@/api/tqqq'
import SignalPanel from '@/components/tqqq/SignalPanel.vue'
import PositionPanel from '@/components/tqqq/PositionPanel.vue'
import BacktestPanel from '@/components/tqqq/BacktestPanel.vue'

const loadingHistory = ref(false)
const loadingRefresh = ref(false)

async function loadHistory() {
  loadingHistory.value = true
  try { await tqqqApi.loadHistory() } finally { loadingHistory.value = false }
}

async function refreshData() {
  loadingRefresh.value = true
  try { await tqqqApi.refreshData() } finally { loadingRefresh.value = false }
}
</script>
```

- [ ] **Step 2: Add route in router/index.js**

In `frontend/src/router/index.js`, add this import at the top:
```javascript
import Tqqq from '../views/Tqqq.vue'
```

Add this route inside the `children` array (after the `stocks` route):
```javascript
{
  path: 'tqqq',
  name: 'Tqqq',
  component: Tqqq,
  meta: {
    requiresAuth: true,
    title: 'TQQQ Signal',
    description: 'TQQQ buy signal algorithm'
  }
}
```

- [ ] **Step 3: Add TQQQ nav item in Sidebar.vue**

In `frontend/src/components/Sidebar.vue`, find the Strategy section. Replace the disabled Strategies item with an active TQQQ link before the existing "Strategies" disabled item:

```html
<!-- TQQQ Signal — add BEFORE the disabled "Strategies" item -->
<router-link
  to="/tqqq"
  class="flex items-center space-x-3 px-3 py-2 rounded-md text-sm font-medium transition-colors cursor-pointer"
  :class="isActive('/tqqq')"
>
  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
      d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
  </svg>
  <span>TQQQ 信号</span>
</router-link>
```

- [ ] **Step 4: Verify frontend dev server starts**

```bash
cd frontend && npm run dev
```
Expected: server starts on localhost:5173 with no errors. Navigate to http://localhost:5173/tqqq — page should render.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/Tqqq.vue
git add frontend/src/router/index.js
git add frontend/src/components/Sidebar.vue
git commit -m "feat: add TQQQ dashboard page, route, and sidebar navigation"
```

---

## Task 16: End-to-End Verification

- [ ] **Step 1: Run all backend tests**

```bash
cd backend && mvn test -q 2>&1 | tail -15
```
Expected: `BUILD SUCCESS`, all tests pass, 0 failures

- [ ] **Step 2: Start backend**

```bash
cd backend && mvn spring-boot:run &
```
Wait for "Started StockInvestmentApplication" in logs.

- [ ] **Step 3: Load history data via API**

```bash
curl -s -X POST http://localhost:8080/api/tqqq/data/load-history \
  -H "Authorization: Bearer <your-jwt-token>"
```
Expected: `"History loading started"`. Wait ~30 seconds for data to load.

- [ ] **Step 4: Test today's signal endpoint**

```bash
curl -s http://localhost:8080/api/tqqq/signal/today \
  -H "Authorization: Bearer <your-jwt-token>" | python -m json.tool
```
Expected: JSON with `totalScore`, `buySignalActive`, `suggestedAmount` fields.

- [ ] **Step 5: Run a backtest via API**

```bash
curl -s -X POST http://localhost:8080/api/tqqq/backtest \
  -H "Authorization: Bearer <your-jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{"budget": 10000, "startDate": "2022-01-01"}' | python -m json.tool
```
Expected: JSON with `totalReturn`, `maxDrawdown`, `signalCount`, `lumpSumReturn`.

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "feat: TQQQ signal algorithm — complete implementation"
```
