package com.stock.investment.service;

import com.stock.investment.dto.PortfolioRequest;
import com.stock.investment.dto.PortfolioResponse;
import com.stock.investment.entity.Portfolio;
import com.stock.investment.repository.PortfolioRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class PortfolioService {

    private final PortfolioRepository portfolioRepository;
    private final UserService userService;

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
}
