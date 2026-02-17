package com.stock.investment.scheduler;

import com.stock.investment.entity.Stock;
import com.stock.investment.repository.StockRepository;
import com.stock.investment.service.YahooFinanceService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@Component
@Slf4j
@RequiredArgsConstructor
public class StockDataScheduler {
    private final StockRepository stockRepository;
    private final YahooFinanceService yahooFinanceService;

    /**
     * Update stock prices daily at 6 PM (after market close)
     * Cron: 0 0 18 * * ? (18:00:00 every day)
     */
    @Scheduled(cron = "0 0 18 * * ?")
    public void updateDailyStockPrices() {
        log.info("Starting daily stock price update...");
        List<Stock> activeStocks = stockRepository.findByIsActiveTrue();

        int successCount = 0;
        int failureCount = 0;

        for (Stock stock : activeStocks) {
            try {
                Map<String, Object> quote = yahooFinanceService.getQuote(stock.getSymbol());
                // Price updates would go to a separate price history table in production
                // For now, we skip the price update since the field is removed
                stockRepository.save(stock);
                successCount++;

                log.debug("Checked stock {}", stock.getSymbol());

                // Sleep to avoid rate limiting
                Thread.sleep(1000);
            } catch (Exception e) {
                failureCount++;
                log.error("Failed to update price for {}: {}", stock.getSymbol(), e.getMessage());
            }
        }

        log.info("Daily stock price update completed. Success: {}, Failed: {}", successCount, failureCount);
    }

    /**
     * Update stock details weekly on Sunday at 2 AM
     * Cron: 0 0 2 * * SUN
     */
    @Scheduled(cron = "0 0 2 * * SUN")
    public void updateWeeklyStockDetails() {
        log.info("Starting weekly stock details update...");
        List<Stock> activeStocks = stockRepository.findByIsActiveTrue();

        int successCount = 0;
        int failureCount = 0;

        for (Stock stock : activeStocks) {
            try {
                Map<String, Object> details = yahooFinanceService.getStockDetails(stock.getSymbol());

                stock.setName((String) details.getOrDefault("longName", details.get("shortName")));
                stock.setIndustry((String) details.get("industry"));
                stock.setSector((String) details.get("sector"));
                Double marketCapDouble = (Double) details.getOrDefault("marketCap", 0.0);
                stock.setMarketCap(marketCapDouble != null ? marketCapDouble.longValue() : null);
                stock.setDescription((String) details.get("longBusinessSummary"));

                stockRepository.save(stock);
                successCount++;

                log.debug("Updated details for {}", stock.getSymbol());

                // Sleep to avoid rate limiting
                Thread.sleep(2000);
            } catch (Exception e) {
                failureCount++;
                log.error("Failed to update details for {}: {}", stock.getSymbol(), e.getMessage());
            }
        }

        log.info("Weekly stock details update completed. Success: {}, Failed: {}", successCount, failureCount);
    }
}
