package com.stock.investment.repository;

import com.stock.investment.entity.StockPrice;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface StockPriceRepository extends JpaRepository<StockPrice, Long> {

    /**
     * Get latest price for a stock
     */
    Optional<StockPrice> findFirstByStockIdOrderByPriceDateDesc(Long stockId);

    /**
     * Get price history for a stock within a date range
     */
    List<StockPrice> findByStockIdAndPriceDateBetweenOrderByPriceDateDesc(
        Long stockId, LocalDateTime startDate, LocalDateTime endDate);

    /**
     * Get all prices for a stock
     */
    List<StockPrice> findByStockIdOrderByPriceDateDesc(Long stockId);

    /**
     * Check if price exists for stock on a specific date
     */
    @Query("SELECT COUNT(p) > 0 FROM StockPrice p WHERE p.stockId = :stockId " +
           "AND DATE(p.priceDate) = DATE(:priceDate)")
    boolean existsByStockIdAndDate(@Param("stockId") Long stockId,
                                   @Param("priceDate") LocalDateTime priceDate);

    /**
     * Delete old price records (for cleanup)
     */
    void deleteByPriceDateBefore(LocalDateTime date);
}
