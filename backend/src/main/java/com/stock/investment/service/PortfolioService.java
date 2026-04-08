package com.stock.investment.service;

import com.stock.investment.dto.HoldingRequest;
import com.stock.investment.dto.HoldingResponse;
import com.stock.investment.dto.PortfolioRequest;
import com.stock.investment.dto.PortfolioResponse;
import com.stock.investment.entity.Holding;
import com.stock.investment.entity.Portfolio;
import com.stock.investment.entity.Stock;
import com.stock.investment.entity.StockPrice;
import com.stock.investment.repository.HoldingRepository;
import com.stock.investment.repository.PortfolioRepository;
import com.stock.investment.repository.StockPriceRepository;
import com.stock.investment.repository.StockRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;
import java.util.stream.Collectors;

@Service
@Slf4j
@RequiredArgsConstructor
public class PortfolioService {

    private final PortfolioRepository portfolioRepository;
    private final UserService userService;
    private final HoldingRepository holdingRepository;
    private final StockRepository stockRepository;
    private final StockPriceRepository stockPriceRepository;

    @Transactional
    public PortfolioResponse createPortfolio(PortfolioRequest request) {
        Long userId = getCurrentUserId();

        Portfolio portfolio = new Portfolio();
        portfolio.setUserId(userId);
        portfolio.setName(request.getName());
        portfolio.setBroker(request.getBroker());
        portfolio.setAccountType(request.getAccountType());
        portfolio.setTaxDeferred(request.getTaxDeferred() != null ? request.getTaxDeferred() : false);
        portfolio.setTaxFree(request.getTaxFree() != null ? request.getTaxFree() : false);
        portfolio.setContributionLimit(request.getContributionLimit());
        portfolio.setWithdrawalPenalty(request.getWithdrawalPenalty() != null ? request.getWithdrawalPenalty() : false);
        portfolio.setIsActive(true);

        Portfolio saved = portfolioRepository.save(portfolio);
        return toResponse(saved);
    }

    public List<PortfolioResponse> getUserPortfolios() {
        Long userId = getCurrentUserId();
        return portfolioRepository.findByUserIdAndIsActiveTrue(userId)
                .stream()
                .map(this::toResponse)
                .collect(Collectors.toList());
    }

    public PortfolioResponse getPortfolioById(Long id) {
        Portfolio portfolio = portfolioRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Portfolio not found"));

        // Check ownership
        if (!portfolio.getUserId().equals(getCurrentUserId())) {
            throw new RuntimeException("Access denied");
        }

        return toResponse(portfolio);
    }

    @Transactional
    public PortfolioResponse updatePortfolio(Long id, PortfolioRequest request) {
        Portfolio portfolio = portfolioRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Portfolio not found"));

        // Check ownership
        if (!portfolio.getUserId().equals(getCurrentUserId())) {
            throw new RuntimeException("Access denied");
        }

        portfolio.setName(request.getName());
        portfolio.setBroker(request.getBroker());
        portfolio.setAccountType(request.getAccountType());
        portfolio.setTaxDeferred(request.getTaxDeferred());
        portfolio.setTaxFree(request.getTaxFree());
        portfolio.setContributionLimit(request.getContributionLimit());
        portfolio.setWithdrawalPenalty(request.getWithdrawalPenalty());

        Portfolio updated = portfolioRepository.save(portfolio);
        return toResponse(updated);
    }

    @Transactional
    public void deletePortfolio(Long id) {
        Portfolio portfolio = portfolioRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Portfolio not found"));

        // Check ownership
        if (!portfolio.getUserId().equals(getCurrentUserId())) {
            throw new RuntimeException("Access denied");
        }

        // Soft delete
        portfolio.setIsActive(false);
        portfolioRepository.save(portfolio);
    }

    private Long getCurrentUserId() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        String username = authentication.getName();
        return userService.getUserIdByUsername(username);
    }

    /**
     * Get all holdings for a portfolio
     */
    public List<HoldingResponse> getHoldings(Long portfolioId) {
        Portfolio portfolio = portfolioRepository.findById(portfolioId)
                .orElseThrow(() -> new RuntimeException("Portfolio not found"));

        if (!portfolio.getUserId().equals(getCurrentUserId())) {
            throw new RuntimeException("Access denied");
        }

        return holdingRepository.findByPortfolioId(portfolioId).stream()
                .map(this::toHoldingResponse)
                .collect(Collectors.toList());
    }

    /**
     * Add holding to portfolio
     */
    @Transactional
    public HoldingResponse addHolding(Long portfolioId, HoldingRequest request) {
        Portfolio portfolio = portfolioRepository.findById(portfolioId)
                .orElseThrow(() -> new RuntimeException("Portfolio not found"));

        if (!portfolio.getUserId().equals(getCurrentUserId())) {
            throw new RuntimeException("Access denied");
        }

        // Verify stock exists
        stockRepository.findById(request.getStockId())
                .orElseThrow(() -> new RuntimeException("Stock not found: " + request.getStockId()));

        // Check if holding already exists
        holdingRepository.findByPortfolioIdAndStockId(portfolioId, request.getStockId())
                .ifPresent(h -> {
                    throw new RuntimeException("Holding already exists for this stock");
                });

        Holding holding = new Holding();
        holding.setPortfolioId(portfolioId);
        holding.setStockId(request.getStockId());
        holding.setQuantity(request.getQuantity());
        holding.setCostPrice(request.getCostPrice());

        Holding saved = holdingRepository.save(holding);
        log.info("Added holding to portfolio: {}", portfolioId);
        return toHoldingResponse(saved);
    }

    /**
     * Update holding
     */
    @Transactional
    public HoldingResponse updateHolding(Long portfolioId, Long holdingId, HoldingRequest request) {
        Portfolio portfolio = portfolioRepository.findById(portfolioId)
                .orElseThrow(() -> new RuntimeException("Portfolio not found"));

        if (!portfolio.getUserId().equals(getCurrentUserId())) {
            throw new RuntimeException("Access denied");
        }

        Holding holding = holdingRepository.findById(holdingId)
                .orElseThrow(() -> new RuntimeException("Holding not found: " + holdingId));

        if (!holding.getPortfolioId().equals(portfolioId)) {
            throw new RuntimeException("Holding does not belong to this portfolio");
        }

        holding.setQuantity(request.getQuantity());
        holding.setCostPrice(request.getCostPrice());

        Holding updated = holdingRepository.save(holding);
        log.info("Updated holding: {}", holdingId);
        return toHoldingResponse(updated);
    }

    /**
     * Delete holding
     */
    @Transactional
    public void deleteHolding(Long portfolioId, Long holdingId) {
        Portfolio portfolio = portfolioRepository.findById(portfolioId)
                .orElseThrow(() -> new RuntimeException("Portfolio not found"));

        if (!portfolio.getUserId().equals(getCurrentUserId())) {
            throw new RuntimeException("Access denied");
        }

        Holding holding = holdingRepository.findById(holdingId)
                .orElseThrow(() -> new RuntimeException("Holding not found: " + holdingId));

        if (!holding.getPortfolioId().equals(portfolioId)) {
            throw new RuntimeException("Holding does not belong to this portfolio");
        }

        holdingRepository.delete(holding);
        log.info("Deleted holding: {}", holdingId);
    }

    private Long getCurrentUserId() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        String username = authentication.getName();
        return userService.getUserIdByUsername(username);
    }

    private PortfolioResponse toResponse(Portfolio portfolio) {
        return new PortfolioResponse(
                portfolio.getId(),
                portfolio.getName(),
                portfolio.getBroker(),
                portfolio.getAccountType(),
                portfolio.getTaxDeferred(),
                portfolio.getTaxFree(),
                portfolio.getContributionLimit(),
                portfolio.getWithdrawalPenalty(),
                portfolio.getIsActive(),
                portfolio.getCreatedAt(),
                portfolio.getUpdatedAt()
        );
    }

    /**
     * Convert Holding entity to HoldingResponse with current price and calculations
     */
    private HoldingResponse toHoldingResponse(Holding holding) {
        Stock stock = stockRepository.findById(holding.getStockId())
                .orElseThrow(() -> new RuntimeException("Stock not found: " + holding.getStockId()));

        // Get latest price
        StockPrice latestPrice = stockPriceRepository
                .findFirstByStockIdOrderByPriceDateDesc(holding.getStockId())
                .orElse(null);

        BigDecimal currentPrice = latestPrice != null ? latestPrice.getPrice() : null;
        String currency = latestPrice != null ? latestPrice.getCurrency() : null;

        // Calculate total cost and value
        BigDecimal totalCost = holding.getCostPrice().multiply(holding.getQuantity());
        BigDecimal totalValue = currentPrice != null ? currentPrice.multiply(holding.getQuantity()) : null;

        // Calculate gain/loss
        BigDecimal gainLoss = totalValue != null ? totalValue.subtract(totalCost) : null;
        BigDecimal gainLossPercent = null;
        if (gainLoss != null && totalCost.compareTo(BigDecimal.ZERO) > 0) {
            gainLossPercent = gainLoss.divide(totalCost, 4, RoundingMode.HALF_UP)
                    .multiply(BigDecimal.valueOf(100));
        }

        return new HoldingResponse(
                holding.getId(),
                holding.getPortfolioId(),
                holding.getStockId(),
                stock.getSymbol(),
                stock.getName(),
                holding.getQuantity(),
                holding.getCostPrice(),
                currentPrice != null ? currentPrice.doubleValue() : null,
                currency,
                totalCost,
                totalValue,
                gainLoss,
                gainLossPercent,
                holding.getCreatedAt(),
                holding.getUpdatedAt()
        );
    }
}
