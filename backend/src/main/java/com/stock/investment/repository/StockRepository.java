package com.stock.investment.repository;

import com.stock.investment.entity.Stock;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface StockRepository extends JpaRepository<Stock, Long> {
    Optional<Stock> findBySymbol(String symbol);

    List<Stock> findByIsActiveTrue();

    List<Stock> findByMarket(String market);

    List<Stock> findBySecurityType(String securityType);

    @Query("SELECT s FROM Stock s WHERE s.isActive = true AND " +
           "(LOWER(s.symbol) LIKE LOWER(CONCAT('%', :keyword, '%')) OR " +
           "LOWER(s.name) LIKE LOWER(CONCAT('%', :keyword, '%')))")
    List<Stock> searchByKeyword(@Param("keyword") String keyword);

    @Query("SELECT s FROM Stock s WHERE s.isActive = true AND s.market = :market AND s.securityType = :securityType")
    List<Stock> findByMarketAndSecurityType(@Param("market") String market, @Param("securityType") String securityType);
}
