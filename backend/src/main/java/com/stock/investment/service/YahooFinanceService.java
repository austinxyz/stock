package com.stock.investment.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpRequest;
import org.springframework.http.client.ClientHttpRequestExecution;
import org.springframework.http.client.ClientHttpRequestInterceptor;
import org.springframework.http.client.ClientHttpResponse;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.io.IOException;
import java.math.BigDecimal;
import java.util.HashMap;
import java.util.Map;

@Service
@Slf4j
@RequiredArgsConstructor
public class YahooFinanceService {
    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper = new ObjectMapper();

    private static final String YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/";
    private static final String YAHOO_QUOTE_SUMMARY_URL = "https://query2.finance.yahoo.com/v10/finance/quoteSummary/";

    public YahooFinanceService() {
        this.restTemplate = createRestTemplate();
    }

    private RestTemplate createRestTemplate() {
        RestTemplate template = new RestTemplate();
        // Add interceptor to set User-Agent header for every request
        template.getInterceptors().add((request, body, execution) -> {
            request.getHeaders().add("User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36");
            request.getHeaders().add("Accept", "*/*");
            request.getHeaders().add("Accept-Language", "en-US,en;q=0.9");
            request.getHeaders().add("Origin", "https://finance.yahoo.com");
            request.getHeaders().add("Referer", "https://finance.yahoo.com");
            return execution.execute(request, body);
        });
        return template;
    }

    /**
     * Get basic stock quote (current price, change, volume, etc.)
     */
    public Map<String, Object> getQuote(String symbol) {
        try {
            String url = YAHOO_QUOTE_URL + symbol + "?interval=1d&range=1d";
            String response = restTemplate.getForObject(url, String.class);

            JsonNode root = objectMapper.readTree(response);
            JsonNode result = root.path("chart").path("result").get(0);
            JsonNode meta = result.path("meta");

            Map<String, Object> quote = new HashMap<>();
            quote.put("symbol", meta.path("symbol").asText());
            quote.put("currentPrice", meta.path("regularMarketPrice").asDouble());
            quote.put("previousClose", meta.path("previousClose").asDouble());
            quote.put("currency", meta.path("currency").asText());
            quote.put("exchangeName", meta.path("exchangeName").asText());
            quote.put("regularMarketTime", meta.path("regularMarketTime").asLong());

            return quote;
        } catch (Exception e) {
            log.error("Error fetching quote for symbol: {}", symbol, e);
            throw new RuntimeException("Failed to fetch stock quote: " + e.getMessage());
        }
    }

    /**
     * Get detailed stock information (profile, statistics, fundamentals)
     * Uses multiple data sources with fallback strategy
     */
    public Map<String, Object> getStockDetails(String symbol) {
        // Try method 1: Download page (more stable for basic info)
        try {
            return getStockDetailsFromDownload(symbol);
        } catch (Exception e) {
            log.warn("Failed to fetch from download API for {}: {}", symbol, e.getMessage());
        }

        // Try method 2: Quote summary API
        try {
            return getStockDetailsFromQuoteSummary(symbol);
        } catch (Exception e) {
            log.warn("Failed to fetch from quote summary API for {}: {}", symbol, e.getMessage());
        }

        // If both methods fail, return basic info from quote
        try {
            log.info("Falling back to basic quote for {}", symbol);
            Map<String, Object> quote = getQuote(symbol);
            Map<String, Object> details = new HashMap<>();
            details.put("symbol", quote.get("symbol"));
            details.put("shortName", symbol);
            details.put("longName", symbol);
            details.put("quoteType", "EQUITY");
            details.put("industry", "");
            details.put("sector", "");
            details.put("description", "");
            details.put("country", "");
            return details;
        } catch (Exception e) {
            log.error("All methods failed for symbol: {}", symbol, e);
            throw new RuntimeException("Failed to fetch stock details: " + e.getMessage());
        }
    }

    /**
     * Get stock details from Yahoo Finance download page
     */
    private Map<String, Object> getStockDetailsFromDownload(String symbol) throws Exception {
        // Use the download/screener API which is more stable
        String url = "https://query1.finance.yahoo.com/v7/finance/quote?symbols=" + symbol;
        String response = restTemplate.getForObject(url, String.class);

        JsonNode root = objectMapper.readTree(response);
        JsonNode result = root.path("quoteResponse").path("result").get(0);

        Map<String, Object> details = new HashMap<>();
        details.put("symbol", result.path("symbol").asText());
        details.put("shortName", result.path("shortName").asText());
        details.put("longName", result.path("longName").asText(result.path("shortName").asText()));
        details.put("quoteType", result.path("quoteType").asText("EQUITY"));
        details.put("industry", result.path("industry").asText(""));
        details.put("sector", result.path("sector").asText(""));
        details.put("description", result.path("longBusinessSummary").asText(""));
        details.put("country", "");

        // Market cap
        if (result.has("marketCap")) {
            details.put("marketCap", result.path("marketCap").asDouble());
        }

        return details;
    }

    /**
     * Get stock details from quote summary API (original method)
     */
    private Map<String, Object> getStockDetailsFromQuoteSummary(String symbol) throws Exception {
        String url = YAHOO_QUOTE_SUMMARY_URL + symbol + "?modules=price,summaryProfile,summaryDetail,defaultKeyStatistics";
        String response = restTemplate.getForObject(url, String.class);

        JsonNode root = objectMapper.readTree(response);
        JsonNode result = root.path("quoteSummary").path("result").get(0);

        Map<String, Object> details = new HashMap<>();

        // Price information
        JsonNode price = result.path("price");
        details.put("symbol", price.path("symbol").asText());
        details.put("shortName", price.path("shortName").asText());
        details.put("longName", price.path("longName").asText());
        details.put("currentPrice", price.path("regularMarketPrice").path("raw").asDouble());
        details.put("currency", price.path("currency").asText());
        details.put("marketCap", price.path("marketCap").path("raw").asDouble());
        details.put("quoteType", price.path("quoteType").asText()); // EQUITY, ETF, etc.

        // Profile information
        JsonNode profile = result.path("summaryProfile");
        details.put("industry", profile.path("industry").asText());
        details.put("sector", profile.path("sector").asText());
        details.put("description", profile.path("longBusinessSummary").asText());
        details.put("country", profile.path("country").asText());

        // Key statistics
        JsonNode stats = result.path("summaryDetail");
        details.put("fiftyDayAverage", stats.path("fiftyDayAverage").path("raw").asDouble());
        details.put("twoHundredDayAverage", stats.path("twoHundredDayAverage").path("raw").asDouble());
        details.put("trailingPE", stats.path("trailingPE").path("raw").asDouble());
        details.put("dividendYield", stats.path("dividendYield").path("raw").asDouble());

        return details;
    }

    /**
     * Get historical prices for a stock
     */
    public Map<String, Object> getHistoricalPrices(String symbol, String range) {
        try {
            String url = YAHOO_QUOTE_URL + symbol + "?interval=1d&range=" + range;
            String response = restTemplate.getForObject(url, String.class);

            JsonNode root = objectMapper.readTree(response);
            JsonNode result = root.path("chart").path("result").get(0);

            Map<String, Object> historicalData = new HashMap<>();
            historicalData.put("symbol", result.path("meta").path("symbol").asText());
            historicalData.put("timestamps", result.path("timestamp"));

            JsonNode indicators = result.path("indicators").path("quote").get(0);
            historicalData.put("open", indicators.path("open"));
            historicalData.put("high", indicators.path("high"));
            historicalData.put("low", indicators.path("low"));
            historicalData.put("close", indicators.path("close"));
            historicalData.put("volume", indicators.path("volume"));

            return historicalData;
        } catch (Exception e) {
            log.error("Error fetching historical prices for symbol: {}", symbol, e);
            throw new RuntimeException("Failed to fetch historical prices: " + e.getMessage());
        }
    }
}
