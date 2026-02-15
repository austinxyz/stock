package com.stock.investment.repository;

import com.stock.investment.entity.Portfolio;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface PortfolioRepository extends JpaRepository<Portfolio, Long> {
    List<Portfolio> findByUserIdAndIsActiveTrue(Long userId);
    List<Portfolio> findByUserId(Long userId);
}
