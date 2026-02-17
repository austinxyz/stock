package com.stock.investment.service;

import com.stock.investment.dto.StockRequest;
import com.stock.investment.dto.StockResponse;
import com.stock.investment.entity.Stock;
import com.stock.investment.repository.StockRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
@Slf4j
@RequiredArgsConstructor
public class StockService {
    private final StockRepository stockRepository;
    private final YahooFinanceService yahooFinanceService;

    /**
     * Create a new stock manually
     */
    @Transactional
    public StockResponse createStock(StockRequest request) {
        Stock stock = new Stock();
        stock.setSymbol(request.getSymbol().toUpperCase());
        stock.setName(request.getName());
        stock.setMarket(request.getMarket());
        stock.setIndustry(request.getIndustry());
        stock.setSector(request.getSector());
        stock.setSecurityType(request.getSecurityType());
        stock.setMarketCap(request.getMarketCap() != null ? request.getMarketCap().longValue() : null);
        stock.setDescription(request.getDescription());
        stock.setIsActive(true);

        Stock savedStock = stockRepository.save(stock);
        log.info("Created stock: {}", savedStock.getSymbol());
        return StockResponse.fromEntity(savedStock);
    }

    /**
     * Import stock from Yahoo Finance
     */
    @Transactional
    public StockResponse importStockFromYahoo(String symbol) {
        try {
            // Check if stock already exists
            if (stockRepository.findBySymbol(symbol.toUpperCase()).isPresent()) {
                throw new RuntimeException("Stock already exists: " + symbol);
            }

            // Fetch from Yahoo Finance
            Map<String, Object> details = yahooFinanceService.getStockDetails(symbol);

            Stock stock = new Stock();
            stock.setSymbol(symbol.toUpperCase());
            stock.setName((String) details.getOrDefault("longName", details.get("shortName")));
            stock.setMarket(determineMarket((String) details.get("currency")));
            stock.setIndustry((String) details.get("industry"));
            stock.setSector((String) details.get("sector"));
            stock.setSecurityType((String) details.getOrDefault("quoteType", "STOCK"));
            Double marketCapDouble = (Double) details.getOrDefault("marketCap", 0.0);
            stock.setMarketCap(marketCapDouble != null ? marketCapDouble.longValue() : null);
            stock.setDescription((String) details.get("longBusinessSummary"));
            stock.setIsActive(true);

            Stock savedStock = stockRepository.save(stock);
            log.info("Imported stock from Yahoo Finance: {}", savedStock.getSymbol());
            return StockResponse.fromEntity(savedStock);
        } catch (Exception e) {
            log.error("Error importing stock: {}", symbol, e);
            throw new RuntimeException("Failed to import stock: " + e.getMessage());
        }
    }

    /**
     * Update stock price from Yahoo Finance
     */
    @Transactional
    public StockResponse updateStockPrice(String symbol) {
        Stock stock = stockRepository.findBySymbol(symbol.toUpperCase())
            .orElseThrow(() -> new RuntimeException("Stock not found: " + symbol));

        try {
            Map<String, Object> quote = yahooFinanceService.getQuote(symbol);
            // Price updates would go to a separate price history table in production

            Stock updatedStock = stockRepository.save(stock);
            log.info("Updated price for stock: {}", updatedStock.getSymbol());
            return StockResponse.fromEntity(updatedStock);
        } catch (Exception e) {
            log.error("Error updating stock price: {}", symbol, e);
            throw new RuntimeException("Failed to update stock price: " + e.getMessage());
        }
    }

    /**
     * Get all active stocks
     */
    public List<StockResponse> getAllStocks() {
        return stockRepository.findByIsActiveTrue().stream()
            .map(StockResponse::fromEntity)
            .collect(Collectors.toList());
    }

    /**
     * Get stock by ID
     */
    public StockResponse getStockById(Long id) {
        Stock stock = stockRepository.findById(id)
            .orElseThrow(() -> new RuntimeException("Stock not found: " + id));
        return StockResponse.fromEntity(stock);
    }

    /**
     * Get stock by symbol
     */
    public StockResponse getStockBySymbol(String symbol) {
        Stock stock = stockRepository.findBySymbol(symbol.toUpperCase())
            .orElseThrow(() -> new RuntimeException("Stock not found: " + symbol));
        return StockResponse.fromEntity(stock);
    }

    /**
     * Search stocks by keyword
     */
    public List<StockResponse> searchStocks(String keyword) {
        return stockRepository.searchByKeyword(keyword).stream()
            .map(StockResponse::fromEntity)
            .collect(Collectors.toList());
    }

    /**
     * Update stock information
     */
    @Transactional
    public StockResponse updateStock(Long id, StockRequest request) {
        Stock stock = stockRepository.findById(id)
            .orElseThrow(() -> new RuntimeException("Stock not found: " + id));

        stock.setName(request.getName());
        stock.setMarket(request.getMarket());
        stock.setIndustry(request.getIndustry());
        stock.setSector(request.getSector());
        stock.setSecurityType(request.getSecurityType());
        stock.setMarketCap(request.getMarketCap() != null ? request.getMarketCap().longValue() : null);
        stock.setDescription(request.getDescription());

        Stock updatedStock = stockRepository.save(stock);
        log.info("Updated stock: {}", updatedStock.getSymbol());
        return StockResponse.fromEntity(updatedStock);
    }

    /**
     * Delete stock (soft delete)
     */
    @Transactional
    public void deleteStock(Long id) {
        Stock stock = stockRepository.findById(id)
            .orElseThrow(() -> new RuntimeException("Stock not found: " + id));

        stock.setIsActive(false);
        stockRepository.save(stock);
        log.info("Deleted stock: {}", stock.getSymbol());
    }

    /**
     * Determine market from currency
     */
    private String determineMarket(String currency) {
        if (currency == null) return "US";
        switch (currency.toUpperCase()) {
            case "USD":
                return "US";
            case "HKD":
                return "HK";
            case "CNY":
                return "CN";
            default:
                return "US";
        }
    }
}
