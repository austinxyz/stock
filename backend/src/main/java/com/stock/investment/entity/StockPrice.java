package com.stock.investment.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "stock_prices", indexes = {
    @Index(name = "idx_stock_price_date", columnList = "stock_id,price_date"),
    @Index(name = "idx_price_date", columnList = "price_date")
})
@Data
@NoArgsConstructor
@AllArgsConstructor
public class StockPrice {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "stock_id", nullable = false)
    private Long stockId;

    @Column(precision = 15, scale = 4, nullable = false)
    private BigDecimal price;

    @Column
    private Long volume;

    @Column(length = 10)
    private String currency;

    @Column(name = "market_cap")
    private Long marketCap;

    @Column(length = 50)
    private String source;

    @Column(name = "price_date", nullable = false)
    private LocalDateTime priceDate;

    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
    }
}
