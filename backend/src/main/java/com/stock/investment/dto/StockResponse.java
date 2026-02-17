package com.stock.investment.dto;

import com.stock.investment.entity.Stock;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class StockResponse {
    private Long id;
    private String symbol;
    private String name;
    private String market;
    private String industry;
    private String sector;
    private String securityType;
    private BigDecimal marketCap;
    private String description;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    private Double currentPrice;  // Real-time price from API (not stored in DB)
    private String currency;      // Currency for the price

    public static StockResponse fromEntity(Stock stock) {
        return new StockResponse(
            stock.getId(),
            stock.getSymbol(),
            stock.getName(),
            stock.getMarket(),
            stock.getIndustry(),
            stock.getSector(),
            stock.getSecurityType(),
            stock.getMarketCap() != null ? BigDecimal.valueOf(stock.getMarketCap()) : null,
            stock.getDescription(),
            stock.getCreatedAt(),
            stock.getUpdatedAt(),
            null,  // currentPrice - to be set separately if needed
            null   // currency - to be set separately if needed
        );
    }

    public static StockResponse fromEntityWithPrice(Stock stock, Double price, String currency) {
        return new StockResponse(
            stock.getId(),
            stock.getSymbol(),
            stock.getName(),
            stock.getMarket(),
            stock.getIndustry(),
            stock.getSector(),
            stock.getSecurityType(),
            stock.getMarketCap() != null ? BigDecimal.valueOf(stock.getMarketCap()) : null,
            stock.getDescription(),
            stock.getCreatedAt(),
            stock.getUpdatedAt(),
            price,
            currency
        );
    }
}
