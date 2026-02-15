package com.stock.investment.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class PortfolioResponse {
    private Long id;
    private String name;
    private String broker;
    private String accountType;
    private Boolean taxDeferred;
    private Boolean taxFree;
    private BigDecimal contributionLimit;
    private Boolean withdrawalPenalty;
    private Boolean isActive;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
