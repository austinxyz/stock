package com.stock.investment.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.Map;

@Service
@Slf4j
public class AlphaVantageService {
    private final RestTemplate restTemplate = new RestTemplate();
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Value("${alphavantage.api.key:DEMO}")
    private String apiKey;

    private static final String BASE_URL = "https://www.alphavantage.co/query";

    /**
     * Get stock quote (current price and basic info)
     */
    public Map<String, Object> getQuote(String symbol) {
        try {
            String url = String.format("%s?function=GLOBAL_QUOTE&symbol=%s&apikey=%s",
                    BASE_URL, symbol, apiKey);

            String response = restTemplate.getForObject(url, String.class);
            JsonNode root = objectMapper.readTree(response);

            // Check for error
            if (root.has("Error Message")) {
                throw new RuntimeException("Invalid stock symbol: " + symbol);
            }

            if (root.has("Note")) {
                throw new RuntimeException("API rate limit reached. Please try again later.");
            }

            JsonNode quote = root.path("Global Quote");

            Map<String, Object> result = new HashMap<>();
            result.put("symbol", quote.path("01. symbol").asText());
            result.put("currentPrice", quote.path("05. price").asDouble());
            result.put("change", quote.path("09. change").asDouble());
            result.put("changePercent", quote.path("10. change percent").asText());
            result.put("volume", quote.path("06. volume").asLong());
            result.put("previousClose", quote.path("08. previous close").asDouble());

            return result;
        } catch (Exception e) {
            log.error("Error fetching quote from Alpha Vantage for symbol: {}", symbol, e);
            throw new RuntimeException("Failed to fetch stock quote: " + e.getMessage());
        }
    }

    /**
     * Get company overview (detailed information)
     */
    public Map<String, Object> getCompanyOverview(String symbol) {
        try {
            String url = String.format("%s?function=OVERVIEW&symbol=%s&apikey=%s",
                    BASE_URL, symbol, apiKey);

            String response = restTemplate.getForObject(url, String.class);
            JsonNode root = objectMapper.readTree(response);

            // Check for error or empty response
            if (root.has("Error Message")) {
                throw new RuntimeException("Invalid stock symbol: " + symbol);
            }

            if (root.has("Note")) {
                throw new RuntimeException("API rate limit reached. Please try again later.");
            }

            if (!root.has("Symbol") || root.path("Symbol").asText().isEmpty()) {
                throw new RuntimeException("No data found for symbol: " + symbol);
            }

            Map<String, Object> result = new HashMap<>();
            result.put("symbol", root.path("Symbol").asText());
            result.put("name", root.path("Name").asText());
            result.put("description", root.path("Description").asText());
            result.put("sector", root.path("Sector").asText());
            result.put("industry", root.path("Industry").asText());
            result.put("marketCap", root.path("MarketCapitalization").asLong(0));
            result.put("exchange", root.path("Exchange").asText());
            result.put("country", root.path("Country").asText());
            result.put("currency", root.path("Currency").asText());

            return result;
        } catch (Exception e) {
            log.error("Error fetching company overview from Alpha Vantage for symbol: {}", symbol, e);
            throw new RuntimeException("Failed to fetch company overview: " + e.getMessage());
        }
    }

    /**
     * Get detailed stock information (combines quote + overview)
     */
    public Map<String, Object> getStockDetails(String symbol) {
        try {
            Map<String, Object> overview = getCompanyOverview(symbol);

            // Try to get current price, but don't fail if it's not available
            try {
                Map<String, Object> quote = getQuote(symbol);
                overview.put("currentPrice", quote.get("currentPrice"));
                overview.put("previousClose", quote.get("previousClose"));
                overview.put("volume", quote.get("volume"));
            } catch (Exception e) {
                log.warn("Could not fetch quote for {}: {}", symbol, e.getMessage());
            }

            return overview;
        } catch (Exception e) {
            log.error("Error fetching stock details from Alpha Vantage for symbol: {}", symbol, e);
            throw new RuntimeException("Failed to fetch stock details: " + e.getMessage());
        }
    }
}
