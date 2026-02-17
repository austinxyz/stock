package com.stock.investment.service;

import com.stock.investment.dto.StockRequest;
import com.stock.investment.dto.StockResponse;
import com.stock.investment.entity.Stock;
import com.stock.investment.entity.StockPrice;
import com.stock.investment.repository.StockRepository;
import com.stock.investment.repository.StockPriceRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
@Slf4j
@RequiredArgsConstructor
public class StockService {
    private final StockRepository stockRepository;
    private final YahooFinanceService yahooFinanceService;
    private final AlphaVantageService alphaVantageService;
    private final StockPriceRepository stockPriceRepository;

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
     * Import stock from external API (tries Alpha Vantage first, then Yahoo Finance)
     */
    @Transactional
    public StockResponse importStockFromYahoo(String symbol) {
        // Check if stock already exists
        if (stockRepository.findBySymbol(symbol.toUpperCase()).isPresent()) {
            throw new RuntimeException("Stock already exists: " + symbol);
        }

        // Try Alpha Vantage first (more reliable)
        try {
            return importFromAlphaVantage(symbol);
        } catch (Exception e) {
            log.warn("Alpha Vantage import failed for {}: {}", symbol, e.getMessage());
        }

        // Fallback to Yahoo Finance
        try {
            return importFromYahoo(symbol);
        } catch (Exception e) {
            log.error("All import methods failed for {}: {}", symbol, e.getMessage());
            throw new RuntimeException("Failed to import stock. Please try adding manually or check the symbol.");
        }
    }

    /**
     * Import stock from Alpha Vantage
     */
    private StockResponse importFromAlphaVantage(String symbol) {
        Map<String, Object> details = alphaVantageService.getStockDetails(symbol);

        Stock stock = new Stock();
        stock.setSymbol(symbol.toUpperCase());
        stock.setName((String) details.get("name"));
        stock.setMarket(determineMarket((String) details.get("currency")));
        stock.setIndustry((String) details.get("industry"));
        stock.setSector((String) details.get("sector"));
        stock.setSecurityType("STOCK"); // Alpha Vantage doesn't distinguish ETF in free tier
        stock.setMarketCap((Long) details.get("marketCap"));
        stock.setDescription((String) details.get("description"));
        stock.setIsActive(true);

        Stock savedStock = stockRepository.save(stock);
        log.info("Imported stock from Alpha Vantage: {}", savedStock.getSymbol());
        return StockResponse.fromEntity(savedStock);
    }

    /**
     * Import stock from Yahoo Finance (fallback)
     */
    private StockResponse importFromYahoo(String symbol) {
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
        stock.setDescription((String) details.get("description"));
        stock.setIsActive(true);

        Stock savedStock = stockRepository.save(stock);
        log.info("Imported stock from Yahoo Finance: {}", savedStock.getSymbol());
        return StockResponse.fromEntity(savedStock);
    }

    /**
     * Update stock price (tries Alpha Vantage first, then Yahoo Finance)
     * Saves price to database for historical tracking
     */
    @Transactional
    public StockResponse updateStockPrice(String symbol) {
        Stock stock = stockRepository.findBySymbol(symbol.toUpperCase())
            .orElseThrow(() -> new RuntimeException("Stock not found: " + symbol));

        // Try Alpha Vantage first
        try {
            Map<String, Object> quote = alphaVantageService.getQuote(symbol);
            Double priceValue = (Double) quote.get("currentPrice");
            Long volumeValue = quote.get("volume") != null ? ((Number) quote.get("volume")).longValue() : null;
            String currency = stock.getMarket().equals("US") ? "USD" :
                             stock.getMarket().equals("HK") ? "HKD" : "CNY";

            // Save price to database
            StockPrice stockPrice = new StockPrice();
            stockPrice.setStockId(stock.getId());
            stockPrice.setPrice(BigDecimal.valueOf(priceValue));
            stockPrice.setVolume(volumeValue);
            stockPrice.setCurrency(currency);
            stockPrice.setSource("ALPHA_VANTAGE");
            stockPrice.setPriceDate(LocalDateTime.now());
            stockPriceRepository.save(stockPrice);

            log.info("Saved price for stock {} from Alpha Vantage: {} {}", stock.getSymbol(), priceValue, currency);
            return StockResponse.fromEntityWithPrice(stock, priceValue, currency);
        } catch (Exception e) {
            log.warn("Alpha Vantage price update failed for {}: {}", symbol, e.getMessage());
        }

        // Fallback to Yahoo Finance
        try {
            Map<String, Object> quote = yahooFinanceService.getQuote(symbol);
            Double priceValue = (Double) quote.get("currentPrice");
            String currency = (String) quote.get("currency");
            Long volumeValue = quote.get("volume") != null ? ((Number) quote.get("volume")).longValue() : null;

            // Save price to database
            StockPrice stockPrice = new StockPrice();
            stockPrice.setStockId(stock.getId());
            stockPrice.setPrice(BigDecimal.valueOf(priceValue));
            stockPrice.setVolume(volumeValue);
            stockPrice.setCurrency(currency);
            stockPrice.setSource("YAHOO_FINANCE");
            stockPrice.setPriceDate(LocalDateTime.now());
            stockPriceRepository.save(stockPrice);

            log.info("Saved price for stock {} from Yahoo Finance: {} {}", stock.getSymbol(), priceValue, currency);
            return StockResponse.fromEntityWithPrice(stock, priceValue, currency);
        } catch (Exception e) {
            log.error("All price update methods failed for {}: {}", symbol, e.getMessage());
            throw new RuntimeException("Failed to update stock price. API limit may be reached.");
        }
    }

    /**
     * Get all active stocks with latest prices
     */
    public List<StockResponse> getAllStocks() {
        return stockRepository.findByIsActiveTrue().stream()
            .map(stock -> {
                StockResponse response = StockResponse.fromEntity(stock);
                // Get latest price from database
                stockPriceRepository.findFirstByStockIdOrderByPriceDateDesc(stock.getId())
                    .ifPresent(price -> {
                        response.setCurrentPrice(price.getPrice().doubleValue());
                        response.setCurrency(price.getCurrency());
                    });
                return response;
            })
            .collect(Collectors.toList());
    }

    /**
     * Get stock by ID with latest price
     */
    public StockResponse getStockById(Long id) {
        Stock stock = stockRepository.findById(id)
            .orElseThrow(() -> new RuntimeException("Stock not found: " + id));
        return getStockResponseWithPrice(stock);
    }

    /**
     * Get stock by symbol with latest price
     */
    public StockResponse getStockBySymbol(String symbol) {
        Stock stock = stockRepository.findBySymbol(symbol.toUpperCase())
            .orElseThrow(() -> new RuntimeException("Stock not found: " + symbol));
        return getStockResponseWithPrice(stock);
    }

    /**
     * Search stocks by keyword with latest prices
     */
    public List<StockResponse> searchStocks(String keyword) {
        return stockRepository.searchByKeyword(keyword).stream()
            .map(this::getStockResponseWithPrice)
            .collect(Collectors.toList());
    }

    /**
     * Helper method to create StockResponse with latest price
     */
    private StockResponse getStockResponseWithPrice(Stock stock) {
        StockResponse response = StockResponse.fromEntity(stock);
        stockPriceRepository.findFirstByStockIdOrderByPriceDateDesc(stock.getId())
            .ifPresent(price -> {
                response.setCurrentPrice(price.getPrice().doubleValue());
                response.setCurrency(price.getCurrency());
            });
        return response;
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
