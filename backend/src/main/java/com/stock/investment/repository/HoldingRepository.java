package com.stock.investment.repository;

import com.stock.investment.entity.Holding;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;

@Repository
public interface HoldingRepository extends JpaRepository<Holding, Long> {

    /**
     * Find all holdings for a portfolio
     */
    List<Holding> findByPortfolioId(Long portfolioId);

    /**
     * Find specific holding by portfolio and stock
     */
    Optional<Holding> findByPortfolioIdAndStockId(Long portfolioId, Long stockId);

    /**
     * Find all holdings for a specific stock across all portfolios
     */
    List<Holding> findByStockId(Long stockId);

    /**
     * Delete all holdings for a portfolio
     */
    void deleteByPortfolioId(Long portfolioId);

    /**
     * Check if holding exists
     */
    boolean existsByPortfolioIdAndStockId(Long portfolioId, Long stockId);

    /**
     * Get total quantity of a stock across all portfolios
     */
    @Query("SELECT SUM(h.quantity) FROM Holding h WHERE h.stockId = :stockId")
    BigDecimal getTotalQuantityByStock(@Param("stockId") Long stockId);
}
