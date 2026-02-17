package com.stock.investment.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "stocks")
@Data
@NoArgsConstructor
@AllArgsConstructor
@EntityListeners(AuditingEntityListener.class)
public class Stock {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(unique = true, nullable = false, length = 20)
    private String symbol;

    @Column(nullable = false, length = 255)
    private String name;

    @Column(name = "security_type", length = 10)
    private String securityType = "STOCK"; // STOCK, ETF

    @Column(length = 10)
    private String market; // US, HK, CN

    @Column(length = 50)
    private String exchange;

    @Column(length = 100)
    private String sector;

    @Column(length = 100)
    private String industry;

    @Column(name = "market_cap")
    private Long marketCap;

    @Column(name = "listing_date")
    private java.time.LocalDate listingDate;

    // ETF specific fields
    @Column(name = "etf_category", length = 100)
    private String etfCategory;

    @Column(name = "etf_holdings_count")
    private Integer etfHoldingsCount;

    @Column(name = "expense_ratio", precision = 10, scale = 4)
    private BigDecimal expenseRatio;

    @Column(name = "aum")
    private Long aum; // Assets Under Management

    @Column(name = "avg_volume")
    private Long avgVolume;

    @Column(name = "dividend_yield", precision = 10, scale = 4)
    private BigDecimal dividendYield;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(name = "is_active")
    private Boolean isActive = true;

    @CreatedDate
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @LastModifiedDate
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;
}
