package com.stock.investment.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "holdings", indexes = {
    @Index(name = "idx_portfolio_id", columnList = "portfolio_id"),
    @Index(name = "idx_stock_id", columnList = "stock_id")
})
@Data
@NoArgsConstructor
@AllArgsConstructor
public class Holding {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "portfolio_id", nullable = false)
    private Long portfolioId;

    @Column(name = "stock_id", nullable = false)
    private Long stockId;

    @Column(precision = 15, scale = 4, nullable = false)
    private BigDecimal quantity;

    @Column(name = "cost_price", precision = 15, scale = 4, nullable = false)
    private BigDecimal costPrice;

    @Column(name = "import_source", length = 20)
    private String importSource;

    @Column(name = "imported_at")
    private LocalDateTime importedAt;

    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        updatedAt = LocalDateTime.now();
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }
}
