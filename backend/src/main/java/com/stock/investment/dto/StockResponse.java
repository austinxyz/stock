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
    private BigDecimal currentPrice;
    private String currency;
    private String description;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

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
            stock.getCurrentPrice(),
            stock.getCurrency(),
            stock.getDescription(),
            stock.getCreatedAt(),
            stock.getUpdatedAt()
        );
    }
}
