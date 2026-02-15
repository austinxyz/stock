package com.stock.investment.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.math.BigDecimal;

@Data
public class PortfolioRequest {

    @NotBlank(message = "Portfolio name is required")
    @Size(max = 100, message = "Portfolio name must not exceed 100 characters")
    private String name;

    @Size(max = 50, message = "Broker name must not exceed 50 characters")
    private String broker;

    private String accountType; // CASH, MARGIN, IRA_TRADITIONAL, IRA_ROTH, 401K, TAXABLE

    private Boolean taxDeferred;

    private Boolean taxFree;

    private BigDecimal contributionLimit;

    private Boolean withdrawalPenalty;
}
