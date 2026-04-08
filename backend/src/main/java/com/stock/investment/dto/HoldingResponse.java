package com.stock.investment.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class HoldingResponse {
    private Long id;
    private Long portfolioId;
    private Long stockId;
    private String symbol;
    private String stockName;
    private BigDecimal quantity;
    private BigDecimal costPrice;
    private BigDecimal currentPrice;
    private String currency;
    private BigDecimal totalCost;
    private BigDecimal totalValue;
    private BigDecimal gainLoss;
    private BigDecimal gainLossPercent;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
