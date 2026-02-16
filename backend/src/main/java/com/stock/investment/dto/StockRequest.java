package com.stock.investment.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class StockRequest {
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
}
